from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.db.models import AskLlmSpan
from dbc_askdata.db.session import get_session
from dbc_askdata.security.auth import require_permission

router = APIRouter(prefix="/api/admin/llm")


@router.get("/spans")
async def list_spans(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    workspace_id: int | None = None,
    project_id: int | None = None,
    kind: str | None = None,
    status: str | None = None,
    trace_id: str | None = None,
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
    total = await session.scalar(count_q)
    rows = (
        await session.execute(q.order_by(AskLlmSpan.id.desc()).offset((page - 1) * size).limit(size))
    ).scalars().all()
    return ApiResponse.ok(
        {
            "page": page,
            "size": size,
            "total": int(total or 0),
            "items": [
                {
                    "id": s.id,
                    "traceId": s.trace_id,
                    "phase": s.phase,
                    "kind": s.kind,
                    "name": s.name,
                    "status": s.status,
                    "latencyMs": s.latency_ms,
                    "model": s.model,
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
                for s in rows
            ],
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
    return ApiResponse.ok(
        {
            "id": s.id,
            "traceId": s.trace_id,
            "parentSpanId": s.parent_span_id,
            "phase": s.phase,
            "kind": s.kind,
            "name": s.name,
            "status": s.status,
            "latencyMs": s.latency_ms,
            "tokenIn": s.token_in,
            "tokenOut": s.token_out,
            "model": s.model,
            "residency": s.residency,
            "payloadMeta": s.payload_meta,
            "errorCode": s.error_code,
            "errorMessage": s.error_message,
            "workspaceId": s.workspace_id,
            "projectId": s.project_id,
            "sessionId": s.session_id,
            "runId": s.run_id,
            "userId": s.user_id,
            "startedAt": s.started_at,
            "finishedAt": s.finished_at,
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
