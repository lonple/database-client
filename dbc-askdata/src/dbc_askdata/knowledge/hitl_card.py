from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.db.models import AskHitl, AskHitlCard
from dbc_askdata.graph.hitl_prompt import physical_table_name

log = logging.getLogger(__name__)

_PROMOTE_KINDS = frozenset({"TABLE", "COLUMN", "EQ_LITERAL"})
_SKIP_KINDS = frozenset({"SCOPE", "REVIEW", "KNOWLEDGE_DOWN"})


def normalize_surface(text: str | None) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip().lower())
    return s[:500]


def _resolution_kind(resolution: dict[str, Any] | None, options: dict[str, Any] | None) -> str:
    if isinstance(resolution, dict):
        k = str(resolution.get("kind") or "").strip().upper()
        if k:
            return k
    ui = (options or {}).get("ui") if isinstance(options, dict) else None
    if isinstance(ui, dict):
        k = str(ui.get("kind") or "").strip().upper()
        if k:
            return k
    return "SCOPE"


def _context_tables(checkpoint_state: dict[str, Any] | None, resolution: dict[str, Any]) -> list[str]:
    out: list[str] = []
    table = physical_table_name(resolution.get("table"))
    if table:
        out.append(table)
    if isinstance(checkpoint_state, dict):
        catalog = checkpoint_state.get("catalog")
        if isinstance(catalog, dict):
            for it in catalog.get("items") or []:
                if isinstance(it, dict) and it.get("name"):
                    name = str(it.get("name")).strip()
                    if name and name not in out:
                        out.append(name)
        confirmed = physical_table_name(checkpoint_state.get("confirmed_table"))
        if confirmed and confirmed not in out:
            out.append(confirmed)
    return out[:20]


def build_hitl_card_fields(
    *,
    hitl: AskHitl,
    resolution: dict[str, Any] | None,
    connection_id: int,
    database: str | None,
    schema: str | None,
    project_id: int | None,
    owner_user_id: int,
    checkpoint_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """从 HITL + resolution 组装卡片字段（不写库）。"""
    opts = hitl.options if isinstance(hitl.options, dict) else {}
    res = resolution if isinstance(resolution, dict) else {}
    kind = _resolution_kind(res, opts)
    question = str(opts.get("question") or hitl.question or "").strip()
    column = str(res.get("column") or "").strip() or None
    text = str(
        res.get("text") or res.get("literal") or res.get("note") or ""
    ).strip()
    table = physical_table_name(res.get("table"))
    if kind == "TABLE" and table is None and text:
        table = physical_table_name(text)
    if kind == "COLUMN" and not column and text and physical_table_name(text) is None:
        # 列名槽位有时只回填 text
        if re.match(r"^[A-Za-z_][\w]*$", text):
            column = text

    surface = ""
    target_value: str | None = None
    if kind == "TABLE":
        surface = question or (table or "")
        target_value = table
    elif kind == "COLUMN":
        surface = question or (column or "")
        target_value = column
    elif kind == "EQ_LITERAL":
        # 码值：surface 尽量保留问句中的业务说法，target_value 为库内码
        surface = question or text
        target_value = text or None
    else:
        surface = question or text
        target_value = text or None

    ctx_tables = _context_tables(checkpoint_state, res)
    if not table and ctx_tables:
        table = ctx_tables[0]

    return {
        "hitl_id": int(hitl.id),
        "session_id": int(hitl.session_id),
        "project_id": project_id,
        "connection_id": int(connection_id),
        "database_name": (database or "").strip() or None,
        "schema_name": (schema or "").strip() or None,
        "kind": kind,
        "surface": surface[:2000],
        "target_table": table,
        "target_column": column,
        "target_value": target_value,
        "question": question or None,
        "payload": {
            "resolution": res,
            "ui": opts.get("ui"),
            "interruptedNode": opts.get("interruptedNode"),
            "contextTables": ctx_tables,
            "promoteEligible": kind in _PROMOTE_KINDS,
        },
        "status": "PENDING" if kind in _PROMOTE_KINDS else "SKIPPED",
        "owner_user_id": int(owner_user_id),
        "promote_meta": None if kind in _PROMOTE_KINDS else {"reason": "kind_not_auto_promote", "kind": kind},
    }


async def save_hitl_card(
    session: AsyncSession,
    *,
    hitl: AskHitl,
    resolution: dict[str, Any] | None,
    connection_id: int,
    database: str | None,
    schema: str | None,
    project_id: int | None,
    owner_user_id: int,
    checkpoint_state: dict[str, Any] | None = None,
) -> AskHitlCard | None:
    """幂等写入确认卡片（同一 hitl_id 只一条）。"""
    if hitl is None or hitl.id is None:
        return None
    existing = (
        await session.execute(select(AskHitlCard).where(AskHitlCard.hitl_id == int(hitl.id)))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    fields = build_hitl_card_fields(
        hitl=hitl,
        resolution=resolution,
        connection_id=connection_id,
        database=database,
        schema=schema,
        project_id=project_id,
        owner_user_id=owner_user_id,
        checkpoint_state=checkpoint_state,
    )
    card = AskHitlCard(**fields)
    session.add(card)
    await session.commit()
    await session.refresh(card)
    log.info(
        "HITL 确认卡片已落库 hitl_id=%s kind=%s status=%s table=%s column=%s",
        card.hitl_id,
        card.kind,
        card.status,
        card.target_table,
        card.target_column,
    )
    return card


async def list_pending_cards(
    session: AsyncSession,
    *,
    session_id: int,
) -> list[AskHitlCard]:
    rows = (
        await session.execute(
            select(AskHitlCard)
            .where(
                AskHitlCard.session_id == int(session_id),
                AskHitlCard.status == "PENDING",
            )
            .order_by(AskHitlCard.id.asc())
        )
    ).scalars().all()
    return list(rows)
