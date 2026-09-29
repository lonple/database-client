from __future__ import annotations

import logging
from typing import Any

import sqlglot
from sqlglot import exp

from dbc_askdata.clients.sqlwork import SqlworkClient

log = logging.getLogger(__name__)


class VerifyResult:
    def __init__(self, ok: bool, message: str = "ok", dialect_sql: str | None = None) -> None:
        self.ok = ok
        self.message = message
        self.dialect_sql = dialect_sql


def static_check(sql: str, *, dialect: str = "postgres") -> VerifyResult:
    text = (sql or "").strip()
    if not text:
        return VerifyResult(False, "SQL 为空")
    if ";" in text.rstrip(";"):
        return VerifyResult(False, "不允许多语句")
    try:
        parsed = sqlglot.parse_one(text, read=dialect)
    except Exception as ex:
        log.warning("sqlglot 解析失败", exc_info=True)
        return VerifyResult(False, f"SQL 解析失败: {ex}")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)
    if isinstance(parsed, forbidden) or any(parsed.find(t) for t in forbidden):
        # 工作流写路径由 Runner 单独校验；生成阶段默认只允许 SELECT/WITH
        if not isinstance(parsed, (exp.Select, exp.Union)) and not text.upper().startswith("WITH"):
            return VerifyResult(False, "生成阶段仅允许 SELECT/WITH")
    try:
        normalized = parsed.sql(dialect=dialect)
    except Exception:
        normalized = text
    return VerifyResult(True, "ok", normalized)


async def explain_check(
    sqlwork: SqlworkClient,
    *,
    workspace_id: int,
    connection_id: int,
    sql: str,
    database: str | None = None,
    schema: str | None = None,
) -> VerifyResult:
    static = static_check(sql)
    if not static.ok:
        return static
    try:
        await sqlwork.execute(
            workspace_id=workspace_id,
            connection_id=connection_id,
            sql=f"EXPLAIN {static.dialect_sql or sql}",
            max_rows=50,
            database=database,
            schema=schema,
        )
        return VerifyResult(True, "EXPLAIN ok", static.dialect_sql)
    except Exception as ex:
        log.warning("EXPLAIN 校验失败", exc_info=True)
        return VerifyResult(False, f"EXPLAIN 失败: {ex}")
