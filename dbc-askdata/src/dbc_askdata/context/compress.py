from __future__ import annotations

import json
from typing import Any


def estimate_messages_chars(messages: list[dict[str, Any]] | None) -> int:
    if not messages:
        return 0
    try:
        return len(json.dumps(messages, ensure_ascii=False, default=str))
    except Exception:
        return sum(len(str(m)) for m in messages)


def _trim_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 20)] + "…(truncated)"


def slim_tool_result(name: str, result: Any, *, max_chars: int) -> str:
    """按工具类型瘦身后再序列化，避免 describe/knowledge 撑爆轮内上下文。"""
    tool = (name or "").strip()
    slim: Any = result
    if isinstance(result, dict):
        if tool == "describe_table":
            cols_out: list[dict[str, Any]] = []
            for c in result.get("columns") or []:
                if not isinstance(c, dict):
                    continue
                cols_out.append(
                    {
                        "name": c.get("name") or c.get("columnName"),
                        "dataType": c.get("dataType") or c.get("type"),
                        "nullable": c.get("nullable"),
                        "comment": c.get("comment"),
                    }
                )
            kg = result.get("knowledge")
            kg_slim: Any = None
            if isinstance(kg, dict):
                units = []
                for u in (kg.get("units") or [])[:3]:
                    if isinstance(u, dict):
                        units.append(
                            {
                                "title": u.get("title"),
                                "summary": u.get("summary"),
                            }
                        )
                kg_slim = {
                    "query": kg.get("query"),
                    "units": units,
                }
            slim = {"columns": cols_out, "knowledge": kg_slim}
        elif tool == "get_column_profile":
            vcs = []
            for vc in (result.get("value_counts") or [])[:20]:
                if isinstance(vc, dict):
                    vcs.append({"value": vc.get("value"), "count": vc.get("count")})
            slim = {
                "table": result.get("table"),
                "schema": result.get("schema"),
                "column": result.get("column"),
                "row_count": result.get("row_count"),
                "distinct_count": result.get("distinct_count"),
                "null_count": result.get("null_count"),
                "enum_like": result.get("enum_like"),
                "value_counts": vcs,
                "note": result.get("note"),
            }
        elif tool == "search_catalog":
            items = []
            for it in (result.get("items") or [])[:5]:
                if isinstance(it, dict):
                    items.append(
                        {
                            "name": it.get("name"),
                            "description": it.get("description"),
                        }
                    )
            slim = {
                "items": items,
                "query": result.get("query"),
            }
        elif tool in ("sample_columns", "explain_sql"):
            # 执行类结果：保留结构摘要
            if "statements" in result:
                stmts = []
                for st in (result.get("statements") or [])[:2]:
                    if not isinstance(st, dict):
                        continue
                    rows = st.get("rows") or []
                    stmts.append(
                        {
                            "success": st.get("success"),
                            "message": st.get("message"),
                            "columns": st.get("columns"),
                            "rowCount": len(rows) if isinstance(rows, list) else st.get("rowCount"),
                            "rowsSample": rows[:3] if isinstance(rows, list) else None,
                        }
                    )
                slim = {"statements": stmts}
    text = json.dumps(slim, ensure_ascii=False, default=str)
    return _trim_text(text, max_chars)


def fold_working_messages(
    messages: list[dict[str, Any]],
    *,
    budget_chars: int,
    keep_recent_tool_rounds: int = 1,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    超预算时折叠更早的 tool 轮次为一条摘要 user 消息。
    保留：开头 system/首条 user（若有）、以及最近 keep_recent_tool_rounds 个含 tool_calls 的轮次。
    """
    before = estimate_messages_chars(messages)
    meta: dict[str, Any] = {
        "compressed": False,
        "chars_before": before,
        "chars_after": before,
        "folded_tool_rounds": 0,
    }
    if before <= budget_chars or len(messages) < 6:
        return messages, meta

    # 找出 assistant(tool_calls) 的下标
    tool_round_starts: list[int] = []
    for i, m in enumerate(messages):
        if isinstance(m, dict) and m.get("role") == "assistant" and m.get("tool_calls"):
            tool_round_starts.append(i)
    if len(tool_round_starts) <= keep_recent_tool_rounds:
        return messages, meta

    keep_from = tool_round_starts[-keep_recent_tool_rounds]
    head = messages[: tool_round_starts[0]]
    # 折叠中间：从第一个 tool 轮到 keep_from 之前
    middle = messages[tool_round_starts[0] : keep_from]
    tail = messages[keep_from:]

    folded_tools: list[str] = []
    for m in middle:
        if not isinstance(m, dict):
            continue
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m.get("tool_calls") or []:
                fn = (tc.get("function") or {}).get("name")
                if fn:
                    folded_tools.append(str(fn))
        if m.get("role") == "tool":
            # 已计入 tool_calls 名称即可
            pass

    summary_msg = {
        "role": "user",
        "content": (
            "（上下文压缩）更早的探测轮次已折叠，工具调用包括："
            + ("、".join(dict.fromkeys(folded_tools)) if folded_tools else "若干 tool")
            + "。硬事实以近窗用户问句、已确认有用的涉及表与最近探测结果为准；勿依赖已折叠的原始 JSON。"
        ),
    }
    out = [*head, summary_msg, *tail]
    after = estimate_messages_chars(out)
    meta.update(
        {
            "compressed": True,
            "chars_after": after,
            "folded_tool_rounds": max(0, len(tool_round_starts) - keep_recent_tool_rounds),
            "folded_tools": list(dict.fromkeys(folded_tools))[:20],
        }
    )
    return out, meta
