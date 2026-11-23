from __future__ import annotations

import logging
import re
from typing import Any

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings

log = logging.getLogger(__name__)

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|CALL|EXECUTE|COPY|MERGE)\b",
    re.IGNORECASE,
)


def assert_readonly_select(sql: str) -> str:
    text = (sql or "").strip().rstrip(";")
    if not text:
        raise ValueError("期望 SQL 为空")
    if ";" in text:
        raise ValueError("期望 SQL 仅允许单条语句")
    head = text.lstrip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        raise ValueError("期望 SQL 必须为 SELECT/WITH")
    if _FORBIDDEN.search(text):
        raise ValueError("期望 SQL 含非只读关键字")
    return text


def normalize_execute_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    """将 sqlwork ExecuteResult（含 statements[]）压成单结果 {columns,rows,rowCount,truncated}。"""
    if not raw:
        return {"columns": [], "rows": [], "rowCount": 0, "truncated": False}
    if isinstance(raw.get("columns"), list) and (
        isinstance(raw.get("rows"), list) or raw.get("rowCount") is not None
    ):
        return {
            "columns": raw.get("columns") or [],
            "rows": raw.get("rows") or [],
            "rowCount": int(raw.get("rowCount") or len(raw.get("rows") or [])),
            "truncated": bool(raw.get("truncated")),
        }
    stmts = raw.get("statements") or raw.get("statementResults") or []
    if isinstance(stmts, list):
        for stmt in stmts:
            if not isinstance(stmt, dict):
                continue
            if stmt.get("success") is False:
                continue
            cols = stmt.get("columns") or []
            rows = stmt.get("rows") or []
            return {
                "columns": cols,
                "rows": rows,
                "rowCount": int(stmt.get("rowCount") or len(rows)),
                "truncated": bool(stmt.get("truncated")),
            }
        # 全部失败时仍取首条便于暴露列/错误信息
        if stmts and isinstance(stmts[0], dict):
            stmt = stmts[0]
            cols = stmt.get("columns") or []
            rows = stmt.get("rows") or []
            return {
                "columns": cols,
                "rows": rows,
                "rowCount": int(stmt.get("rowCount") or len(rows)),
                "truncated": bool(stmt.get("truncated")),
                "message": stmt.get("message") or raw.get("message"),
            }
    return {"columns": [], "rows": [], "rowCount": 0, "truncated": False, "rawKeys": list(raw.keys())}


async def execute_expect_sql(
    *,
    settings: Settings,
    sqlwork: SqlworkClient,
    workspace_id: int,
    connection_id: int,
    database: str | None,
    schema: str | None,
    sql: str,
) -> dict[str, Any]:
    safe = assert_readonly_select(sql)
    try:
        # sqlwork 超时由客户端 timeout 控制；行限与问数对齐
        raw = await sqlwork.execute(
            workspace_id=workspace_id,
            connection_id=connection_id,
            sql=safe,
            max_rows=settings.workflow_run_row_limit,
            database=database,
            schema=schema,
        )
        return normalize_execute_payload(raw if isinstance(raw, dict) else {})
    except Exception:
        log.error("期望 SQL 执行失败 connection_id=%s", connection_id, exc_info=True)
        raise
