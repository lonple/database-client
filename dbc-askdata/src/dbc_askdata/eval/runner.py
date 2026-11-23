from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.models import AskProject
from dbc_askdata.db.session import SessionLocal
from dbc_askdata.eval.case_executor import execute_task_case
from dbc_askdata.eval.metrics import aggregate_metrics
from dbc_askdata.eval.models import EvalProject, EvalTask, EvalTaskCase
from dbc_askdata.llm.client import LlmClient

log = logging.getLogger(__name__)

# task_id -> cancel flag
_cancel_flags: dict[int, bool] = {}
_running_tasks: dict[int, asyncio.Task[Any]] = {}
# 每次 start 递增；旧协程收尾若 generation 不匹配则不得回写终态（避免清 PENDING 后又被标 CANCELLED）
_run_generations: dict[int, int] = {}


def request_cancel(task_id: int) -> None:
    _cancel_flags[task_id] = True


def is_cancel_requested(task_id: int) -> bool:
    return bool(_cancel_flags.get(task_id))


def _current_generation(task_id: int) -> int:
    return int(_run_generations.get(task_id) or 0)


async def stop_eval_task_background(task_id: int, *, timeout_sec: float = 120.0) -> None:
    """取消并等待既有后台跑批结束，避免与新一轮 start 竞态。"""
    prev = _running_tasks.get(task_id)
    if prev is None or prev.done():
        _running_tasks.pop(task_id, None)
        return
    log.warning("测评任务仍有后台协程，请求停止并等待 task_id=%s", task_id)
    _cancel_flags[task_id] = True
    try:
        await asyncio.wait_for(asyncio.shield(prev), timeout=timeout_sec)
    except asyncio.TimeoutError:
        log.error("等待旧跑批超时，强制 cancel task_id=%s", task_id)
        prev.cancel()
        try:
            await prev
        except (asyncio.CancelledError, Exception):
            log.warning("强制结束旧跑批异常 task_id=%s", task_id, exc_info=True)
    except asyncio.CancelledError:
        pass
    except Exception:
        log.warning("等待旧跑批结束异常 task_id=%s", task_id, exc_info=True)
    if _running_tasks.get(task_id) is prev:
        _running_tasks.pop(task_id, None)


async def start_eval_task_background(
    *,
    task_id: int,
    settings: Settings | None = None,
    llm: LlmClient,
    authorization: str,
    user_id: int,
    task_case_ids: list[int] | None = None,
) -> int:
    """启动后台跑批。

    若同任务仍有未结束协程，先停稳再开新一轮（禁止静默跳过）。
    返回本轮 generation。
    task_case_ids 非空时仅执行这些任务用例（须已重置为 PENDING）；空则执行全部 PENDING。
    """
    await stop_eval_task_background(task_id)

    gen = _current_generation(task_id) + 1
    _run_generations[task_id] = gen
    _cancel_flags[task_id] = False

    t = asyncio.create_task(
        _run_task(
            task_id=task_id,
            settings=settings or get_settings(),
            llm=llm,
            authorization=authorization,
            user_id=user_id,
            task_case_ids=task_case_ids,
            generation=gen,
        ),
        name=f"eval-task-{task_id}-g{gen}",
    )
    _running_tasks[task_id] = t

    def _clear(done: asyncio.Task[Any], *, tid: int = task_id, expected: asyncio.Task[Any] = t) -> None:
        if _running_tasks.get(tid) is expected:
            _running_tasks.pop(tid, None)
        if done.cancelled():
            return
        exc = done.exception()
        if exc is not None:
            log.error("测评后台 Task 异常退出 task_id=%s", tid, exc_info=exc)

    t.add_done_callback(_clear)
    log.info(
        "测评任务后台已启动 task_id=%s generation=%s case_filter=%s",
        task_id,
        gen,
        task_case_ids,
    )
    return gen


async def _run_task(
    *,
    task_id: int,
    settings: Settings,
    llm: LlmClient,
    authorization: str,
    user_id: int,
    task_case_ids: list[int] | None = None,
    generation: int,
) -> None:
    async with SessionLocal() as session:
        task = await session.get(EvalTask, task_id)
        if task is None:
            return
        if _current_generation(task_id) != generation:
            log.info(
                "测评跑批 generation 已过期，跳过启动 task_id=%s gen=%s current=%s",
                task_id,
                generation,
                _current_generation(task_id),
            )
            return
        if task.status not in ("PENDING", "RUNNING"):
            log.warning(
                "测评跑批跳过：任务状态不可跑 task_id=%s status=%s gen=%s",
                task_id,
                task.status,
                generation,
            )
            return
        task.status = "RUNNING"
        task.started_at = datetime.now(timezone.utc)
        task.error_message = None
        await session.commit()

        eval_project = await session.get(EvalProject, task.project_id)
        if eval_project is None:
            task.status = "FAILED"
            task.error_message = "测评工程不存在"
            task.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return
        ask_project = await session.get(AskProject, eval_project.ask_project_id)
        if ask_project is None or ask_project.deleted:
            task.status = "FAILED"
            task.error_message = "影子问数工程不存在"
            task.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return

        q = (
            select(EvalTaskCase)
            .where(EvalTaskCase.task_id == task_id)
            .order_by(EvalTaskCase.id.asc())
        )
        if task_case_ids:
            q = q.where(EvalTaskCase.id.in_(task_case_ids))
        cases = (await session.execute(q)).scalars().all()
        pending_ids = [c.id for c in cases if (c.status or "").upper() == "PENDING"]
        if not pending_ids:
            log.warning(
                "测评跑批无 PENDING 用例 task_id=%s gen=%s filter=%s loaded=%s",
                task_id,
                generation,
                task_case_ids,
                [c.id for c in cases],
            )
            if _current_generation(task_id) == generation:
                task.status = "FAILED"
                task.error_message = "没有可执行的 PENDING 用例（可能被上一轮收尾覆盖）"
                task.finished_at = datetime.now(timezone.utc)
                await session.commit()
            return

        # 优先系统应用配置；缺省回退环境/Settings
        conc = int(settings.eval_task_concurrency)
        try:
            from dbc_askdata.app_config.service import get_askdata_runtime_config

            runtime_cfg = await get_askdata_runtime_config(session)
            conc = int(runtime_cfg.eval_task_concurrency)
        except Exception:
            log.warning(
                "读取测评并发配置失败，使用 Settings.eval_task_concurrency=%s",
                conc,
                exc_info=True,
            )
        conc = max(1, min(200, conc))
        log.info("测评任务用例并发 task_id=%s concurrency=%s", task_id, conc)
        sem = asyncio.Semaphore(conc)

        async def _one(tc_id: int) -> None:
            async with sem:
                if is_cancel_requested(task_id) or _current_generation(task_id) != generation:
                    return
                async with SessionLocal() as s2:
                    tc = await s2.get(EvalTaskCase, tc_id)
                    ep = await s2.get(EvalProject, eval_project.id)
                    ap = await s2.get(AskProject, ask_project.id)
                    if tc is None or ep is None or ap is None:
                        return
                    if tc.status not in ("PENDING",):
                        return
                    if _current_generation(task_id) != generation:
                        return
                    sw = SqlworkClient(settings, authorization, trace_id=tc.trace_id or f"eval-{tc_id}")
                    await execute_task_case(
                        s2,
                        settings=settings,
                        llm=llm,
                        sqlwork=sw,
                        eval_project=ep,
                        ask_project=ap,
                        task_case=tc,
                        user_id=user_id,
                        authorization=authorization,
                        cancel_check=lambda: is_cancel_requested(task_id)
                        or _current_generation(task_id) != generation,
                    )

        try:
            await asyncio.gather(*[_one(i) for i in pending_ids])
        except Exception:
            log.error("测评任务跑批异常 task_id=%s gen=%s", task_id, generation, exc_info=True)
            if _current_generation(task_id) != generation:
                return
            task = await session.get(EvalTask, task_id)
            if task:
                task.status = "FAILED"
                task.error_message = "跑批异常，详见服务端日志"
                task.finished_at = datetime.now(timezone.utc)
                await session.commit()
            return

        # 刷新明细并汇总（仅本轮 generation 仍有效时回写）
        if _current_generation(task_id) != generation:
            log.info(
                "测评跑批收尾跳过：已被新一轮取代 task_id=%s gen=%s current=%s",
                task_id,
                generation,
                _current_generation(task_id),
            )
            return

        async with SessionLocal() as s3:
            if _current_generation(task_id) != generation:
                return
            task = await s3.get(EvalTask, task_id)
            if task is None:
                return
            finals = (
                await s3.execute(select(EvalTaskCase).where(EvalTaskCase.task_id == task_id))
            ).scalars().all()
            if is_cancel_requested(task_id):
                for c in finals:
                    if c.status == "PENDING":
                        # 仅取消本轮目标用例：局部跑时未入选的 PENDING 保留待后续启动
                        if not task_case_ids or c.id in task_case_ids:
                            c.status = "CANCELLED"
                task.status = "CANCELLED"
            else:
                failed_hard = any(c.status == "ASK_FAILED" for c in finals) and all(
                    c.status not in ("PENDING", "RUNNING") for c in finals
                )
                # 任务级：全部终态即 SUCCEEDED（含部分失败用例）；取消另计
                task.status = "SUCCEEDED"
                if failed_hard and not finals:
                    task.status = "FAILED"
            task.finished_at = datetime.now(timezone.utc)
            metrics = aggregate_metrics(finals)
            if task.started_at is not None:
                metrics["elapsedMs"] = max(
                    0, int((task.finished_at - task.started_at).total_seconds() * 1000)
                )
            task.metrics_json = metrics
            await s3.commit()
            log.info(
                "测评任务结束 task_id=%s status=%s gen=%s metrics=%s",
                task_id,
                task.status,
                generation,
                task.metrics_json,
            )
