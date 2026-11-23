from __future__ import annotations

import re
from typing import Any

from dbc_askdata.graph.sql_tables import extract_tables_from_sql
from dbc_askdata.workflow.runner import flatten_draft_to_inline_sql

# 未展开的节点占位，不得当成物理表
_NODE_REF = re.compile(r"^(__node_.+__|n\d+)$", re.I)


def should_skip_table_select(
    *,
    compare_mode: str | None = None,
    govern_subtype: str | None = None,
) -> str | None:
    """拒绝补充等无需选表的用例：返回跳过原因；否则 None。"""
    mode = (compare_mode or "").strip().lower()
    subtype = (govern_subtype or "").strip().upper()
    if subtype == "HITL_NO_SUPPLEMENT":
        return "hitl_no_supplement"
    if mode == "empty_or_refuse":
        return "empty_or_refuse"
    return None


def table_names_from_sql(sql: str | None, *, dialect: str = "postgres") -> list[str]:
    """解析 SQL 中的物理表名（仅表名小写，忽略 schema），保序去重；剔除节点占位。"""
    found = extract_tables_from_sql(sql or "", dialect=dialect)
    out: list[str] = []
    seen: set[str] = set()
    for _schema, name in sorted(found, key=lambda x: ((x[0] or ""), x[1].lower())):
        bare = (name or "").strip().lower()
        if not bare or bare in seen:
            continue
        if _NODE_REF.match(bare):
            continue
        seen.add(bare)
        out.append(bare)
    return out


def resolve_ask_sql_for_tables(
    *,
    ask_sql: str | None = None,
    draft: dict[str, Any] | None = None,
) -> str | None:
    """
    选表解析用 SQL：多节点草稿先把 ``__node_*`` / ``FROM n1`` 占位内联成子查询，再解析。
    无草稿时回退已落库的 ask_sql（测评路径通常已 flatten）。
    """
    if isinstance(draft, dict) and draft.get("nodes"):
        flat = flatten_draft_to_inline_sql(draft)
        if (flat or "").strip():
            return flat.strip()
    raw = (ask_sql or "").strip()
    return raw or None


def judge_table_select(
    *,
    expect_sql: str | None,
    ask_sql: str | None = None,
    draft: dict[str, Any] | None = None,
    compare_mode: str | None = None,
    govern_subtype: str | None = None,
    dialect: str = "postgres",
) -> dict[str, Any]:
    """
    用例级选表评判：期望 SQL 与问数 SQL（多节点先替换占位）解析出的表名集合是否一致。
    拒绝补充（HITL_NO_SUPPLEMENT / empty_or_refuse）与无 expect_sql 时不计入占比（scored=false）。
    """
    skip = should_skip_table_select(
        compare_mode=compare_mode, govern_subtype=govern_subtype
    )
    ask_resolved = resolve_ask_sql_for_tables(ask_sql=ask_sql, draft=draft)
    ask_tables = table_names_from_sql(ask_resolved, dialect=dialect)

    if skip:
        return {
            "scored": False,
            "ok": None,
            "reason": skip,
            "expectTables": [],
            "askTables": ask_tables,
            "missing": [],
            "extra": [],
            "askSqlResolved": bool(ask_resolved),
        }

    expect_sql_s = (expect_sql or "").strip()
    if not expect_sql_s:
        return {
            "scored": False,
            "ok": None,
            "reason": "no_expect_sql",
            "expectTables": [],
            "askTables": ask_tables,
            "missing": [],
            "extra": [],
            "askSqlResolved": bool(ask_resolved),
        }

    expect_tables = table_names_from_sql(expect_sql_s, dialect=dialect)
    if not expect_tables:
        return {
            "scored": False,
            "ok": None,
            "reason": "expect_sql_no_tables",
            "expectTables": [],
            "askTables": ask_tables,
            "missing": [],
            "extra": [],
            "askSqlResolved": bool(ask_resolved),
        }

    exp_set = set(expect_tables)
    ask_set = set(ask_tables)
    missing = sorted(exp_set - ask_set)
    extra = sorted(ask_set - exp_set)
    ok = not missing and not extra
    return {
        "scored": True,
        "ok": ok,
        "reason": None if ok else "table_mismatch",
        "expectTables": expect_tables,
        "askTables": ask_tables,
        "missing": missing,
        "extra": extra,
        "askSqlResolved": bool(ask_resolved),
    }
