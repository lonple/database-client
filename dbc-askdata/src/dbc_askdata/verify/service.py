from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp

from dbc_askdata.clients.sqlwork import SqlworkClient

log = logging.getLogger(__name__)

_ROWS_RE = re.compile(r"rows=(\d+)", re.I)


@dataclass
class ExplainRowStats:
    """EXPLAIN 估算行（观测用；不再用于强制拆 GOVERN）。"""

    rows_peak: int | None = None
    rows_final: int | None = None
    raw_samples: list[int] = field(default_factory=list)


def parse_explain_row_stats(exec_data: dict[str, Any] | None) -> ExplainRowStats:
    """从 sqlwork execute(EXPLAIN ...) 结果中抽取估算行数。"""
    stats = ExplainRowStats()
    if not isinstance(exec_data, dict):
        return stats
    chunks: list[str] = []
    for stmt in exec_data.get("statements") or []:
        if not isinstance(stmt, dict):
            continue
        for row in stmt.get("rows") or []:
            if isinstance(row, (list, tuple)) and row:
                chunks.append(str(row[0]))
            elif isinstance(row, dict):
                chunks.append(str(next(iter(row.values()), "")))
            else:
                chunks.append(str(row))
        for k in ("message", "output", "text"):
            if stmt.get(k):
                chunks.append(str(stmt.get(k)))

    text = "\n".join(chunks)
    rows_from_json: list[int] = []
    for ch in chunks:
        s = ch.strip()
        if not s.startswith("[") and not s.startswith("{"):
            continue
        try:
            data = json.loads(s)
        except Exception:
            continue
        rows_from_json.extend(_walk_plan_rows(data))

    rows_from_text = [int(m.group(1)) for m in _ROWS_RE.finditer(text)]
    all_rows = rows_from_json or rows_from_text
    stats.raw_samples = all_rows
    if not all_rows:
        return stats
    stats.rows_peak = max(all_rows)
    if rows_from_json:
        stats.rows_final = rows_from_json[0]
    else:
        stats.rows_final = all_rows[0]
    return stats


def _walk_plan_rows(node: Any) -> list[int]:
    out: list[int] = []
    if isinstance(node, list):
        for item in node:
            out.extend(_walk_plan_rows(item))
        return out
    if not isinstance(node, dict):
        return out
    plan = node.get("Plan") if "Plan" in node else node
    if isinstance(plan, dict):
        for key in ("Plan Rows", "PlanRows", "rows"):
            if key in plan and plan[key] is not None:
                try:
                    out.append(int(plan[key]))
                except (TypeError, ValueError):
                    pass
        for child in plan.get("Plans") or []:
            out.extend(_walk_plan_rows(child))
    return out


class VerifyResult:
    def __init__(
        self,
        ok: bool,
        message: str = "ok",
        dialect_sql: str | None = None,
        *,
        code: str | None = None,
        needs_hitl: bool = False,
        need_profile: list[dict[str, str]] | None = None,
        auto_added_eq_cols: list[str] | None = None,
        auto_added_group_cols: list[str] | None = None,
        auto_use_key_rewrites: list[str] | None = None,
        explain_rows: ExplainRowStats | None = None,
    ) -> None:
        self.ok = ok
        self.message = message
        self.dialect_sql = dialect_sql
        self.code = code
        self.needs_hitl = needs_hitl
        self.need_profile = need_profile or []
        self.auto_added_eq_cols = auto_added_eq_cols or []
        self.auto_added_group_cols = auto_added_group_cols or []
        self.auto_use_key_rewrites = auto_use_key_rewrites or []
        self.explain_rows = explain_rows


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
    keep_dialect_sql: str | None = None,
) -> VerifyResult:
    """对 sql 做 EXPLAIN（优先 FORMAT JSON 以便抽估算行）；keep_dialect_sql 回传草稿原文。"""
    static = static_check(sql)
    if not static.ok:
        return static
    body_sql = static.dialect_sql or sql
    explain_sql = f"EXPLAIN (FORMAT JSON) {body_sql}"
    try:
        data = await sqlwork.execute(
            workspace_id=workspace_id,
            connection_id=connection_id,
            sql=explain_sql,
            max_rows=50,
            database=database,
            schema=schema,
        )
        rows_stats = parse_explain_row_stats(data if isinstance(data, dict) else None)
        return VerifyResult(
            True,
            "EXPLAIN ok",
            keep_dialect_sql or body_sql,
            explain_rows=rows_stats,
        )
    except Exception:
        log.warning("EXPLAIN FORMAT JSON 失败，回退文本 EXPLAIN", exc_info=True)
        try:
            data = await sqlwork.execute(
                workspace_id=workspace_id,
                connection_id=connection_id,
                sql=f"EXPLAIN {body_sql}",
                max_rows=50,
                database=database,
                schema=schema,
            )
            rows_stats = parse_explain_row_stats(data if isinstance(data, dict) else None)
            return VerifyResult(
                True,
                "EXPLAIN ok",
                keep_dialect_sql or body_sql,
                explain_rows=rows_stats,
            )
        except Exception as ex:
            log.warning("EXPLAIN 校验失败", exc_info=True)
            detail = getattr(ex, "detail", None)
            msg = detail if isinstance(detail, str) and detail.strip() else str(ex)
            return VerifyResult(False, f"EXPLAIN 失败: {msg}")
