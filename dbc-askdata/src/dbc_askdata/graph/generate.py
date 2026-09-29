from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.graph.deep_govern import run_deep_govern
from dbc_askdata.graph.tool_agent import run_tool_agent
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.observability.worklog import append_work_log
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.verify.repair import parse_workflow_draft, verify_and_repair

log = logging.getLogger(__name__)

ProgressFn = Callable[[str], Awaitable[None]]


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
    catalog: dict[str, Any]
    route: Literal["CHAT", "QUERY", "GOVERN", "HITL"]
    needs_hitl: bool
    hitl_question: str
    draft: dict[str, Any]
    reply: str
    error: str


ROUTER_SYSTEM = """你是问数路由。根据用户问题与目录摘要，只输出一个 JSON：
{"route":"CHAT|QUERY|GOVERN|HITL","hitl_question":"可选，仅 HITL 时必填","reason":"..."}
规则：
- CHAT：问候、寒暄、感谢、闲聊、与查库无关的普通沟通；直接自然语言回复，禁止 HITL
- QUERY：明确的单表/简单只读问数需求，且信息足够生成 SQL
- GOVERN：需要清洗、多表关联、中间结果落表等治理流程
- HITL：用户明确要查数/分析数据，但缺少表名、指标口径、时间范围等关键信息，必须交互确认
禁止把「你好」一类闲聊打成 HITL。禁止输出其它内容。"""

CHAT_SYSTEM = """你是企业智能问数助手。用户当前是普通沟通（非查数任务）。
用简洁友好的中文回复；可简要提示：描述想查的指标/表/时间范围后，可生成并执行工作流。
不要编造已查询到的数据，不要输出 JSON 或 SQL。"""

BUILD_SYSTEM = """你是企业智能问数 SQL 规划器。只能通过目录摘要与 tools 了解元数据，禁止编造表/列。
可用探测：search_catalog、describe_table、get_column_profile、explain_sql（以 tools 声明为准）。
- 需要列名/类型时调用 describe_table
- 当 WHERE/分组可能依赖状态、类型、性别、码表等离散取值时，先调用 get_column_profile，
  使用返回的 value_counts 真实码值写 SQL；禁止用自然语言猜码（例如把 active 写成「在职」）
- 若不涉及离散码值，不要调用 get_column_profile
- 源表必须用「来源 schema.表名」限定（如 company.hr_employee），禁止未限定表名
最终只输出严格 JSON（不要 Markdown）：
{"name":"工作流名","nodes":[{"id":"n1","type":"QUERY","title":"...","sql":"SELECT ...","readonly":true}]}
要求：单条 SELECT/WITH；末节点 QUERY；不要 EXPLAIN。"""


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
    """LangGraph：gather → router → CHAT|HITL|govern|build → verify → present。"""

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
            s["catalog"] = catalog or {"items": []}
            n = len((s["catalog"] or {}).get("items") or [])
            await progress(f"目录检索完成，可见表约 {n} 张")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_catalog",
                status="OK",
                latency_ms=int((time.monotonic() - t0) * 1000),
                payload_meta={"hit_count": n},
                **ctx,
            )
        except Exception as ex:
            log.warning("gather_context 失败", exc_info=True)
            s["catalog"] = {"items": []}
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
        await spans.record(session, phase="generate", kind="GRAPH", name="gather_context", status="OK", **ctx)
        return s

    async def router(s: GraphState) -> GraphState:
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
        items = (s.get("catalog") or {}).get("items") or []
        user_payload = json.dumps(
            {
                "question": s.get("question"),
                "tables": items[:20],
                "database": s.get("database"),
                "schema": s.get("schema"),
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
        if route == "QUERY" and not items:
            route = "HITL"
            data["hitl_question"] = data.get("hitl_question") or "当前库/模式下未找到表，请确认来源连接作用域或表名。"
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
            ctx=ctx,
            on_progress=progress,
        )
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
        await progress("正在生成 SQL 工作流草稿（模型可按需探测枚举）…")
        items = (s.get("catalog") or {}).get("items") or []
        resolution = s.get("hitl_resolution") or {}
        messages = [
            {"role": "system", "content": BUILD_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": s.get("question"),
                        "catalog": items[:20],
                        "confirmed_table": resolution.get("table"),
                        "workspace_id": s["workspace_id"],
                        "connection_id": s["connection_id"],
                        "database": s.get("database"),
                        "schema": s.get("schema"),
                        "hint": "需要真实码值时再调用 get_column_profile；否则可直接出 SQL。",
                    },
                    ensure_ascii=False,
                ),
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
        )
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
        await progress("正在校验/修复 SQL（含 EXPLAIN）…")
        nodes = list(draft.get("nodes") or [])
        fixed = []
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
            )
            if not result.ok:
                s["error"] = f"节点 {n.get('id')} 校验失败: {result.message}"
                s["reply"] = s["error"]
                s["draft"] = None  # type: ignore[typeddict-item]
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
        await progress("SQL 校验通过")
        await spans.record(session, phase="generate", kind="GRAPH", name="verify", status="OK", **ctx)
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
        s["reply"] = (
            f"已生成工作流草稿「{draft.get('name')}」，共 {len(draft.get('nodes') or [])} 个节点。"
            f"请确认保存后执行。\n\n```sql\n{sql_preview}\n```"
        )
        await progress("草稿已就绪，可保存并执行")
        await spans.record(
            session, phase="generate", kind="GRAPH", name="present_save_and_execute_actions", status="OK", **ctx
        )
        return s

    def after_router(s: GraphState) -> str:
        route = s.get("route")
        if route == "CHAT":
            return "chat"
        if route == "HITL":
            return "hitl"
        if route == "GOVERN":
            return "govern"
        return "build"

    def after_govern(s: GraphState) -> str:
        if s.get("needs_hitl"):
            return "hitl"
        return "verify"

    g = StateGraph(GraphState)
    g.add_node("gather_context", gather_context)
    g.add_node("router", router)
    g.add_node("chat_reply", chat_reply)
    g.add_node("hitl", hitl_node)
    g.add_node("govern_plan", govern_plan)
    g.add_node("build_workflow_draft", build_workflow_draft)
    g.add_node("verify", verify_nodes)
    g.add_node("present", present)
    g.set_entry_point("gather_context")
    g.add_edge("gather_context", "router")
    g.add_conditional_edges(
        "router",
        after_router,
        {"chat": "chat_reply", "hitl": "hitl", "govern": "govern_plan", "build": "build_workflow_draft"},
    )
    g.add_edge("chat_reply", "present")
    g.add_edge("build_workflow_draft", "verify")
    g.add_conditional_edges("govern_plan", after_govern, {"hitl": "hitl", "verify": "verify"})
    g.add_edge("hitl", "present")
    g.add_edge("verify", "present")
    g.add_edge("present", END)
    app = g.compile()
    await progress("开始处理您的请求…")
    return await app.ainvoke(state)
