from __future__ import annotations

import re
from typing import Any

import sqlglot
from sqlglot import exp

_NODE_REF = re.compile(r"^(__node_.+__|n\d+)$", re.I)


def normalize_table_key(table: str, *, default_schema: str | None = None) -> str:
    """统一为 schema.table（小写）；无 schema 时仅 table。"""
    raw = (table or "").strip().strip('"').strip("`").strip("'")
    if not raw:
        return ""
    parts = [p.strip().strip('"').strip("`") for p in raw.replace("..", ".").split(".") if p.strip()]
    if len(parts) >= 2:
        return f"{parts[-2].lower()}.{parts[-1].lower()}"
    name = parts[-1].lower() if parts else ""
    if default_schema and name:
        return f"{default_schema.strip().lower()}.{name}"
    return name


def extract_tables_from_sql(sql: str, *, dialect: str = "postgres") -> set[tuple[str | None, str]]:
    """从 SELECT/WITH 中提取物理表 (schema, name)；忽略解析失败。"""
    text = (sql or "").strip()
    if not text:
        return set()
    try:
        tree = sqlglot.parse_one(text, read=dialect)
    except Exception:
        return set()
    out: set[tuple[str | None, str]] = set()
    for t in tree.find_all(exp.Table):
        name = (t.name or "").strip()
        if not name:
            continue
        schema = (t.db or "").strip() or None
        out.add((schema, name))
    return out


def source_tables_from_draft(
    draft: dict[str, Any] | None,
    *,
    default_schema: str | None = None,
    dialect: str = "postgres",
) -> set[str]:
    """工作流草稿中引用的源业务表（规范化 key），排除节点引用/临时占位。"""
    if not draft:
        return set()
    node_ids = {str(n.get("id") or "").strip().lower() for n in (draft.get("nodes") or []) if isinstance(n, dict)}
    found: set[str] = set()
    for n in draft.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        sql = n.get("sql") or ""
        for schema, name in extract_tables_from_sql(sql, dialect=dialect):
            bare = name.lower()
            if bare in node_ids or _NODE_REF.match(bare):
                continue
            key = normalize_table_key(
                f"{schema}.{name}" if schema else name,
                default_schema=default_schema,
            )
            if key:
                found.add(key)
    return found


def described_key_from_args(args: dict[str, Any], *, default_schema: str | None = None) -> str:
    table = str(args.get("table") or "").strip()
    schema = args.get("schema") or args.get("schema_name") or default_schema
    if "." in table:
        return normalize_table_key(table)
    return normalize_table_key(table, default_schema=str(schema) if schema else None)
