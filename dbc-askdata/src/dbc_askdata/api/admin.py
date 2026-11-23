from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.db.models import AskLlmSpan, AskTurn
from dbc_askdata.db.session import get_session
from dbc_askdata.observability.llm_exchange import extract_llm_rounds
from dbc_askdata.security.auth import require_permission

router = APIRouter(prefix="/api/admin/llm")


def _prompt_version_of(s: AskLlmSpan) -> str:
    meta = s.payload_meta if isinstance(s.payload_meta, dict) else {}
    ver = meta.get("promptVersion")
    if isinstance(ver, str) and ver.strip():
        return ver.strip()
    rounds = meta.get("llmRounds")
    if isinstance(rounds, list):
        for item in rounds:
            if isinstance(item, dict):
                inner = item.get("promptVersion")
                if isinstance(inner, str) and inner.strip():
                    return inner.strip()
    return ""


def _span_item(s: AskLlmSpan) -> dict:
    return {
        "id": s.id,
        "traceId": s.trace_id,
        "turnId": s.turn_id,
        "phase": s.phase,
        "kind": s.kind,
        "name": s.name,
        "status": s.status,
        "latencyMs": s.latency_ms,
        "tokenIn": s.token_in,
        "tokenOut": s.token_out,
        "model": s.model,
        "promptVersion": _prompt_version_of(s),
        "residency": s.residency,
        "workspaceId": s.workspace_id,
        "projectId": s.project_id,
        "sessionId": s.session_id,
        "runId": s.run_id,
        "userId": s.user_id,
        "errorMessage": s.error_message,
        "startedAt": s.started_at,
        "finishedAt": s.finished_at,
    }


def _turn_item(t: AskTurn) -> dict:
    return {
        "id": t.id,
        "rootTraceId": t.root_trace_id,
        "question": t.question,
        "status": t.status,
        "workspaceId": t.workspace_id,
        "projectId": t.project_id,
        "sessionId": t.session_id,
        "userId": t.user_id,
        "hitlId": t.hitl_id,
        "route": t.route,
        "tokenIn": t.token_in,
        "tokenOut": t.token_out,
        "tokenTotal": int(t.token_in or 0) + int(t.token_out or 0),
        "spanCount": t.span_count,
        "latencyMs": t.latency_ms,
        "errorMessage": t.error_message,
        "startedAt": t.started_at,
        "finishedAt": t.finished_at,
    }


@router.get("/turns")
async def list_turns(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    workspace_id: int | None = None,
    project_id: int | None = None,
    status: str | None = None,
    _: object = Depends(require_permission("audit.askdata.view")),
    session: AsyncSession = Depends(get_session),
):
    q = select(AskTurn)
    count_q = select(func.count()).select_from(AskTurn)
    if workspace_id is not None:
        q = q.where(AskTurn.workspace_id == workspace_id)
        count_q = count_q.where(AskTurn.workspace_id == workspace_id)
    if project_id is not None:
        q = q.where(AskTurn.project_id == project_id)
        count_q = count_q.where(AskTurn.project_id == project_id)
    if status:
        q = q.where(AskTurn.status == status)
        count_q = count_q.where(AskTurn.status == status)
    total = await session.scalar(count_q)
    rows = (
        await session.execute(q.order_by(AskTurn.id.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()
    return ApiResponse.ok(
        {
            "page": page,
            "size": size,
            "total": int(total or 0),
            "items": [_turn_item(t) for t in rows],
        }
    )


@router.get("/turns/{turn_id}")
async def turn_detail(
    turn_id: int,
    _: object = Depends(require_permission("audit.askdata.view")),
    session: AsyncSession = Depends(get_session),
):
    t = await session.get(AskTurn, turn_id)
    if t is None:
        return ApiResponse.fail("问数记录不存在")
    return ApiResponse.ok(_turn_item(t))


@router.get("/spans")
async def list_spans(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    workspace_id: int | None = None,
    project_id: int | None = None,
    kind: str | None = None,
    status: str | None = None,
    trace_id: str | None = None,
    turn_id: int | None = None,
    _: object = Depends(require_permission("audit.askdata.view")),
    session: AsyncSession = Depends(get_session),
):
    q = select(AskLlmSpan)
    count_q = select(func.count()).select_from(AskLlmSpan)
    if workspace_id is not None:
        q = q.where(AskLlmSpan.workspace_id == workspace_id)
        count_q = count_q.where(AskLlmSpan.workspace_id == workspace_id)
    if project_id is not None:
        q = q.where(AskLlmSpan.project_id == project_id)
        count_q = count_q.where(AskLlmSpan.project_id == project_id)
    if kind:
        q = q.where(AskLlmSpan.kind == kind)
        count_q = count_q.where(AskLlmSpan.kind == kind)
    if status:
        q = q.where(AskLlmSpan.status == status)
        count_q = count_q.where(AskLlmSpan.status == status)
    if trace_id:
        q = q.where(AskLlmSpan.trace_id == trace_id.strip())
        count_q = count_q.where(AskLlmSpan.trace_id == trace_id.strip())
    if turn_id is not None:
        q = q.where(AskLlmSpan.turn_id == turn_id)
        count_q = count_q.where(AskLlmSpan.turn_id == turn_id)
    total = await session.scalar(count_q)
    rows = (
        await session.execute(q.order_by(AskLlmSpan.id.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()
    return ApiResponse.ok(
        {
            "page": page,
            "size": size,
            "total": int(total or 0),
            "items": [_span_item(s) for s in rows],
        }
    )


@router.get("/spans/{span_id}")
async def span_detail(
    span_id: int,
    _: object = Depends(require_permission("audit.askdata.view")),
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(AskLlmSpan, span_id)
    if s is None:
        return ApiResponse.fail("span 不存在")
    rounds = extract_llm_rounds(s.payload_meta if isinstance(s.payload_meta, dict) else None)
    # 父 GRAPH 若未收口多轮，则从子 LLM span 聚合
    if not rounds:
        child_rows = (
            await session.execute(
                select(AskLlmSpan)
                .where(AskLlmSpan.parent_span_id == span_id, AskLlmSpan.kind == "LLM")
                .order_by(AskLlmSpan.id.asc())
            )
        ).scalars().all()
        for idx, child in enumerate(child_rows):
            child_rounds = extract_llm_rounds(
                child.payload_meta if isinstance(child.payload_meta, dict) else None
            )
            if child_rounds:
                for r in child_rounds:
                    item = dict(r)
                    item.setdefault("step", idx)
                    item.setdefault("childSpanId", child.id)
                    rounds.append(item)
            else:
                rounds.append(
                    {
                        "step": idx,
                        "childSpanId": child.id,
                        "role": child.name,
                        "prompt": [],
                        "response": None,
                        "note": "该子 span 无 prompt/response 记录（历史数据）",
                    }
                )
    return ApiResponse.ok(
        {
            **_span_item(s),
            "parentSpanId": s.parent_span_id,
            "payloadMeta": s.payload_meta,
            "errorCode": s.error_code,
            "llmRounds": rounds,
            "llmRoundCount": len(rounds),
        }
    )


@router.get("/summary")
async def summary(
    hours: int = Query(24, ge=1, le=168),
    _: object = Depends(require_permission("audit.askdata.view")),
    session: AsyncSession = Depends(get_session),
):
    # 简化：按 kind/status 聚合最近 N 小时
    from datetime import timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        await session.execute(
            select(AskLlmSpan.kind, AskLlmSpan.status, func.count(), func.avg(AskLlmSpan.latency_ms))
            .where(AskLlmSpan.started_at >= since)
            .group_by(AskLlmSpan.kind, AskLlmSpan.status)
        )
    ).all()
    return ApiResponse.ok(
        {
            "hours": hours,
            "buckets": [
                {"kind": r[0], "status": r[1], "count": int(r[2]), "avgLatencyMs": float(r[3] or 0)}
                for r in rows
            ],
        }
    )
