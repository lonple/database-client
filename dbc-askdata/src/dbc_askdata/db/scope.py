from __future__ import annotations

from typing import Any


def is_pg_style(db_type: str | None) -> bool:
    t = (db_type or "").lower()
    return "postgres" in t or t == "pg"


def find_connection(conns: list[dict[str, Any]], connection_id: int) -> dict[str, Any] | None:
    for c in conns:
        cid = int(c.get("connectionId") or c.get("id") or 0)
        if cid == connection_id:
            return c
    return None


def normalize_scope(
    *,
    label: str,
    connection_id: int,
    database: str | None,
    schema: str | None,
    db_type: str | None,
) -> tuple[str, str | None]:
    """按库类型校验并归一化 database/schema。返回 (database, schema)。"""
    db = (database or "").strip()
    if not db:
        raise ValueError(f"{label}：请选择库")
    sch = (schema or "").strip() or None
    if is_pg_style(db_type):
        if not sch:
            raise ValueError(f"{label}：PostgreSQL 须选择模式")
        return db, sch
    # MySQL 等：无独立 schema 层级，存空
    return db, None
