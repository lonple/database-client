from __future__ import annotations

from typing import Any


def physical_table_name(raw: Any) -> str | None:
    """仅接受 schema.table / table 标识符；中文码值、空格、口语不算表名。"""
    s = str(raw or "").strip()
    if not s or len(s) > 128:
        return None
    parts = s.replace('"', "").replace("`", "").split(".")
    if not (1 <= len(parts) <= 2):
        return None
    for p in parts:
        if not p:
            return None
        if not p[0].isascii() or p[0].isdigit():
            return None
        if not all((c.isascii() and (c.isalnum() or c == "_")) for c in p):
            return None
    return ".".join(parts)


def hitl_for_sql_prompt(resolution: dict[str, Any] | None) -> dict[str, Any] | None:
    """把 HITL 确认整理进生成 SQL 的 user 载荷；码值走 text，表名才走 confirmed_table。"""
    if not isinstance(resolution, dict) or not resolution:
        return None
    # 兼容前端分槽：fields 映射后的 text/table/literal/column
    column = str(resolution.get("column") or "").strip()
    text = str(
        resolution.get("text")
        or resolution.get("literal")
        or resolution.get("note")
        or column
        or ""
    ).strip()
    table = physical_table_name(resolution.get("table"))
    # 列名确认时：即使长得像标识符，也不要当成表名
    kind = str(resolution.get("kind") or "").strip().upper()
    if kind != "COLUMN" and table is None and text and not column:
        table = physical_table_name(text)
    if not text and not table and not column:
        return None
    out: dict[str, Any] = {
        "instruction": (
            "这是用户对人机确认的补充，不是新问题。"
            "若补充的是过滤码值或口径（含 SCOPE 自由回答），SQL 必须按用户确认采纳，禁止再用口语缩写。"
            "若补充的是字段名（kind=COLUMN），须用该列写过滤/投影，不要把它当成表名。"
            "仅当补充内容是物理表名（标识符）时才作为选表依据。"
        ),
    }
    if text:
        out["text"] = text
    if column:
        out["column"] = column
    if table:
        out["confirmed_table"] = table
    if kind:
        out["kind"] = kind
    return out
