from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.db.models import AskTurn

log = logging.getLogger(__name__)

current_turn_id: ContextVar[int | None] = ContextVar("current_turn_id", default=None)

TURN_STATUS_RUNNING = "RUNNING"
TURN_STATUS_HITL = "HITL"
TURN_STATUS_OK = "OK"
TURN_STATUS_ERROR = "ERROR"
TURN_STATUS_CANCELLED = "CANCELLED"


def bind_turn(turn_id: int | None) -> None:
    current_turn_id.set(turn_id)


def clear_turn() -> None:
    current_turn_id.set(None)


def get_bound_turn_id() -> int | None:
    return current_turn_id.get()


async def begin_turn(
    session: AsyncSession,
    *,
    root_trace_id: str,
    question: str,
    workspace_id: int | None = None,
    project_id: int | None = None,
    session_id: int | None = None,
    user_id: int | None = None,
) -> AskTurn:
    row = AskTurn(
        root_trace_id=root_trace_id,
        question=(question or "")[:8000] or "(空)",
        status=TURN_STATUS_RUNNING,
        workspace_id=workspace_id,
        project_id=project_id,
        session_id=session_id,
        user_id=user_id,
        token_in=0,
        token_out=0,
        span_count=0,
        started_at=datetime.now(timezone.utc),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    bind_turn(int(row.id))
    return row


async def resume_turn(
    session: AsyncSession,
    *,
    turn_id: int,
) -> AskTurn | None:
    row = await session.get(AskTurn, turn_id)
    if row is None:
        return None
    row.status = TURN_STATUS_RUNNING
    row.finished_at = None
    row.latency_ms = None
    await session.commit()
    await session.refresh(row)
    bind_turn(int(row.id))
    return row


async def find_turn_by_hitl(
    session: AsyncSession,
    *,
    hitl_options: dict[str, Any] | None,
    hitl_id: int | None = None,
) -> AskTurn | None:
    opts = hitl_options if isinstance(hitl_options, dict) else {}
    raw = opts.get("turnId") or opts.get("turn_id")
    if raw is not None:
        try:
            tid = int(raw)
        except (TypeError, ValueError):
            tid = None
        if tid is not None:
            row = await session.get(AskTurn, tid)
            if row is not None:
                return row
    if hitl_id is not None:
        return (
            await session.execute(select(AskTurn).where(AskTurn.hitl_id == hitl_id).limit(1))
        ).scalar_one_or_none()
    return None


async def finish_turn(
    session: AsyncSession,
    *,
    turn_id: int | None,
    status: str,
    route: str | None = None,
    hitl_id: int | None = None,
    error_message: str | None = None,
    close: bool = True,
) -> None:
    """更新问数回合状态。HITL 等待时 close=False，不写 finished_at。"""
    if turn_id is None:
        return
    try:
        row = await session.get(AskTurn, turn_id)
        if row is None:
            return
        row.status = status
        if route:
            row.route = route[:16]
        if hitl_id is not None:
            row.hitl_id = hitl_id
        if error_message:
            row.error_message = error_message[:1024]
        if close:
            now = datetime.now(timezone.utc)
            row.finished_at = now
            if row.started_at is not None:
                started = row.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                row.latency_ms = max(0, int((now - started).total_seconds() * 1000))
        else:
            row.finished_at = None
            row.latency_ms = None
        await session.commit()
        if close:
            # 入队淘汰：排在本 turn 已入队的 work_log 之后，避免删缓存早于落库
            try:
                from dbc_askdata.observability.obs_queue import enqueue

                await enqueue({"type": "worklog_evict", "turnId": int(turn_id)})
            except Exception:
                log.warning("enqueue worklog_evict failed turn_id=%s", turn_id, exc_info=True)
    except Exception:
        log.warning("finish_turn failed turn_id=%s status=%s", turn_id, status, exc_info=True)
        try:
            await session.rollback()
        except Exception:
            log.warning("finish_turn rollback failed", exc_info=True)


async def add_turn_tokens(
    *,
    turn_id: int | None,
    token_in: int | None,
    token_out: int | None,
    bump_span: bool = True,
) -> None:
    """独立短事务累加 token / span_count，失败只打日志。"""
    if turn_id is None:
        return
    tin = int(token_in or 0)
    tout = int(token_out or 0)
    if tin <= 0 and tout <= 0 and not bump_span:
        return
    try:
        from dbc_askdata.db.session import SessionLocal

        async with SessionLocal() as s:
            values: dict[str, Any] = {}
            if tin > 0:
                values["token_in"] = AskTurn.token_in + tin
            if tout > 0:
                values["token_out"] = AskTurn.token_out + tout
            if bump_span:
                values["span_count"] = AskTurn.span_count + 1
            if not values:
                return
            await s.execute(update(AskTurn).where(AskTurn.id == turn_id).values(**values))
            await s.commit()
    except Exception:
        log.warning("add_turn_tokens failed turn_id=%s", turn_id, exc_info=True)


async def bump_turn_span_count(*, turn_id: int | None) -> None:
    await add_turn_tokens(turn_id=turn_id, token_in=0, token_out=0, bump_span=True)
