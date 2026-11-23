from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskMessage, AskRunFeedback, AskVerifiedSample, AskWorkflow
from dbc_askdata.graph.sql_tables import source_tables_from_draft

log = logging.getLogger(__name__)

KEEP_WINDOW = 10


async def load_chat_recent_turns(
    session: AsyncSession,
    *,
    session_id: int,
    max_turns: int = KEEP_WINDOW,
) -> list[dict[str, str]]:
    """近窗历史会话（默认 10 条 user/assistant）。CHAT 用全文；QUERY 只取其中 user 问句。"""
    if max_turns <= 0:
        return []
    rows = (
        await session.execute(
            select(AskMessage)
            .where(
                AskMessage.session_id == session_id,
                AskMessage.role.in_(("user", "assistant")),
            )
            .order_by(AskMessage.id.desc())
            .limit(max_turns)
        )
    ).scalars().all()
    turns: list[dict[str, str]] = []
    for m in reversed(rows):
        role = (m.role or "").strip()
        content = (m.content or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if len(content) > 800:
            content = content[:780] + "…(truncated)"
        turns.append({"role": role, "content": content})
    return turns


def user_questions_from_turns(
    recent_turns: list[dict[str, str]] | None,
    *,
    keep: int = KEEP_WINDOW,
) -> list[str]:
    """从近窗对话中抽出用户问句（不含 assistant）。"""
    out: list[str] = []
    for t in recent_turns or []:
        if (t.get("role") or "").strip() != "user":
            continue
        q = (t.get("content") or "").strip()
        if not q:
            continue
        out.append(q)
    if keep > 0 and len(out) > keep:
        out = out[-keep:]
    return out


async def load_verified_sample_tables(
    session: AsyncSession,
    *,
    session_id: int,
    default_schema: str | None = None,
    keep: int = KEEP_WINDOW,
) -> list[dict[str, Any]]:
    """
    QUERY：近窗「有用」样本的涉及表。

    仅统计 AskRunFeedback.useful_done=true 且已关联 sample 的记录；
    按 sample 解析 workflow 源表。不把 SQL 正文、未点有用的表塞进近窗。
    """
    rows = (
        await session.execute(
            select(AskVerifiedSample, AskRunFeedback)
            .join(AskRunFeedback, AskRunFeedback.sample_id == AskVerifiedSample.id)
            .where(
                AskVerifiedSample.session_id == session_id,
                AskRunFeedback.useful_done.is_(True),
            )
            .order_by(AskVerifiedSample.id.desc())
            .limit(max(1, keep))
        )
    ).all()
    out: list[dict[str, Any]] = []
    seen_sample: set[int] = set()
    for sample, _fb in rows:
        if sample.id in seen_sample:
            continue
        seen_sample.add(sample.id)
        wf = await session.get(AskWorkflow, sample.workflow_id)
        tables: list[str] = []
        if wf and isinstance(wf.nodes_json, dict):
            keys = source_tables_from_draft(wf.nodes_json, default_schema=default_schema)
            tables = sorted(keys)
        out.append(
            {
                "sampleId": sample.id,
                "workflowId": sample.workflow_id,
                "question": (sample.question or "")[:200],
                "tables": tables,
            }
        )
    return out


def build_session_prefix_messages(
    *,
    route: str | None,
    recent_turns: list[dict[str, str]] | None,
    verified_samples: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """近窗注入：

    - CHAT：user/assistant 对话原文
    - QUERY（含历史 GOVERN 别名）：用户问句始终带上；表仅来自「执行成功且点有用」的样本
    """
    r = (route or "").upper()
    out: list[dict[str, Any]] = []
    if r == "CHAT":
        if recent_turns:
            lines = [f"{t.get('role')}: {t.get('content')}" for t in recent_turns[:KEEP_WINDOW]]
            out.append({"role": "user", "content": "（近窗对话·最多10条）\n" + "\n".join(lines)})
        return out

    if r in ("QUERY", "GOVERN"):  # GOVERN：历史会话兼容
        questions = user_questions_from_turns(recent_turns, keep=KEEP_WINDOW)
        if questions:
            out.append(
                {
                    "role": "user",
                    "content": (
                        f"（本会话近窗用户问句·最多{KEEP_WINDOW}条）\n"
                        + "\n".join(f"- {q}" for q in questions)
                    ),
                }
            )
        # 只注入表清单；样本上的 question 已由近窗用户问句覆盖，避免重复塞 SQL
        table_rows: list[dict[str, Any]] = []
        seen_tables: set[str] = set()
        ordered_tables: list[str] = []
        for s in (verified_samples or [])[:KEEP_WINDOW]:
            for t in s.get("tables") or []:
                name = str(t or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen_tables:
                    continue
                seen_tables.add(key)
                ordered_tables.append(name)
            if s.get("tables"):
                table_rows.append(
                    {
                        "question": s.get("question"),
                        "tables": list(s.get("tables") or []),
                    }
                )
        if ordered_tables or table_rows:
            out.append(
                {
                    "role": "user",
                    "content": (
                        "（本会话近窗已确认有用·涉及表；写 SQL 时优先考虑这些表，"
                        f"仍须 describe_table 核对。最多{KEEP_WINDOW}条样本。）\n"
                        + json.dumps(
                            {
                                "tables": ordered_tables,
                                "samples": table_rows,
                            },
                            ensure_ascii=False,
                        )
                    ),
                }
            )
    return out


async def load_session_context(
    session: AsyncSession,
    *,
    session_id: int,
    settings: Settings,
) -> dict[str, Any]:
    recent = await load_chat_recent_turns(
        session,
        session_id=session_id,
        max_turns=getattr(settings, "context_recent_turns", KEEP_WINDOW) or KEEP_WINDOW,
    )
    samples = await load_verified_sample_tables(session, session_id=session_id, keep=KEEP_WINDOW)
    return {
        "recent_turns": recent,
        "verified_samples": samples,
    }


async def reset_session_memory(session: AsyncSession, *, session_id: int) -> None:
    # 清空消息时不删已确认样本（样本按 session；若需一并清可扩展）
    _ = session
    _ = session_id
