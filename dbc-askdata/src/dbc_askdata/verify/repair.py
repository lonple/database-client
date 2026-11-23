from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Protocol

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.verify.condition_match import accept_sql_literal
from dbc_askdata.verify.semantic import (
    check_eq_projection,
    ensure_eq_projection_in_select,
    ensure_group_by_cols_in_select,
    iter_eq_literal_jobs,
    rewrite_use_key_literals,
    store_profile,
)
from dbc_askdata.verify.service import VerifyResult, explain_check, static_check

log = logging.getLogger(__name__)


class ProfileFetcher(Protocol):
    async def __call__(
        self,
        table: str,
        column: str,
        condition_value: str | None = None,
    ) -> dict[str, Any] | None: ...


async def verify_sql(
    *,
    sqlwork: SqlworkClient | None,
    sql: str,
    workspace_id: int | None = None,
    connection_id: int | None = None,
    database: str | None = None,
    schema: str | None = None,
    use_explain: bool = True,
    column_profiles: dict[str, Any] | None = None,
    fetch_profile: ProfileFetcher | None = None,
    explain_sql: str | None = None,
) -> VerifyResult:
    """静态 + 语义（等值投影/枚举画像）+ 可选 EXPLAIN；不内联盲修。

    生成图在失败时应把 SQL+错误回传 build（带工具重写），而非本函数内猜改。
    explain_sql：兼容旧多节点草稿时可将上游占位展开后的 SQL 仅用于 EXPLAIN，草稿仍保留 sql。
    """
    # 原地写入，便于调用方跨节点复用已拉取的列画像
    profiles: dict[str, Any] = column_profiles if column_profiles is not None else {}
    return await _full_check(
        (sql or "").strip(),
        sqlwork=sqlwork,
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
        use_explain=use_explain,
        profiles=profiles,
        fetch_profile=fetch_profile,
        explain_sql=(explain_sql or "").strip() or None,
    )


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
    """静态校验；失败则无工具 LLM 盲修（遗留，生成主路径请用 verify_sql + 回生成）。"""
    profiles: dict[str, Any] = dict(column_profiles or {})
    current = sql.strip()
    last = await verify_sql(
        sqlwork=sqlwork,
        sql=current,
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
        use_explain=use_explain,
        column_profiles=profiles,
        fetch_profile=fetch_profile,
    )
    if last.ok:
        return last

    for round_i in range(settings.verify_max_repair_rounds):
        repair_prompt = (
            f"用户问题：{question}\n"
            f"当前 SQL：\n{current}\n\n"
            f"校验错误：{last.message}\n"
            "修复要求：\n"
            "1) 按校验错误改正 SQL。WHERE 等值/IN 条件须符合 get_column_profile 的 "
            "use_literal/use_key/follow_fk 等判定；格式不一致时换列或跟外键，字典列用 key。\n"
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
            last = await verify_sql(
                sqlwork=sqlwork,
                sql=current,
                workspace_id=workspace_id,
                connection_id=connection_id,
                database=database,
                schema=schema,
                use_explain=use_explain,
                column_profiles=profiles,
                fetch_profile=fetch_profile,
            )
            if last.ok:
                log.info("SQL 修复成功 round=%s", round_i + 1)
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
    explain_sql: str | None = None,
) -> VerifyResult:
    last = static_check(sql)
    if not last.ok:
        return last
    current = last.dialect_sql or sql

    # 代码层自动补全投影：明细等值列、GROUP BY 普通列
    current, auto_eq_cols = ensure_eq_projection_in_select(current)
    if auto_eq_cols:
        log.info("verify auto-added eq projection cols=%s", auto_eq_cols)
    current, auto_group_cols = ensure_group_by_cols_in_select(current)
    if auto_group_cols:
        log.info("verify auto-added group by cols=%s", auto_group_cols)

    proj = check_eq_projection(current)
    if proj is not None:
        return VerifyResult(
            False,
            proj.message,
            code=proj.code,
            need_profile=[],
            auto_added_eq_cols=auto_eq_cols,
            auto_added_group_cols=auto_group_cols,
        )

    # 按 SQL 条件值探测画像；use_key 可代码改写，其余不合规则回灌大模型
    current, use_key_rewrites, lit_err = await _check_eq_literals_with_probe(
        current,
        profiles=profiles,
        schema=schema,
        fetch_profile=fetch_profile,
    )
    if lit_err is not None:
        lit_err.dialect_sql = current
        lit_err.auto_added_eq_cols = list(auto_eq_cols)
        lit_err.auto_added_group_cols = list(auto_group_cols)
        lit_err.auto_use_key_rewrites = list(use_key_rewrites)
        return lit_err
    if use_key_rewrites:
        log.info("verify auto-rewrote use_key literals=%s", use_key_rewrites)

    if use_explain and sqlwork and workspace_id and connection_id:
        explained = await explain_check(
            sqlwork,
            workspace_id=workspace_id,
            connection_id=connection_id,
            sql=explain_sql or current,
            database=database,
            schema=schema,
            keep_dialect_sql=current,
        )
        explained.auto_added_eq_cols = list(auto_eq_cols)
        explained.auto_added_group_cols = list(auto_group_cols)
        explained.auto_use_key_rewrites = list(use_key_rewrites)
        return explained
    return VerifyResult(
        True,
        "ok",
        current,
        auto_added_eq_cols=auto_eq_cols,
        auto_added_group_cols=auto_group_cols,
        auto_use_key_rewrites=use_key_rewrites,
    )


async def _check_eq_literals_with_probe(
    sql: str,
    *,
    profiles: dict[str, Any],
    schema: str | None,
    fetch_profile: ProfileFetcher | None,
) -> tuple[str, list[str], VerifyResult | None]:
    """对每个 WHERE 全等集合字面量：get_column_profile(condition_value) + accept_sql_literal。

    返回 (sql, use_key改写说明, error)。
    - use_key 且 SQL 仍是展示值：代码层改成 key 后放行
    - use_literal / 已是 key：放行
    - 其余不匹配：error（needs_hitl=False，走 regen）
    """
    jobs = iter_eq_literal_jobs(sql)
    if not jobs:
        return sql, [], None

    async def _probe(job: dict[str, str]) -> tuple[dict[str, str], dict[str, Any] | None]:
        table = (job.get("table") or "").strip()
        column = (job.get("column") or "").strip()
        literal = (job.get("literal") or "").strip()
        if not column or not table:
            return job, None
        if fetch_profile is None:
            return job, None
        try:
            prof = await fetch_profile(table, column, literal)
            return job, prof if isinstance(prof, dict) else None
        except TypeError:
            # 兼容旧签名 fetch(table, column)
            try:
                prof = await fetch_profile(table, column)  # type: ignore[call-arg]
                return job, prof if isinstance(prof, dict) else None
            except Exception:
                log.warning(
                    "校验拉取列画像失败 table=%s column=%s literal=%s",
                    table,
                    column,
                    literal,
                    exc_info=True,
                )
                return job, None
        except Exception:
            log.warning(
                "校验拉取列画像失败 table=%s column=%s literal=%s",
                table,
                column,
                literal,
                exc_info=True,
            )
            return job, None

    probed = await asyncio.gather(*[_probe(j) for j in jobs])
    bad: list[str] = []
    need: list[dict[str, str]] = []
    rewrites: list[dict[str, str]] = []
    for job, prof in probed:
        table = (job.get("table") or "").strip()
        column = (job.get("column") or "").strip()
        literal = (job.get("literal") or "").strip()
        if isinstance(prof, dict):
            store_profile(
                profiles,
                table=table,
                column=column,
                schema=schema,
                profile=prof,
            )
        verdict = accept_sql_literal(literal, prof)
        if verdict.get("ok"):
            continue
        action = str(verdict.get("action") or "")
        key = str(verdict.get("key") or "").strip()
        if action == "use_key" and verdict.get("rewritable") and key:
            rewrites.append(
                {"table": table, "column": column, "from": literal, "to": key}
            )
            continue
        msg = str(verdict.get("message") or "")
        label = f"{table}.{column}" if table else column
        bad.append(f"{label}={literal!r}（{action}）: {msg}")
        if action in ("need_profile",) or prof is None:
            need.append({"table": table, "column": column})

    current = sql
    rewrite_labels: list[str] = []
    if rewrites:
        current, rewrite_labels = rewrite_use_key_literals(sql, rewrites)
        if not rewrite_labels:
            # 判定可改写但 AST 未命中：仍打回，避免静默放过错误字面量
            for item in rewrites:
                label = (
                    f"{item['table']}.{item['column']}"
                    if item.get("table")
                    else item["column"]
                )
                bad.append(
                    f"{label}={item['from']!r}（use_key）: 应改为 key={item['to']!r}，"
                    "自动改写未命中 AST，请手动改正。"
                )

    if bad:
        code = "EQ_LITERAL_MISMATCH"
        if need and len(need) == len(bad):
            code = "EQ_LITERAL_NEED_PROFILE"
        return (
            current,
            rewrite_labels,
            VerifyResult(
                False,
                "WHERE 条件值未通过列画像/格式匹配，请按指摘改写 SQL：\n"
                + "\n".join(bad),
                code=code,
                needs_hitl=False,
                need_profile=need,
            ),
        )
    return current, rewrite_labels, None


def parse_workflow_draft(text: str) -> dict[str, Any] | None:
    """从模型输出解析工作流 JSON；归一为单节点 QUERY（多节点/GOVERN 展平内联）。"""
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
        # 兼容模型偶发 GOVERN/SQL；最终统一展平为 QUERY
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
                "readonly": True,
            }
        )
    if not cleaned:
        return None
    draft = {"name": str(data.get("name") or "问数工作流")[:128], "nodes": cleaned}
    if len(cleaned) == 1:
        cleaned[0]["type"] = "QUERY"
        cleaned[0]["readonly"] = True
        return draft
    from dbc_askdata.workflow.runner import draft_as_single_query

    flat = draft_as_single_query(draft)
    return flat or draft


def _extract_sql(text: str) -> str:
    t = (text or "").strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]*?)```", t, re.I)
    if fence:
        t = fence.group(1).strip()
    t = t.rstrip(";").strip()
    return t
