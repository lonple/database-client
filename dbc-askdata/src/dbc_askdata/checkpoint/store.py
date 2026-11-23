from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.db.models import AskGraphCheckpoint

log = logging.getLogger(__name__)

# 可恢复字段（勿存 authorization 等敏感头）
CHECKPOINT_KEYS = (
    "question",
    "workspace_id",
    "connection_id",
    "database",
    "schema",
    "project_id",
    "session_id",
    "user_id",
    "trace_id",
    "turn_id",
    "catalog",
    "db_general_knowledge",
    "table_intent",
    "intent_gate",
    "route",
    "draft",
    "column_profiles",
    "described_columns",
    "recommended_tables",
    "table_relations",
    "pre_described_tables",
    "review_critique",
    "review_rounds",
    "review_action",
    "verify_critique",
    "verify_rounds",
    "verify_action",
    "recent_turns",
    "verified_samples",
    "interrupted_node",
    "completed_nodes",
)


def snapshot_state_for_checkpoint(state: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in CHECKPOINT_KEYS:
        if k in state and state[k] is not None:
            out[k] = state[k]
    return out


def infer_resume_from(state: dict[str, Any]) -> str:
    """根据打断节点决定续跑入口。"""
    node = str(state.get("interrupted_node") or "").strip()
    # 码值/语义不确定：带确认回同一次 SQL 生成
    if node in ("verify", "review", "build_workflow_draft", "govern_plan"):
        # 查询与治理已并入同一次 SQL 生成
        return "build"
    if node in ("fine_router", "after_router", "hitl"):
        # 已有候选表/关系则可直接回生成；否则重新 gather
        if state.get("recommended_tables") or (state.get("catalog") or {}).get("items"):
            return "build"
        return "gather"
    if node == "gather_context":
        return "gather"
    return "intent_gate"


async def save_interrupted_checkpoint(
    session: AsyncSession,
    *,
    session_id: int,
    hitl_id: int,
    state: dict[str, Any],
) -> AskGraphCheckpoint:
    payload = snapshot_state_for_checkpoint(state)
    interrupted = str(state.get("interrupted_node") or "hitl")
    resume = infer_resume_from({**state, "interrupted_node": interrupted})
    row = AskGraphCheckpoint(
        session_id=session_id,
        hitl_id=hitl_id,
        status="INTERRUPTED",
        interrupted_node=interrupted,
        resume_from=resume,
        state_json=payload,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    log.info(
        "checkpoint 已保存 id=%s hitl_id=%s interrupted=%s resume_from=%s",
        row.id,
        hitl_id,
        interrupted,
        resume,
    )
    return row


async def load_checkpoint_for_hitl(
    session: AsyncSession, *, hitl_id: int
) -> AskGraphCheckpoint | None:
    return (
        await session.execute(
            select(AskGraphCheckpoint)
            .where(
                AskGraphCheckpoint.hitl_id == hitl_id,
                AskGraphCheckpoint.status == "INTERRUPTED",
            )
            .order_by(AskGraphCheckpoint.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def complete_checkpoint(
    session: AsyncSession, *, hitl_id: int, status: str = "COMPLETED"
) -> None:
    """结束中断快照：COMPLETED（续跑成功）或 CANCELLED（用户取消）。"""
    st = (status or "COMPLETED").strip().upper()
    if st not in ("COMPLETED", "CANCELLED"):
        st = "COMPLETED"
    rows = (
        await session.execute(
            select(AskGraphCheckpoint).where(
                AskGraphCheckpoint.hitl_id == hitl_id,
                AskGraphCheckpoint.status == "INTERRUPTED",
            )
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for r in rows:
        r.status = st
        r.updated_at = now
    if rows:
        await session.commit()
