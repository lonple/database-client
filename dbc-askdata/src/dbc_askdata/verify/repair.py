from __future__ import annotations

import json
import logging
import re
from typing import Any

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.verify.service import VerifyResult, explain_check, static_check

log = logging.getLogger(__name__)


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
) -> VerifyResult:
    """静态校验 + 可选 EXPLAIN；失败则 LLM 修复，最多 verify_max_repair_rounds 轮。"""
    current = sql.strip()
    last = static_check(current)
    if last.ok and use_explain and sqlwork and workspace_id and connection_id:
        last = await explain_check(
            sqlwork,
            workspace_id=workspace_id,
            connection_id=connection_id,
            sql=last.dialect_sql or current,
            database=database,
            schema=schema,
        )
        if last.ok:
            return last
    elif last.ok:
        return last

    for round_i in range(settings.verify_max_repair_rounds):
        repair_prompt = (
            f"用户问题：{question}\n"
            f"当前 SQL：\n{current}\n\n"
            f"校验错误：{last.message}\n"
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
            last = static_check(current)
            if not last.ok:
                continue
            if use_explain and sqlwork and workspace_id and connection_id:
                last = await explain_check(
                    sqlwork,
                    workspace_id=workspace_id,
                    connection_id=connection_id,
                    sql=last.dialect_sql or current,
                    database=database,
                    schema=schema,
                )
            if last.ok:
                log.info("SQL 修复成功 round=%s", round_i + 1)
                return last
        except Exception:
            log.warning("SQL 修复轮次失败 round=%s", round_i + 1, exc_info=True)
            last = VerifyResult(False, f"修复调用失败 round={round_i + 1}")
    return last


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
        # 尝试截取第一个 { ... }
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
    # 末节点强制 QUERY 只读
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
