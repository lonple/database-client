from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.verify.semantic import (
    check_eq_literals_against_profiles,
    check_eq_projection,
    store_profile,
)
from dbc_askdata.verify.service import VerifyResult, explain_check, static_check

log = logging.getLogger(__name__)

ProfileFetcher = Callable[[str, str], Awaitable[dict[str, Any] | None]]


async def verify_and_repair(
    *,
    settings: Settings,
    llm: LlmClient,
    sqlwork: SqlworkClient | None,
    sql: str,
    question: str,
    workspace_id: int | None = None,
    connection_id: int | None = None,
    database: str | None = None,
    schema: str | None = None,
    use_explain: bool = True,
    column_profiles: dict[str, Any] | None = None,
    fetch_profile: ProfileFetcher | None = None,
) -> VerifyResult:
    """静态 + 语义（等值投影/枚举画像）+ 可选 EXPLAIN；失败则 LLM 修复。"""
    profiles: dict[str, Any] = dict(column_profiles or {})
    current = sql.strip()
    last = await _full_check(
        current,
        sqlwork=sqlwork,
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
        use_explain=use_explain,
        profiles=profiles,
        fetch_profile=fetch_profile,
    )
    if last.ok:
        return last
    if last.needs_hitl and last.code == "EQ_LITERAL_NOT_IN_PROFILE":
        # 画像已证实码值不对：优先 HITL，不再盲目猜码修复
        return last

    for round_i in range(settings.verify_max_repair_rounds):
        repair_prompt = (
            f"用户问题：{question}\n"
            f"当前 SQL：\n{current}\n\n"
            f"校验错误：{last.message}\n"
            "修复要求：\n"
            "1) 若为明细查询（无聚合、无 GROUP BY），最外层 WHERE 的等值（=/IN）过滤列必须出现在 SELECT 投影中；"
            "范围条件（LIKE/BETWEEN/</>）列不必投影。\n"
            "2) WHERE 离散码值必须来自列画像 value_counts，禁止用用户口语或臆造值。\n"
            "请输出修复后的单条只读 SELECT/WITH SQL，不要解释，不要 Markdown。"
        )
        try:
            resp = await llm.chat_text(
                system="你是 SQL 修复助手。只输出一条合法 SQL。",
                user=repair_prompt,
                temperature=0,
            )
            content = (resp.get("message") or {}).get("content") or ""
            repaired = _extract_sql(content)
            if not repaired:
                last = VerifyResult(False, "修复结果为空")
                continue
            current = repaired
            last = await _full_check(
                current,
                sqlwork=sqlwork,
                workspace_id=workspace_id,
                connection_id=connection_id,
                database=database,
                schema=schema,
                use_explain=use_explain,
                profiles=profiles,
                fetch_profile=fetch_profile,
            )
            if last.ok:
                log.info("SQL 修复成功 round=%s", round_i + 1)
                return last
            if last.needs_hitl and last.code == "EQ_LITERAL_NOT_IN_PROFILE":
                return last
        except Exception:
            log.warning("SQL 修复轮次失败 round=%s", round_i + 1, exc_info=True)
            last = VerifyResult(False, f"修复调用失败 round={round_i + 1}")
    return last


async def _full_check(
    sql: str,
    *,
    sqlwork: SqlworkClient | None,
    workspace_id: int | None,
    connection_id: int | None,
    database: str | None,
    schema: str | None,
    use_explain: bool,
    profiles: dict[str, Any],
    fetch_profile: ProfileFetcher | None,
) -> VerifyResult:
    last = static_check(sql)
    if not last.ok:
        return last
    current = last.dialect_sql or sql

    proj = check_eq_projection(current)
    if proj is not None:
        return VerifyResult(
            False,
            proj.message,
            code=proj.code,
            need_profile=[],
        )

    # 先拉缺失画像，再校验字面量
    lit_issue = check_eq_literals_against_profiles(
        current, profiles, default_schema=schema
    )
    if lit_issue is not None and lit_issue.code == "EQ_LITERAL_NEED_PROFILE" and fetch_profile:
        for item in lit_issue.need_profile:
            table = (item.get("table") or "").strip()
            column = (item.get("column") or "").strip()
            if not column:
                continue
            if not table:
                # 无法定位表则留给 HITL
                continue
            try:
                prof = await fetch_profile(table, column)
            except Exception:
                log.warning("自动拉取列画像失败 table=%s column=%s", table, column, exc_info=True)
                prof = None
            if isinstance(prof, dict):
                store_profile(
                    profiles,
                    table=table,
                    column=column,
                    schema=schema,
                    profile=prof,
                )
        lit_issue = check_eq_literals_against_profiles(
            current, profiles, default_schema=schema
        )

    if lit_issue is not None:
        return VerifyResult(
            False,
            lit_issue.message,
            code=lit_issue.code,
            needs_hitl=lit_issue.needs_hitl
            or lit_issue.code == "EQ_LITERAL_NEED_PROFILE",
            need_profile=lit_issue.need_profile,
        )

    if use_explain and sqlwork and workspace_id and connection_id:
        return await explain_check(
            sqlwork,
            workspace_id=workspace_id,
            connection_id=connection_id,
            sql=current,
            database=database,
            schema=schema,
        )
    return VerifyResult(True, "ok", current)


def parse_workflow_draft(text: str) -> dict[str, Any] | None:
    """从模型输出解析工作流 JSON。"""
    if not text:
        return None
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict):
        return None
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return None
    cleaned = []
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            continue
        ntype = str(n.get("type") or "QUERY").upper()
        if ntype not in ("QUERY", "GOVERN", "SQL"):
            ntype = "QUERY"
        sql = (n.get("sql") or "").strip()
        if not sql:
            continue
        cleaned.append(
            {
                "id": str(n.get("id") or f"n{i + 1}"),
                "type": ntype,
                "title": str(n.get("title") or ntype),
                "sql": sql,
                "readonly": bool(n.get("readonly", ntype == "QUERY")),
            }
        )
    if not cleaned:
        return None
    cleaned[-1]["type"] = "QUERY"
    cleaned[-1]["readonly"] = True
    return {"name": str(data.get("name") or "问数工作流")[:128], "nodes": cleaned}


def _extract_sql(text: str) -> str:
    t = (text or "").strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]*?)```", t, re.I)
    if fence:
        t = fence.group(1).strip()
    t = t.rstrip(";").strip()
    return t
