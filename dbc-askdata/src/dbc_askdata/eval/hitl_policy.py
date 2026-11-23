from __future__ import annotations

from typing import Any, Literal

from dbc_askdata.graph.hitl_prompt import physical_table_name

HitlAction = Literal["supplement", "refuse", "fail_unexpected"]


def next_hitl_action(
    *,
    govern_subtype: str | None,
    hitl_replies: list[str] | None,
    hitl_rounds: int,
) -> tuple[HitlAction, str | None]:
    """根据治理子类决定 HITL 下一步。

    Returns:
        (action, reply_text)
    """
    subtype = (govern_subtype or "").strip().upper() or None
    replies = [str(x) for x in (hitl_replies or []) if str(x).strip()]

    if subtype == "HITL_SUPPLEMENT":
        if hitl_rounds < len(replies):
            return "supplement", replies[hitl_rounds]
        # 补全话术用尽仍要 HITL → 视为失败
        return "fail_unexpected", None

    if subtype == "HITL_NO_SUPPLEMENT":
        return "refuse", None

    # BOARD 或非治理：意外 HITL
    return "fail_unexpected", None


def build_hitl_resolution(reply: str) -> dict[str, Any]:
    """将预置补全话转为与前端 resolve 兼容的 resolution。"""
    text = (reply or "").strip()
    return {
        "ack": True,
        "text": text,
        "route": "QUERY",
        "table": text if physical_table_name(text) else None,
    }
