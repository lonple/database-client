from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import (
    AskHitl,
    AskMessage,
    AskProject,
    AskSession,
    AskWorkflow,
    AskWorkflowDraft,
    AskWorkflowRunResult,
)
from dbc_askdata.eval.comparer import compare_results
from dbc_askdata.eval.expect_sql import execute_expect_sql
from dbc_askdata.eval.hitl_policy import build_hitl_resolution, next_hitl_action
from dbc_askdata.eval.models import EvalProject, EvalTaskCase
from dbc_askdata.eval.sql_alias import (
    normalize_count_aliases_in_sql,
    normalize_draft_count_aliases,
    rewrite_required_columns_by_sql,
    rewrite_result_columns_by_sql,
)
from dbc_askdata.eval.table_select import judge_table_select
from dbc_askdata.graph.generate import run_generate_graph
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.observability.turn import (
    TURN_STATUS_CANCELLED,
    TURN_STATUS_ERROR,
    TURN_STATUS_HITL,
    TURN_STATUS_OK,
    begin_turn,
    clear_turn,
    finish_turn,
)
from dbc_askdata.observability.worklog import append_work_log, clear_work_logs, evict_turn_cache
from dbc_askdata.tools.gateway import build_tool_registry
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.workflow.runner import WorkflowRunner, draft_as_single_query, flatten_draft_to_inline_sql
from sqlalchemy import select

log = logging.getLogger(__name__)


def _attach_table_select_judgment(
    task_case: EvalTaskCase,
    *,
    draft: dict[str, Any] | None = None,
) -> None:
    """把选表评判写入 compare_detail_json.tableSelect（不改用例最终 status）。"""
    judgment = judge_table_select(
        expect_sql=task_case.expect_sql,
        ask_sql=task_case.ask_sql,
        draft=draft,
        compare_mode=task_case.compare_mode,
        govern_subtype=task_case.govern_subtype,
    )
    detail = (
        dict(task_case.compare_detail_json)
        if isinstance(task_case.compare_detail_json, dict)
        else {}
    )
    task_case.compare_detail_json = {**detail, "tableSelect": judgment}

MAX_HITL_ROUNDS = 8


def _result_payload(result: AskWorkflowRunResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "columns": result.columns_json or [],
        "rows": result.rows_json or [],
        "rowCount": result.row_count,
        "truncated": bool(result.truncated),
    }


async def execute_task_case(
    session: AsyncSession,
    *,
    settings: Settings,
    llm: LlmClient,
    sqlwork: SqlworkClient,
    eval_project: EvalProject,
    ask_project: AskProject,
    task_case: EvalTaskCase,
    user_id: int,
    authorization: str,
    cancel_check: Any | None = None,
) -> EvalTaskCase:
    """单条测评用例：生成 → HITL 策略 → 自动保存执行 → 期望 SQL 比对。"""
    task_case.status = "RUNNING"
    task_case.started_at = datetime.now(timezone.utc)
    task_case.trace_id = uuid.uuid4().hex
    await session.commit()

    try:
        if cancel_check and cancel_check():
            task_case.status = "CANCELLED"
            task_case.finished_at = datetime.now(timezone.utc)
            await session.commit()
            return task_case

        # 每条用例独立影子会话，避免污染人工 Chat
        ask_session = AskSession(
            project_id=ask_project.id,
            title=f"eval:{task_case.case_key}"[:256],
            owner_user_id=user_id,
            status="ACTIVE",
        )
        session.add(ask_session)
        await session.commit()
        await session.refresh(ask_session)
        task_case.session_id = ask_session.id
        await session.commit()

        await clear_work_logs(ask_session.id)

        # 与会话问数一致：先 begin_turn，再写 work-log（无 turn_id 会被跳过）
        turn = await begin_turn(
            session,
            root_trace_id=task_case.trace_id or uuid.uuid4().hex,
            question=task_case.question,
            workspace_id=eval_project.workspace_id,
            project_id=ask_project.id,
            session_id=ask_session.id,
            user_id=user_id,
        )
        turn_id = int(turn.id)
        await append_work_log(
            ask_session.id,
            f"评测用例 {task_case.case_key}：{(task_case.question or '')[:120]}",
            turn_id=turn_id,
        )

        gateway = ToolGateway(build_tool_registry(settings, sqlwork))
        spans = SpanRecorder(settings)
        hitl_resolution: dict[str, Any] | None = None
        draft: dict[str, Any] | None = None
        refused = False
        hitl_rounds = 0
        turn_status = TURN_STATUS_OK
        turn_error: str | None = None

        try:
            for _round in range(MAX_HITL_ROUNDS + 1):
                if cancel_check and cancel_check():
                    task_case.status = "CANCELLED"
                    task_case.finished_at = datetime.now(timezone.utc)
                    turn_status = TURN_STATUS_CANCELLED
                    await session.commit()
                    return task_case

                state_in: dict[str, Any] = {
                    "question": task_case.question,
                    "workspace_id": eval_project.workspace_id,
                    "connection_id": ask_project.source_connection_id,
                    "database": ask_project.source_database or "",
                    "schema": ask_project.source_schema or "",
                    "project_id": ask_project.id,
                    "session_id": ask_session.id,
                    "user_id": user_id,
                    "trace_id": task_case.trace_id,
                    "turn_id": turn_id,
                    "authorization": authorization,
                    "eval_mode": True,
                }
                if hitl_resolution is not None:
                    state_in["hitl_resolution"] = hitl_resolution

                from dbc_askdata.quota.context import bind_quota, clear_quota

                bind_quota(user_id=user_id, eval_mode=True)
                try:
                    state = await run_generate_graph(
                        settings=settings,
                        session=session,
                        spans=spans,
                        tool_gateway=gateway,
                        sqlwork=sqlwork,
                        llm=llm,
                        state=state_in,  # type: ignore[arg-type]
                    )
                finally:
                    clear_quota()

                session.add(
                    AskMessage(
                        session_id=ask_session.id,
                        role="assistant",
                        content=state.get("reply") or "",
                        content_type="markdown",
                        payload={
                            "evalCaseKey": task_case.case_key,
                            "route": state.get("route"),
                            "turnId": turn_id,
                        },
                    )
                )
                await session.commit()

                if state.get("needs_hitl"):
                    replies = task_case.hitl_replies_json
                    if not isinstance(replies, list):
                        replies = None
                    action, reply_text = next_hitl_action(
                        govern_subtype=task_case.govern_subtype,
                        hitl_replies=replies,
                        hitl_rounds=hitl_rounds,
                    )
                    hitl = AskHitl(
                        session_id=ask_session.id,
                        question=state.get("hitl_question") or "需要确认",
                        status="PENDING",
                        options={
                            "question": task_case.question,
                            "eval": True,
                            "turnId": turn_id,
                        },
                    )
                    session.add(hitl)
                    await session.commit()
                    await session.refresh(hitl)
                    await finish_turn(
                        session,
                        turn_id=turn_id,
                        status=TURN_STATUS_HITL,
                        hitl_id=int(hitl.id),
                        close=False,
                    )

                    if action == "supplement" and reply_text:
                        hitl.status = "RESOLVED"
                        hitl.resolution = build_hitl_resolution(reply_text)
                        hitl.resolved_at = datetime.now(timezone.utc)
                        hitl_rounds += 1
                        task_case.hitl_rounds = hitl_rounds
                        hitl_resolution = hitl.resolution
                        await session.commit()
                        await append_work_log(
                            ask_session.id,
                            f"测评 HITL 补全（第 {hitl_rounds} 轮）：{(reply_text or '')[:200]}",
                            turn_id=turn_id,
                        )
                        continue

                    if action == "refuse":
                        hitl.status = "CANCELLED"
                        await session.commit()
                        refused = True
                        draft = None
                        await append_work_log(
                            ask_session.id,
                            "测评 HITL：按用例策略拒答，不出数",
                            turn_id=turn_id,
                        )
                        break

                    # fail_unexpected
                    hitl.status = "CANCELLED"
                    task_case.status = "ASK_FAILED"
                    task_case.ask_error = "意外 HITL 或补全话术用尽"
                    task_case.finished_at = datetime.now(timezone.utc)
                    turn_status = TURN_STATUS_ERROR
                    turn_error = task_case.ask_error
                    await session.commit()
                    return task_case

                draft = state.get("draft")
                break
            else:
                task_case.status = "ASK_FAILED"
                task_case.ask_error = "HITL 轮次超限"
                task_case.finished_at = datetime.now(timezone.utc)
                turn_status = TURN_STATUS_ERROR
                turn_error = task_case.ask_error
                await session.commit()
                return task_case

            # 测评：与 EXPLAIN/expect_sql 同形态——内联子查询单 SQL；COUNT 投影统一 AS cnt
            inline_draft = None
            ask_sql: str | None = None
            if draft and not refused:
                inline_draft = normalize_draft_count_aliases(draft_as_single_query(draft))
                ask_sql = flatten_draft_to_inline_sql(draft)
                if ask_sql:
                    ask_sql = normalize_count_aliases_in_sql(ask_sql)
                if inline_draft and ask_sql:
                    nodes = list(inline_draft.get("nodes") or [])
                    if nodes and isinstance(nodes[0], dict):
                        inline_draft = {
                            **inline_draft,
                            "nodes": [{**nodes[0], "sql": ask_sql}, *nodes[1:]],
                        }
            task_case.ask_sql = ask_sql
            task_case.hitl_rounds = hitl_rounds

            ask_payload: dict[str, Any] | None = None
            ask_truncated = False

            if refused or not inline_draft:
                ask_payload = {"columns": [], "rows": [], "rowCount": 0, "truncated": False}
                task_case.ask_row_count = 0
            else:
                wf = AskWorkflow(
                    project_id=ask_project.id,
                    name=f"eval-{task_case.case_key}"[:128],
                    description="测评自动保存（内联单 SQL）",
                    nodes_json=inline_draft,
                    owner_user_id=user_id,
                )
                session.add(wf)
                await session.commit()
                await session.refresh(wf)
                task_case.workflow_id = wf.id

                drafts = (
                    await session.execute(
                        select(AskWorkflowDraft).where(
                            AskWorkflowDraft.session_id == ask_session.id,
                            AskWorkflowDraft.owner_user_id == user_id,
                        )
                    )
                ).scalars().all()
                for d in drafts:
                    await session.delete(d)
                await session.commit()

                conns = await sqlwork.list_connections(eval_project.workspace_id)
                work_db_type = "POSTGRESQL"
                for c in conns:
                    if int(c.get("connectionId") or 0) == ask_project.work_connection_id:
                        work_db_type = str(c.get("dbType") or "POSTGRESQL")
                        break

                runner = WorkflowRunner(settings, spans, work_db_type=work_db_type)
                run = await runner.start_run(
                    session,
                    workflow=wf,
                    project=ask_project,
                    sqlwork=sqlwork,
                    user_id=user_id,
                    session_id=ask_session.id,
                    trace_id=task_case.trace_id,
                    authorization=authorization,
                    work_db_type=work_db_type,
                )
                task_case.run_id = run.id
                if run.status != "SUCCESS":
                    task_case.status = "ASK_FAILED"
                    task_case.ask_error = run.error_message or f"run_status={run.status}"
                    _attach_table_select_judgment(task_case, draft=draft)
                    task_case.finished_at = datetime.now(timezone.utc)
                    turn_status = TURN_STATUS_ERROR
                    turn_error = task_case.ask_error
                    await session.commit()
                    return task_case

                result = (
                    await session.execute(
                        select(AskWorkflowRunResult).where(AskWorkflowRunResult.run_id == run.id)
                    )
                ).scalar_one_or_none()
                ask_payload = _result_payload(result)
                ask_truncated = bool(result.truncated) if result else False
                task_case.ask_row_count = (result.row_count if result else 0) or len(
                    (ask_payload or {}).get("rows") or []
                )

            expect_payload: dict[str, Any] | None = None
            if task_case.compare_mode != "empty_or_refuse" and task_case.expect_sql:
                try:
                    expect_payload = await execute_expect_sql(
                        settings=settings,
                        sqlwork=sqlwork,
                        workspace_id=eval_project.workspace_id,
                        connection_id=ask_project.source_connection_id,
                        database=ask_project.source_database,
                        schema=ask_project.source_schema,
                        sql=task_case.expect_sql,
                    )
                    task_case.expect_row_count = int(
                        expect_payload.get("rowCount") or len(expect_payload.get("rows") or [])
                    )
                except Exception as ex:
                    log.error("期望 SQL 失败 case_key=%s", task_case.case_key, exc_info=True)
                    task_case.status = "ASK_FAILED"
                    task_case.ask_error = f"expect_sql: {ex}"
                    _attach_table_select_judgment(task_case, draft=draft)
                    task_case.finished_at = datetime.now(timezone.utc)
                    turn_status = TURN_STATUS_ERROR
                    turn_error = task_case.ask_error
                    await session.commit()
                    return task_case

            cmp_spec = (
                dict(task_case.compare_spec_json)
                if isinstance(task_case.compare_spec_json, dict)
                else {}
            )
            alias_notes: list[str] = []
            if task_case.expect_sql:
                cmp_spec, n0 = rewrite_required_columns_by_sql(cmp_spec, task_case.expect_sql)
                alias_notes.extend([f"required:{x}" for x in n0])
            if expect_payload is not None:
                expect_payload, n1 = rewrite_result_columns_by_sql(
                    expect_payload, task_case.expect_sql
                )
                alias_notes.extend([f"expect:{x}" for x in n1])
            if ask_payload is not None:
                ask_payload, n2 = rewrite_result_columns_by_sql(ask_payload, task_case.ask_sql)
                alias_notes.extend([f"ask:{x}" for x in n2])
            cmp = compare_results(
                expect=expect_payload,
                ask=ask_payload,
                compare_mode=task_case.compare_mode,
                compare_spec=cmp_spec,
                ask_truncated=ask_truncated,
                refused=refused,
            )
            if alias_notes:
                detail = cmp.get("detail") if isinstance(cmp.get("detail"), dict) else {}
                detail = {**detail, "aliasRewrite": alias_notes}
                cmp = {**cmp, "detail": detail}
            task_case.compare_score = Decimal(str(cmp.get("score", 0)))
            task_case.compare_detail_json = cmp.get("detail")
            task_case.status = str(cmp.get("status") or "FAILED_COMPARE")
            _attach_table_select_judgment(task_case, draft=draft)
            task_case.finished_at = datetime.now(timezone.utc)
            if task_case.status == "ASK_FAILED":
                turn_status = TURN_STATUS_ERROR
                turn_error = task_case.ask_error
            await session.commit()
            return task_case
        finally:
            await finish_turn(
                session,
                turn_id=turn_id,
                status=turn_status,
                error_message=turn_error,
                close=True,
            )
            await evict_turn_cache(turn_id)
            clear_turn()
    except Exception as ex:
        log.error("测评用例执行失败 case_key=%s", task_case.case_key, exc_info=True)
        task_case.status = "ASK_FAILED"
        task_case.ask_error = str(ex)[:2000]
        _attach_table_select_judgment(task_case, draft=draft)
        task_case.finished_at = datetime.now(timezone.utc)
        await session.commit()
        return task_case
