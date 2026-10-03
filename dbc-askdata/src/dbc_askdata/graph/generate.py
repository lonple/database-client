from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.graph.deep_govern import run_deep_govern
from dbc_askdata.graph.hitl_prompt import hitl_for_sql_prompt
from dbc_askdata.graph.sql_review import (
    REVIEW_SYSTEM,
    build_review_user_payload,
    parse_review_verdict,
)
from dbc_askdata.graph.tool_agent import ProgressFn, run_tool_agent
from dbc_askdata.knowledge.general_knowledge import (
    format_catalog_directory_knowledge_for_prompt,
    format_db_general_knowledge_for_prompt,
    search_db_general_knowledge,
)
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.observability.worklog import append_work_log
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.verify.repair import parse_workflow_draft, verify_and_repair

log = logging.getLogger(__name__)

# build / govern 阶段目录已由 gather_context 注入，禁止再查 catalog
_BUILD_EXCLUDE_TOOLS = {"search_catalog", "list_connections"}


class GraphState(TypedDict, total=False):
    question: str
    workspace_id: int
    connection_id: int
    database: str
    schema: str
    project_id: int
    session_id: int
    user_id: int
    trace_id: str
    authorization: str
    hitl_resolution: dict[str, Any]
    eval_mode: bool
    catalog: dict[str, Any]
    # gather_context 检索到的库/模式通用知识（一条），供 SQL 生成提示词追加
    db_general_knowledge: dict[str, Any]
    # search_catalog 旁路命中的「库表目录」切片，供选表消歧
    catalog_directory_knowledge: dict[str, Any]
    route: Literal["CHAT", "QUERY", "GOVERN", "HITL"]
    needs_hitl: bool
    hitl_question: str
    draft: dict[str, Any]
    reply: str
    error: str
    auto_save_ready: bool
    column_profiles: dict[str, Any]
    described_columns: dict[str, list[str]]
    review_critique: str
    review_rounds: int
    review_action: str


ROUTER_SYSTEM = """你是问数路由。根据用户问题、作用域（库/模式）与可见表目录摘要判断意图，只输出一个 JSON：
{"route":"CHAT|QUERY|GOVERN|HITL","hitl_question":"可选，仅 HITL 时必填","reason":"..."}
规则：
- CHAT：问候、寒暄、感谢、闲聊、与查库无关的普通沟通；直接自然语言回复，禁止 HITL
- QUERY：明确的单表/简单只读问数需求；目录中已有候选表时，即使题面未写物理表名也可 QUERY
- GOVERN：需要清洗、多表关联、中间结果落表等治理流程
- HITL：用户明确要查数/分析数据，但结合目录后仍缺少不可推断的关键信息（如必须用户选定的口径），才交互确认
禁止把「你好」一类闲聊打成 HITL。禁止因业务口语（如在职、已付款、质保中）而 HITL——应交由后续探测消歧。
禁止输出其它内容。禁止臆造目录中不存在的表。"""

CHAT_SYSTEM = """你是企业智能问数助手。用户当前是普通沟通（非查数任务）。
用简洁友好的中文回复；可简要提示：描述想查的指标/表/时间范围后，可生成并执行工作流。
不要编造已查询到的数据，不要输出 JSON 或 SQL。"""

BUILD_SYSTEM = """你是企业智能问数 SQL 规划器。只能通过目录摘要与 tools 了解元数据，禁止编造表/列。
可用探测：describe_table、get_column_profile、explain_sql（以 tools 声明为准）。
- 可见表目录已在上下文 catalog 中，禁止调用 search_catalog
- 若上下文含 catalog_directory_knowledge：必须先依据其中「表名↔中文业务含义」与用户话术对齐初选物理表，再 describe；
  禁止凭英文表名猜测或互替含义不同的表
- 若上下文含 hitl_confirmation：这是用户对人机确认的补充；码值/口径用其原文写条件，仅标识符才当表名
- 若上下文含 db_general_knowledge：这是当前库/模式的通用业务知识，生成 SQL 时须遵守其中口径、术语与关联约定
- **强制**：凡 SQL 将引用的每一张源业务表，必须先调用 describe_table 查看列结构（含 knowledge 切片）；
  选列/过滤/关联字段必须来自 describe 返回的 columns，禁止凭记忆臆造列名
- describe_table 若返回 knowledge：须用该表业务说明再次核对是否匹配用户问题；
  明显不符则改选目录中的其它表并重新 describe，禁止在错误表上硬写 SQL
- 当 WHERE/分组可能依赖状态、类型、性别、码表等离散取值时，**必须先**调用 get_column_profile，
  使用返回的 value_counts 真实码值写 SQL；禁止用自然语言猜码（例如把 active 写成「在职」或把用户话术直接当条件值）；
  无法确定码值时不要硬写，应在回复中说明需要人工确认
- 若不涉及离散码值，不要调用 get_column_profile
- **明细查询**（无聚合函数、无 GROUP BY）：最外层 WHERE 中等值条件（= / IN）涉及的列，必须同时出现在 SELECT 投影中；
  范围条件（LIKE、<、>、BETWEEN 等）列不必投影。GOVERN 与 QUERY 节点均遵守。
- 源表必须用「来源 schema.表名」限定（如 company.hr_employee），禁止未限定表名
- 若上下文含 review_critique：必须按其中指出的漏过滤/错粒度改正，禁止原样重出
最终只输出严格 JSON（不要 Markdown）：
{"name":"工作流名","nodes":[{"id":"n1","type":"QUERY","title":"...","sql":"SELECT ...","readonly":true}]}
要求：单条 SELECT/WITH；末节点 QUERY；不要 EXPLAIN。"""


def _catalog_table_names(catalog: dict[str, Any] | None, *, limit: int = 40) -> list[str]:
    items = (catalog or {}).get("items") or []
    names: list[str] = []
    for it in items[:limit]:
        if not isinstance(it, dict):
            continue
        name = it.get("name") or it.get("tableName") or it.get("table_name")
        schema = it.get("schema") or it.get("schemaName") or it.get("tableSchema")
        if name and schema:
            names.append(f"{schema}.{name}")
        elif name:
            names.append(str(name))
    return names


async def run_generate_graph(
    *,
    settings: Settings,
    session: AsyncSession,
    spans: SpanRecorder,
    tool_gateway: ToolGateway,
    sqlwork: SqlworkClient,
    llm: LlmClient,
    state: GraphState,
    on_progress: ProgressFn | None = None,
) -> GraphState:
    """LangGraph：gather_context → router → CHAT|HITL|QUERY|GOVERN → verify → review → present。"""

    ctx = {
        "trace_id": state.get("trace_id"),
        "workspace_id": state.get("workspace_id"),
        "project_id": state.get("project_id"),
        "session_id": state.get("session_id"),
        "user_id": state.get("user_id"),
    }
    sid = state.get("session_id")

    async def progress(msg: str) -> None:
        await append_work_log(sid, msg)
        if on_progress:
            await on_progress(msg)

    async def gather_context(s: GraphState) -> GraphState:
        """入口：检索目录 + 库通用知识，写入 state；QUERY/GOVERN 不再重复 search_catalog。"""
        await progress("正在检索数据目录…")
        t0 = time.monotonic()
        try:
            catalog = await tool_gateway.invoke(
                "search_catalog",
                {
                    "workspace_id": s["workspace_id"],
                    "connection_id": s["connection_id"],
                    "database": s.get("database"),
                    "schema": s.get("schema"),
                    "keyword": None,
                    "page": 1,
                    "size": 30,
                },
            )
            catalog = catalog or {"items": []}
            # 旁路库表目录切片提出到独立 state，避免与 items 混杂且漏进生成提示词
            dir_kg = catalog.get("knowledge") if isinstance(catalog, dict) else None
            if isinstance(dir_kg, dict) and (
                (dir_kg.get("body") or dir_kg.get("summary") or "").strip()
            ):
                s["catalog_directory_knowledge"] = dir_kg
            else:
                s.pop("catalog_directory_knowledge", None)
            if isinstance(catalog, dict):
                slim = dict(catalog)
                slim.pop("knowledge", None)
                s["catalog"] = slim
            else:
                s["catalog"] = {"items": []}
            n = len((s["catalog"] or {}).get("items") or [])
            await progress(
                f"目录检索完成，可见表约 {n} 张"
                + ("；已附带库表目录知识" if s.get("catalog_directory_knowledge") else "")
            )
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_catalog",
                status="OK",
                latency_ms=int((time.monotonic() - t0) * 1000),
                payload_meta={
                    "hit_count": n,
                    "catalog_directory_hit": bool(s.get("catalog_directory_knowledge")),
                    "catalog_directory_refId": (s.get("catalog_directory_knowledge") or {}).get(
                        "refId"
                    ),
                },
                **ctx,
            )
        except Exception as ex:
            log.warning("gather_context 目录检索失败", exc_info=True)
            s["catalog"] = {"items": []}
            s.pop("catalog_directory_knowledge", None)
            s["error"] = str(ex)
            await progress(f"目录检索失败（将尽量继续）：{ex}")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_catalog",
                status="ERROR",
                error_message=str(ex),
                **ctx,
            )

        # 模式名（或库名）+「库通用知识」→ 只取 1 条 GENERAL 切片，供后续 SQL 提示词追加
        await progress("正在检索库通用知识…")
        t1 = time.monotonic()
        try:
            kg = await search_db_general_knowledge(
                settings,
                database=s.get("database"),
                schema=s.get("schema"),
            )
            if kg:
                s["db_general_knowledge"] = kg
                await progress(f"库通用知识已加载：{kg.get('title') or '未命名'}")
            else:
                s.pop("db_general_knowledge", None)
                await progress("未命中库通用知识（将仅依赖目录与表知识）")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_db_general_knowledge",
                status="OK",
                latency_ms=int((time.monotonic() - t1) * 1000),
                payload_meta={
                    "hit": bool(kg),
                    "query": (kg or {}).get("query"),
                    "refId": (kg or {}).get("refId"),
                },
                **ctx,
            )
        except Exception as ex:
            log.warning("gather_context 库通用知识检索失败", exc_info=True)
            s.pop("db_general_knowledge", None)
            await progress(f"库通用知识检索失败（将继续）：{ex}")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_db_general_knowledge",
                status="ERROR",
                error_message=str(ex),
                **ctx,
            )

        await spans.record(session, phase="generate", kind="GRAPH", name="gather_context", status="OK", **ctx)
        return s

    async def router(s: GraphState) -> GraphState:
        """意图判定：可参考 gather 写入的目录摘要。"""
        await progress("正在判断意图（闲聊 / 简单查询 / 治理 / 需确认）…")
        if s.get("hitl_resolution"):
            route = str((s.get("hitl_resolution") or {}).get("route") or "QUERY").upper()
            s["route"] = "GOVERN" if route == "GOVERN" else "QUERY"
            s["needs_hitl"] = False
            await progress(f"已收到确认，继续按 {s['route']} 生成")
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="router",
                status="OK",
                payload_meta={"from_hitl": True, "route": s["route"]},
                **ctx,
            )
            return s
        tables = _catalog_table_names(s.get("catalog"))
        user_payload = json.dumps(
            {
                "question": s.get("question"),
                "database": s.get("database"),
                "schema": s.get("schema"),
                "catalog_tables": tables,
                "catalog_empty": len(tables) == 0,
            },
            ensure_ascii=False,
        )
        resp = await llm.chat_text(system=ROUTER_SYSTEM, user=user_payload, temperature=0)
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name=resp.get("model") or settings.llm_model,
            status="OK",
            latency_ms=resp.get("latency_ms"),
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            **ctx,
        )
        content = (resp.get("message") or {}).get("content") or "{}"
        try:
            data = json.loads(content[content.find("{") : content.rfind("}") + 1])
        except Exception:
            # 解析失败：闲聊倾向走 CHAT，避免误弹 HITL
            q = (s.get("question") or "").strip()
            if len(q) <= 8 or q in ("你好", "您好", "在吗", "嗨", "hello", "hi"):
                data = {"route": "CHAT", "reason": "短问候"}
            else:
                data = {"route": "HITL", "hitl_question": "请补充要查询的表或指标（例如：各部门在职人数）。"}
        route = str(data.get("route") or "CHAT").upper()
        if route not in ("CHAT", "QUERY", "GOVERN", "HITL"):
            route = "CHAT"
        s["route"] = route  # type: ignore[assignment]
        if route == "HITL":
            s["needs_hitl"] = True
            s["hitl_question"] = str(data.get("hitl_question") or "请确认查询对象（表名/指标/时间范围）。")
        await progress(f"意图判定：{route}" + (f"；{data.get('reason')}" if data.get("reason") else ""))
        await spans.record(
            session,
            phase="generate",
            kind="GRAPH",
            name="router",
            status="OK",
            payload_meta={"route": route},
            **ctx,
        )
        return s

    async def chat_reply(s: GraphState) -> GraphState:
        await progress("普通沟通：正在生成回复…")
        s["needs_hitl"] = False
        resp = await llm.chat_text(
            system=CHAT_SYSTEM,
            user=str(s.get("question") or ""),
            temperature=0.4,
        )
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name=resp.get("model") or settings.llm_model,
            status="OK",
            latency_ms=resp.get("latency_ms"),
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            **ctx,
        )
        s["reply"] = ((resp.get("message") or {}).get("content") or "").strip() or (
            "您好！我是智能问数助手。直接描述要查的数据即可，例如「各部门在职员工人数」。"
        )
        await progress("闲聊回复完成")
        await spans.record(session, phase="generate", kind="GRAPH", name="chat_reply", status="OK", **ctx)
        return s

    async def hitl_node(s: GraphState) -> GraphState:
        s["needs_hitl"] = True
        s["reply"] = s.get("hitl_question") or "需要您确认后继续。"
        await progress("等待您确认关键信息（表名/口径）…")
        await spans.record(session, phase="generate", kind="HITL", name="await_user", status="OK", **ctx)
        return s

    async def govern_plan(s: GraphState) -> GraphState:
        await progress("复杂治理：正在规划多表清洗与落表步骤…")
        profiles = dict(s.get("column_profiles") or {})
        described_cols = dict(s.get("described_columns") or {})
        draft = await run_deep_govern(
            settings=settings,
            llm=llm,
            gateway=tool_gateway,
            spans=spans,
            session=session,
            question=s.get("question") or "",
            workspace_id=s["workspace_id"],
            connection_id=s["connection_id"],
            database=s.get("database"),
            schema=s.get("schema"),
            catalog_hint=s.get("catalog"),
            db_general_knowledge=s.get("db_general_knowledge"),
            catalog_directory_knowledge=s.get("catalog_directory_knowledge"),
            hitl_resolution=s.get("hitl_resolution"),
            ctx=ctx,
            on_progress=progress,
            column_profiles=profiles,
            described_columns=described_cols,
            review_critique=s.get("review_critique"),
        )
        s["column_profiles"] = profiles
        s["described_columns"] = described_cols
        if not draft:
            s["needs_hitl"] = True
            s["hitl_question"] = "复杂治理未能自动规划，请补充表关系或简化问题。"
            s["reply"] = s["hitl_question"]
            await progress("治理规划失败，需要您补充信息")
            return s
        s["draft"] = draft
        await progress(f"治理草稿已生成，节点数 {len(draft.get('nodes') or [])}")
        await spans.record(session, phase="generate", kind="GRAPH", name="govern_plan", status="OK", **ctx)
        return s

    async def build_workflow_draft(s: GraphState) -> GraphState:
        if s.get("draft"):
            return s
        await progress("正在生成 SQL 工作流草稿（涉表须先 describe_table）…")
        items = (s.get("catalog") or {}).get("items") or []
        profiles = dict(s.get("column_profiles") or {})
        described_cols = dict(s.get("described_columns") or {})
        user_payload: dict[str, Any] = {
            "question": s.get("question"),
            "catalog": items[:20],
            "workspace_id": s["workspace_id"],
            "connection_id": s["connection_id"],
            "database": s.get("database"),
            "schema": s.get("schema"),
            "hint": (
                "catalog 只含物理表名；若有 catalog_directory_knowledge，须先对照其中中文含义初选表，再 describe。"
                "describe_table 返回的 knowledge 须再次核对表意是否匹配用户问题，不符则换表重探。"
                "若有 hitl_confirmation，优先按其 text 写过滤字面量；confirmed_table 仅在其为物理表名时采用。"
                "写 SQL 前必须对每张涉表调用 describe_table；列名只能来自 describe 结果。"
                "需要真实码值必须先 get_column_profile。"
                "明细查询须把最外层等值 WHERE 列投影到 SELECT。"
            ),
        }
        if s.get("review_critique"):
            user_payload["review_critique"] = s.get("review_critique")
        hitl_prompt = hitl_for_sql_prompt(s.get("hitl_resolution"))
        if hitl_prompt:
            user_payload["hitl_confirmation"] = hitl_prompt
            if hitl_prompt.get("confirmed_table"):
                user_payload["confirmed_table"] = hitl_prompt["confirmed_table"]
        dir_prompt = format_catalog_directory_knowledge_for_prompt(
            s.get("catalog_directory_knowledge")
        )
        if dir_prompt:
            user_payload["catalog_directory_knowledge"] = dir_prompt
        kg_prompt = format_db_general_knowledge_for_prompt(s.get("db_general_knowledge"))
        if kg_prompt:
            user_payload["db_general_knowledge"] = kg_prompt
        messages = [
            {"role": "system", "content": BUILD_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ]
        draft = await run_tool_agent(
            settings=settings,
            llm=llm,
            gateway=tool_gateway,
            spans=spans,
            session=session,
            messages=messages,
            workspace_id=s["workspace_id"],
            connection_id=s["connection_id"],
            database=s.get("database"),
            schema=s.get("schema"),
            ctx=ctx,
            parent_span_name="build_workflow_draft",
            max_steps=settings.llm_max_tool_rounds,
            on_progress=progress,
            on_final_content=parse_workflow_draft,
            exclude_tools=_BUILD_EXCLUDE_TOOLS,
            require_describe_tables=True,
            column_profiles=profiles,
            described_columns=described_cols,
        )
        s["column_profiles"] = profiles
        s["described_columns"] = described_cols
        if not draft:
            s["error"] = "模型未产出合法工作流 JSON"
            s["reply"] = "生成失败：模型输出无法解析为工作流，请重试或简化问题。"
            await progress("SQL 草稿解析失败")
            await spans.record(
                session, phase="generate", kind="GRAPH", name="build_workflow_draft", status="ERROR", **ctx
            )
            return s
        s["draft"] = draft
        await progress(f"草稿生成完成：{draft.get('name')}（{len(draft.get('nodes') or [])} 节点）")
        await spans.record(session, phase="generate", kind="GRAPH", name="build_workflow_draft", status="OK", **ctx)
        return s

    async def verify_nodes(s: GraphState) -> GraphState:
        draft = s.get("draft")
        if not draft:
            return s
        await progress("正在校验/修复 SQL（投影、画像、EXPLAIN）…")
        nodes = list(draft.get("nodes") or [])
        fixed = []
        profiles = dict(s.get("column_profiles") or {})

        async def fetch_profile(table: str, column: str) -> dict[str, Any] | None:
            await progress(f"校验前拉取列画像：{table}.{column}")
            args: dict[str, Any] = {
                "workspace_id": s["workspace_id"],
                "connection_id": s["connection_id"],
                "table": table,
                "column": column,
            }
            if s.get("database"):
                args["database"] = s["database"]
            if s.get("schema"):
                args["schema"] = s["schema"]
            return await tool_gateway.invoke("get_column_profile", args)

        for idx, n in enumerate(nodes, start=1):
            sql = n.get("sql") or ""
            await progress(f"校验节点 {idx}/{len(nodes)}：{n.get('title') or n.get('id')}")
            result = await verify_and_repair(
                settings=settings,
                llm=llm,
                sqlwork=sqlwork,
                sql=sql,
                question=s.get("question") or "",
                workspace_id=s["workspace_id"],
                connection_id=s["connection_id"],
                database=s.get("database"),
                schema=s.get("schema"),
                use_explain=True,
                column_profiles=profiles,
                fetch_profile=fetch_profile,
            )
            if not result.ok:
                if result.needs_hitl:
                    s["needs_hitl"] = True
                    s["hitl_question"] = (
                        "过滤条件码值无法自动确认："
                        f"{result.message} "
                        "请提供该字段的真实取值（不要用口语描述），或说明口径。"
                    )
                    s["reply"] = s["hitl_question"]
                    s["draft"] = None  # type: ignore[typeddict-item]
                    s["column_profiles"] = profiles
                    await progress("码值不确定，需人工确认")
                    await spans.record(
                        session,
                        phase="generate",
                        kind="HITL",
                        name="verify_enum_hitl",
                        status="OK",
                        error_message=result.message,
                        **ctx,
                    )
                    return s
                s["error"] = f"节点 {n.get('id')} 校验失败: {result.message}"
                s["reply"] = s["error"]
                s["draft"] = None  # type: ignore[typeddict-item]
                s["column_profiles"] = profiles
                await progress(f"节点校验失败：{result.message}")
                await spans.record(
                    session,
                    phase="generate",
                    kind="GRAPH",
                    name="verify",
                    status="ERROR",
                    error_message=result.message,
                    **ctx,
                )
                return s
            n = dict(n)
            n["sql"] = result.dialect_sql or sql
            fixed.append(n)
        draft = dict(draft)
        draft["nodes"] = fixed
        s["draft"] = draft
        s["column_profiles"] = profiles
        await progress("SQL 校验通过")
        await spans.record(session, phase="generate", kind="GRAPH", name="verify", status="OK", **ctx)
        return s

    async def review_sql(s: GraphState) -> GraphState:
        if s.get("needs_hitl") or s.get("error") or not s.get("draft"):
            return s
        await progress("正在语义评审 SQL 是否覆盖用户话术…")
        user_payload = json.dumps(build_review_user_payload(s), ensure_ascii=False)
        try:
            resp = await llm.chat_text(
                system=REVIEW_SYSTEM,
                user=user_payload,
                temperature=0,
            )
        except Exception:
            log.warning("SQL 语义评审调用失败，按通过处理", exc_info=True)
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="review_sql",
                status="ERROR",
                error_message="LLM 评审调用失败，已放行",
                **ctx,
            )
            s["review_action"] = "pass"
            return s
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name=resp.get("model") or settings.llm_model,
            status="OK",
            latency_ms=resp.get("latency_ms"),
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            **ctx,
        )
        content = (resp.get("message") or {}).get("content") or ""
        verdict = parse_review_verdict(content)
        s["review_action"] = verdict.action
        if verdict.action == "pass":
            await progress("语义评审通过")
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="review_sql",
                status="OK",
                payload_meta={"action": "pass"},
                **ctx,
            )
            return s
        if verdict.action == "hitl":
            s["needs_hitl"] = True
            s["hitl_question"] = verdict.hitl_question or verdict.critique
            s["reply"] = s["hitl_question"]
            s["draft"] = None  # type: ignore[typeddict-item]
            await progress("语义评审：需人工确认")
            await spans.record(
                session,
                phase="generate",
                kind="HITL",
                name="review_sql",
                status="OK",
                error_message=verdict.critique,
                **ctx,
            )
            return s
        rounds = int(s.get("review_rounds") or 0)
        if rounds >= settings.sql_review_max_regen:
            s["needs_hitl"] = True
            s["review_action"] = "hitl"
            s["hitl_question"] = (
                "语义评审仍认为 SQL 未覆盖话术，且已达重写上限。"
                f"{verdict.critique} 请确认实体或口径。"
            )
            s["reply"] = s["hitl_question"]
            s["draft"] = None  # type: ignore[typeddict-item]
            await progress("语义评审重写次数已用尽，需人工确认")
            await spans.record(
                session,
                phase="generate",
                kind="HITL",
                name="review_sql",
                status="OK",
                error_message=verdict.critique,
                payload_meta={"action": "hitl", "rounds": rounds},
                **ctx,
            )
            return s
        s["review_rounds"] = rounds + 1
        s["review_critique"] = verdict.critique
        s["draft"] = None  # type: ignore[typeddict-item]
        await progress(f"语义评审未通过，回退重写草稿：{verdict.critique[:80]}")
        await spans.record(
            session,
            phase="generate",
            kind="GRAPH",
            name="review_sql",
            status="OK",
            payload_meta={"action": "regen", "rounds": s["review_rounds"]},
            error_message=verdict.critique,
            **ctx,
        )
        return s

    async def present(s: GraphState) -> GraphState:
        if s.get("route") == "CHAT":
            await progress("本轮为普通会话，已回复")
            return s
        if s.get("needs_hitl"):
            s["reply"] = s.get("hitl_question") or s.get("reply") or "需要确认"
            return s
        draft = s.get("draft")
        if not draft:
            s["reply"] = s.get("reply") or s.get("error") or "未生成草稿"
            await progress("未生成可执行草稿")
            return s
        sql_preview = "\n\n".join(
            f"-- {n.get('title') or n.get('id')} ({n.get('type')})\n{n.get('sql')}" for n in draft.get("nodes") or []
        )
        if s.get("eval_mode"):
            s["auto_save_ready"] = True
            s["reply"] = (
                f"测评模式已生成工作流「{draft.get('name')}」，"
                f"共 {len(draft.get('nodes') or [])} 个节点，将自动保存并执行。\n\n"
                f"```sql\n{sql_preview}\n```"
            )
            await progress("测评草稿已就绪，自动保存执行")
            await spans.record(
                session, phase="generate", kind="GRAPH", name="present_eval_auto_save", status="OK", **ctx
            )
            return s
        s["reply"] = (
            f"已生成工作流草稿「{draft.get('name')}」，共 {len(draft.get('nodes') or [])} 个节点。"
            f"请确认保存后执行。\n\n```sql\n{sql_preview}\n```"
        )
        await progress("草稿已就绪，可保存并执行")
        await spans.record(
            session, phase="generate", kind="GRAPH", name="present_save_and_execute_actions", status="OK", **ctx
        )
        return s

    def after_gather(_s: GraphState) -> str:
        return "router"

    def after_router(s: GraphState) -> str:
        route = s.get("route")
        if route == "CHAT":
            return "chat"
        items = (s.get("catalog") or {}).get("items") or []
        if route in ("QUERY", "GOVERN") and not items:
            s["route"] = "HITL"
            s["needs_hitl"] = True
            s["hitl_question"] = "当前库/模式下未找到表，请确认来源连接作用域或表名。"
            s["reply"] = s["hitl_question"]
            return "hitl"
        if route == "HITL" or s.get("needs_hitl"):
            return "hitl"
        if route == "GOVERN":
            return "govern"
        return "build"

    def after_govern(s: GraphState) -> str:
        if s.get("needs_hitl"):
            return "hitl"
        return "verify"

    def after_verify(s: GraphState) -> str:
        if s.get("needs_hitl") or s.get("error") or not s.get("draft"):
            return "present"
        return "review"

    def after_review(s: GraphState) -> str:
        if s.get("needs_hitl"):
            return "hitl"
        if s.get("review_action") == "regen":
            if s.get("route") == "GOVERN":
                return "govern"
            return "build"
        return "present"

    g = StateGraph(GraphState)
    g.add_node("gather_context", gather_context)
    g.add_node("router", router)
    g.add_node("chat_reply", chat_reply)
    g.add_node("hitl", hitl_node)
    g.add_node("govern_plan", govern_plan)
    g.add_node("build_workflow_draft", build_workflow_draft)
    g.add_node("verify", verify_nodes)
    g.add_node("review", review_sql)
    g.add_node("present", present)
    g.set_entry_point("gather_context")
    g.add_conditional_edges("gather_context", after_gather, {"router": "router"})
    g.add_conditional_edges(
        "router",
        after_router,
        {"chat": "chat_reply", "hitl": "hitl", "govern": "govern_plan", "build": "build_workflow_draft"},
    )
    g.add_edge("chat_reply", "present")
    g.add_edge("build_workflow_draft", "verify")
    g.add_conditional_edges("govern_plan", after_govern, {"hitl": "hitl", "verify": "verify"})
    g.add_edge("hitl", "present")
    g.add_conditional_edges(
        "verify",
        after_verify,
        {"review": "review", "present": "present"},
    )
    g.add_conditional_edges(
        "review",
        after_review,
        {"hitl": "hitl", "govern": "govern_plan", "build": "build_workflow_draft", "present": "present"},
    )
    g.add_edge("present", END)
    app = g.compile()
    await progress("开始处理您的请求…")
    return await app.ainvoke(state)

