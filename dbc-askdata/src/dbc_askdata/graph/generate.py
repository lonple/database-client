from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.context.session_context import (
    KEEP_WINDOW,
    build_session_prefix_messages,
    user_questions_from_turns,
)
from dbc_askdata.graph.hitl_prompt import hitl_for_sql_prompt, physical_table_name
from dbc_askdata.graph.time_context import current_time_context, current_time_system_suffix
from dbc_askdata.graph.tool_agent import ProgressFn, run_tool_agent
from dbc_askdata.knowledge.ask_catalog_search import search_ask_catalog
from dbc_askdata.knowledge.general_knowledge import (
    format_db_general_knowledge_for_prompt,
    search_db_general_knowledge,
    unwrap_general_knowledge_result,
)
from dbc_askdata.knowledge.sql_ex_knowledge import (
    format_sql_ex_knowledge_for_prompt,
    load_sql_ex_knowledge,
)
from dbc_askdata.knowledge.table_intent import (
    ROLE_TABLE,
    normalize_entity_role,
    parse_table_intent_pairs,
    resolve_table_intent_query,
)
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.llm_exchange import build_llm_rounds_meta
from dbc_askdata.observability.spans import ScopeTimer, SpanRecorder
from dbc_askdata.observability.worklog import append_work_log
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.verify.repair import parse_workflow_draft, verify_sql
from dbc_askdata.workflow.runner import expand_node_refs_for_explain

log = logging.getLogger(__name__)

# build 阶段目录已由 gather_context 注入，禁止再查 catalog
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
    turn_id: int
    authorization: str
    hitl_resolution: dict[str, Any]
    eval_mode: bool
    catalog: dict[str, Any]
    # gather_context 检索到的库/模式通用知识（一条），供 SQL 生成提示词追加
    db_general_knowledge: dict[str, Any]
    # SQL_EX 分类已发布原文（不分片），供 SQL 生成参考
    sql_ex_knowledge: list[dict[str, Any]]
    # 大模型抽取的中文表意图（供语义找表）
    table_intent: dict[str, Any]
    # 轻量意图门闩：CHAT 闲聊短路；DATA 再抽实体/找表/细路由
    intent_gate: Literal["CHAT", "DATA"]
    route: Literal["CHAT", "QUERY", "HITL"]
    needs_hitl: bool
    hitl_question: str
    # HITL 表单类型：TABLE|COLUMN|EQ_LITERAL|SCOPE|REVIEW|…；空则由 hitl_ui 推断
    hitl_kind: str
    draft: dict[str, Any]
    reply: str
    error: str
    auto_save_ready: bool
    column_profiles: dict[str, Any]
    described_columns: dict[str, list[str]]
    # 找表结果表名列表；图谱邻接表关系（注入 build）
    recommended_tables: list[str]
    table_relations: list[dict[str, Any]]
    # 遗留字段：不再预 describe，保持空列表以兼容断点
    pre_described_tables: list[dict[str, Any]]
    review_critique: str
    review_rounds: int
    review_action: str
    # 机械校验失败 → 带 SQL+错误回生成
    verify_critique: str
    verify_rounds: int
    verify_action: str
    # 会话上下文：CHAT 近窗 / QUERY 已验证样本表名
    recent_turns: list[dict[str, str]]
    verified_samples: list[dict[str, Any]]
    # 企业级断点续跑
    resume_from: str
    interrupted_node: str
    completed_nodes: list[str]


# 提示词已迁至 llm/providers/<provider>/prompts/；此处仅作极端回退
_FALLBACK_GATE = "你是问数入口。只输出 JSON：{\"gate\":\"CHAT|DATA\",\"entities\":[]}。"


def _table_intent_from_pairs(
    pairs: list[dict[str, str]],
    *,
    question: str,
    source: str,
) -> dict[str, Any]:
    entity_pairs = [p for p in pairs if isinstance(p, dict)]
    table_zh = [
        str(p.get("entity") or "").strip()
        for p in entity_pairs
        if str(p.get("entity") or "").strip()
        and normalize_entity_role(p.get("role")) == ROLE_TABLE
    ]
    zh_list = [
        str(p.get("entity") or "").strip()
        for p in entity_pairs
        if str(p.get("entity") or "").strip()
    ]
    en_list = [
        str(p.get("english") or "").strip()
        for p in entity_pairs
        if str(p.get("english") or "").strip()
    ]
    first = next(
        (p for p in entity_pairs if normalize_entity_role(p.get("role")) == ROLE_TABLE),
        entity_pairs[0] if entity_pairs else {},
    )
    q = (question or "").strip()
    return {
        "entities": entity_pairs,
        "entity": str(first.get("entity") or "").strip(),
        "english": str(first.get("english") or "").strip(),
        "tables": table_zh or zh_list,
        "englishHints": en_list,
        "query": " ".join(table_zh or zh_list) if (table_zh or zh_list) else q,
        "source": source,
    }

# 明显闲聊，免调 LLM
_CHAT_SHORT = frozenset(
    {"你好", "您好", "在吗", "嗨", "hello", "hi", "谢谢", "感谢", "早上好", "下午好", "晚上好"}
)

_FALLBACK_CHAT = "你是企业智能问数助手。用中文简短回复，勿编造查询结果。"
_FALLBACK_BUILD = "你是 SQL 规划器。输出工作流 JSON；列名须来自 described_tables 或 describe_table。"


_PREFETCH_TABLE_LIMIT = 2


def select_prefetch_tables(
    catalog: dict[str, Any] | None,
    hitl_resolution: dict[str, Any] | None = None,
    *,
    limit: int = _PREFETCH_TABLE_LIMIT,
) -> list[str]:
    """召回顺序里取符合物理表名规则的前 limit 张。人工确认的表名插到最前。"""
    picked: list[str] = []
    seen: set[str] = set()

    def _add(raw: Any) -> None:
        name = physical_table_name(raw)
        if not name:
            return
        key = name.lower()
        bare = key.split(".")[-1]
        if key in seen or bare in seen:
            return
        seen.add(key)
        seen.add(bare)
        picked.append(name)

    hitl = hitl_resolution if isinstance(hitl_resolution, dict) else {}
    _add(hitl.get("confirmed_table") or hitl.get("table"))
    for it in (catalog or {}).get("items") or []:
        if len(picked) >= limit:
            break
        if not isinstance(it, dict):
            continue
        _add(it.get("name") or it.get("tableName") or it.get("table_name"))
    return picked[:limit]


def route_from_draft(draft: dict[str, Any] | None) -> Literal["QUERY"]:
    """查数草稿一律 QUERY（多节点 GOVERN 路径已下线；解析阶段已展平为单节点）。"""
    _ = draft
    return "QUERY"


def _slim_describe_for_prompt(
    *,
    table: str,
    schema: str | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    cols_out: list[dict[str, Any]] = []
    for c in result.get("columns") or []:
        if not isinstance(c, dict):
            continue
        cols_out.append(
            {
                "name": c.get("name") or c.get("columnName"),
                "dataType": c.get("dataType") or c.get("type"),
                "nullable": c.get("nullable"),
                "comment": c.get("comment"),
            }
        )
    kg = result.get("knowledge")
    kg_slim: Any = None
    if isinstance(kg, dict):
        units = []
        for u in (kg.get("units") or [])[:2]:
            if isinstance(u, dict):
                units.append({"title": u.get("title"), "summary": u.get("summary")})
        kg_slim = {"query": kg.get("query"), "units": units}
    return {
        "table": table,
        "schema": schema,
        "columns": cols_out,
        "knowledge": kg_slim,
    }


def _format_draft_sql_log(draft: dict[str, Any] | None, *, title: str = "生成 SQL") -> str | None:
    """业务工作日志：把草稿各节点 SQL 打成可读多行文本。"""
    if not draft:
        return None
    nodes = [n for n in (draft.get("nodes") or []) if isinstance(n, dict) and (n.get("sql") or "").strip()]
    if not nodes:
        return None
    parts = [f"{title}（{len(nodes)} 节点）「{draft.get('name') or '问数工作流'}」："]
    for n in nodes:
        nid = n.get("id") or "?"
        ntype = n.get("type") or "QUERY"
        ntitle = n.get("title") or nid
        sql = (n.get("sql") or "").strip()
        parts.append(f"-- [{nid}] {ntitle} ({ntype})\n{sql}")
    return "\n\n".join(parts)


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
    """LangGraph：intent_gate → (CHAT | gather_context → build) → verify → present。"""

    from dbc_askdata.agent_bundle import get_agent_bundle
    from dbc_askdata.llm.registry import resolve_model_name

    bundle = get_agent_bundle()
    light_model = resolve_model_name(settings, tier="light")
    gate_system = bundle.get_prompt("gate_system", fallback=_FALLBACK_GATE)
    chat_system = bundle.get_prompt("chat_system", fallback=_FALLBACK_CHAT)
    build_system = bundle.get_prompt("build_system", fallback=_FALLBACK_BUILD)

    ctx = {
        "trace_id": state.get("trace_id"),
        "turn_id": state.get("turn_id"),
        "workspace_id": state.get("workspace_id"),
        "project_id": state.get("project_id"),
        "session_id": state.get("session_id"),
        "user_id": state.get("user_id"),
    }
    sid = state.get("session_id")

    def _mark_hitl(s: GraphState, node: str) -> None:
        s["needs_hitl"] = True
        s["interrupted_node"] = node
        # 每次打断清空，避免上一轮 hitl_kind 污染；需要时由本节点重新写入
        s["hitl_kind"] = ""
        done = list(s.get("completed_nodes") or [])
        if node not in done:
            # completed = 已成功跑过的节点，打断点本身不算完成
            s["completed_nodes"] = done

    async def progress(msg: str) -> None:
        log.info("askdata.progress session_id=%s msg=%s", sid, msg)
        await append_work_log(sid, msg, turn_id=ctx.get("turn_id"))
        if on_progress:
            await on_progress(msg)

    async def intent_gate(s: GraphState) -> GraphState:
        """轻量门闩：CHAT/DATA +（DATA 时）实体抽取一次完成。HITL 续跑直接 DATA。"""
        await progress("正在判断意图并抽取实体…")
        timer = ScopeTimer()
        if s.get("hitl_resolution"):
            s["intent_gate"] = "DATA"
            await progress("意图门闩：DATA（HITL 续跑，跳过闲聊判定）")
            graph_ms = timer.exclusive_ms()
            log.info(
                "intent_gate session_id=%s gate=DATA reason=hitl_resolution latency_ms=%s",
                sid,
                graph_ms,
            )
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="intent_gate",
                status="OK",
                latency_ms=graph_ms,
                payload_meta={"gate": "DATA", "from_hitl": True},
                **ctx,
            )
            return s

        q = (s.get("question") or "").strip()
        if q in _CHAT_SHORT or q.lower() in _CHAT_SHORT:
            s["intent_gate"] = "CHAT"
            s["route"] = "CHAT"
            s["table_intent"] = _table_intent_from_pairs([], question=q, source="short_greeting")
            await progress(f"意图门闩：CHAT（短问候启发式）；question={q!r}")
            log.info(
                "intent_gate session_id=%s gate=CHAT reason=short_greeting question=%r",
                sid,
                q,
            )
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="intent_gate",
                status="OK",
                latency_ms=timer.exclusive_ms(),
                payload_meta={"gate": "CHAT", "reason": "short_greeting"},
                **ctx,
            )
            return s

        # 近窗用户问句（routes 已去掉本轮），供追问省略句判定 DATA
        recent_qs = user_questions_from_turns(s.get("recent_turns"), keep=KEEP_WINDOW)
        gate_user: dict[str, Any] = {
            "question": s.get("question"),
            "database": s.get("database"),
            "schema": s.get("schema"),
        }
        if recent_qs:
            gate_user["recent_user_questions"] = recent_qs
        user_payload = json.dumps(gate_user, ensure_ascii=False)
        gate_messages = [
            {"role": "system", "content": gate_system},
            {"role": "user", "content": user_payload},
        ]
        resp = await llm.chat_text(
            system=gate_system, user=user_payload, temperature=0, model=light_model
        )
        llm_ms = resp.get("latency_ms")
        timer.add_child_ms(llm_ms if isinstance(llm_ms, int) else None)
        gate_model = resp.get("model") or light_model
        content = (resp.get("message") or {}).get("content") or "{}"
        reason = ""
        entity_pairs: list[dict[str, str]] = []
        try:
            data = json.loads(content[content.find("{") : content.rfind("}") + 1])
            gate = str(data.get("gate") or "DATA").upper()
            reason = str(data.get("reason") or "")
            entity_pairs = parse_table_intent_pairs(content)
        except Exception:
            log.warning("intent_gate JSON 解析失败，降级 DATA content=%r", content[:200], exc_info=True)
            gate = "DATA"
            reason = "parse_fallback"
            entity_pairs = []
        if gate not in ("CHAT", "DATA"):
            gate = "DATA"
        if gate == "CHAT":
            entity_pairs = []
        s["intent_gate"] = gate  # type: ignore[assignment]
        if gate == "CHAT":
            s["route"] = "CHAT"
            s["table_intent"] = _table_intent_from_pairs([], question=q, source="gate_chat")
        else:
            s["table_intent"] = _table_intent_from_pairs(
                entity_pairs, question=q, source="gate_llm"
            )
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name="intent_gate",
            model=gate_model,
            status="OK",
            latency_ms=llm_ms if isinstance(llm_ms, int) else None,
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            payload_meta={
                "role": "intent_gate",
                "model_tier": "light",
                "merged_entity_extract": True,
                "entity_count": len(entity_pairs),
                "entities": entity_pairs[:12],
                **build_llm_rounds_meta(
                    messages=gate_messages,
                    response=resp.get("message"),
                    role="intent_gate",
                ),
            },
            **ctx,
        )
        entity_hint = ""
        if entity_pairs:
            entity_hint = "；实体：" + "、".join(
                f"{p.get('entity') or '?'}/{(p.get('english') or '-').strip() or '-'}"
                f"[{normalize_entity_role(p.get('role'))}]"
                for p in entity_pairs[:6]
            )
        await progress(
            f"意图门闩：{gate}"
            + (f"；{reason}" if reason else "")
            + entity_hint
        )
        log.info(
            "intent_gate session_id=%s gate=%s reason=%s entities=%s question=%r",
            sid,
            gate,
            reason,
            len(entity_pairs),
            q[:120],
        )
        await spans.record(
            session,
            phase="generate",
            kind="GRAPH",
            name="intent_gate",
            status="OK",
            latency_ms=timer.exclusive_ms(),
            payload_meta={
                "gate": gate,
                "reason": reason,
                "entity_count": len(entity_pairs),
                "merged_entity_extract": True,
            },
            **ctx,
        )
        return s

    async def gather_context(s: GraphState) -> GraphState:
        """查数路径：复用门闩已抽实体（缺省才补抽）→ 找表 + 库通用知识。"""
        graph_timer = ScopeTimer()
        q = str(s.get("question") or "")
        existing = s.get("table_intent") if isinstance(s.get("table_intent"), dict) else {}
        source = str(existing.get("source") or "")
        reuse_gate = source in ("gate_llm", "gate_chat", "short_greeting")

        if reuse_gate:
            entity_pairs = (
                existing.get("entities") if isinstance(existing.get("entities"), list) else []
            )
            entity_pairs = [p for p in entity_pairs if isinstance(p, dict)]
            await progress(
                f"复用门闩实体（{len(entity_pairs)} 对），跳过二次抽取…"
                if entity_pairs
                else "门闩未抽出实体，将用原句找表…"
            )
            log.info(
                "table_intent reused from gate session_id=%s count=%s source=%s",
                sid,
                len(entity_pairs),
                source,
            )
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="table_intent",
                status="OK",
                latency_ms=0,
                payload_meta={
                    "role": "table_intent",
                    "skipped_llm": True,
                    "source": source,
                    "entities": entity_pairs[:12],
                    "count": len(entity_pairs),
                },
                **ctx,
            )
        else:
            await progress("正在抽取业务实体（中文/英文对）…")
            intent = await resolve_table_intent_query(llm, question=q, model=light_model)
            intent_ms = intent.get("latency_ms")
            graph_timer.add_child_ms(intent_ms if isinstance(intent_ms, int) else None)
            entity_pairs = intent.get("entities") if isinstance(intent.get("entities"), list) else []
            entity_pairs = [p for p in entity_pairs if isinstance(p, dict)]
            s["table_intent"] = _table_intent_from_pairs(
                entity_pairs,
                question=q,
                source=str(intent.get("source") or "llm"),
            )
            if entity_pairs:
                pair_txt = "、".join(
                    f"{p.get('entity') or '?'}/{(p.get('english') or '-').strip() or '-'}"
                    for p in entity_pairs[:8]
                )
                await progress(f"表意图（{len(entity_pairs)} 对）：{pair_txt}")
                log.info(
                    "table_intent session_id=%s count=%s pairs=%s",
                    sid,
                    len(entity_pairs),
                    pair_txt,
                )
            else:
                await progress("表意图：（无实体）")
                log.info("table_intent session_id=%s count=0", sid)
            intent_rounds = (
                build_llm_rounds_meta(
                    messages=intent.get("prompt_messages")
                    if isinstance(intent.get("prompt_messages"), list)
                    else None,
                    response=intent.get("response_message")
                    if isinstance(intent.get("response_message"), dict)
                    else None,
                    role="table_intent",
                )
                if intent.get("source") == "llm"
                else {}
            )
            await spans.record(
                session,
                phase="generate",
                kind="LLM",
                name="table_intent",
                model=intent.get("model") or light_model,
                status="OK",
                latency_ms=intent_ms if isinstance(intent_ms, int) else None,
                token_in=intent.get("token_in") if isinstance(intent.get("token_in"), int) else None,
                token_out=intent.get("token_out")
                if isinstance(intent.get("token_out"), int)
                else None,
                payload_meta={
                    "role": "table_intent",
                    "model_tier": "light",
                    "entities": entity_pairs[:12],
                    "count": len(entity_pairs),
                    "source": intent.get("source"),
                    **intent_rounds,
                },
                **ctx,
            )

        import asyncio

        await progress("正在并行检索候选表、库通用知识与 SQL 示例…")

        async def _catalog_job() -> tuple[dict[str, Any], int]:
            t0 = time.monotonic()
            result = await search_ask_catalog(
                settings,
                connection_id=s["connection_id"],
                database=s.get("database"),
                schema=s.get("schema"),
                question=str(s.get("question") or ""),
                entity_pairs=entity_pairs,
                top_k=5,
            )
            return result, int((time.monotonic() - t0) * 1000)

        async def _kg_job() -> tuple[dict[str, Any] | None, int]:
            t0 = time.monotonic()
            result = await search_db_general_knowledge(
                settings,
                connection_id=s.get("connection_id"),
                database=s.get("database"),
                schema=s.get("schema"),
            )
            return result, int((time.monotonic() - t0) * 1000)

        async def _sql_ex_job() -> tuple[list[dict[str, Any]], int]:
            t0 = time.monotonic()
            result = await load_sql_ex_knowledge(settings)
            return result, int((time.monotonic() - t0) * 1000)

        catalog_res, kg_res, sql_ex_res = await asyncio.gather(
            _catalog_job(), _kg_job(), _sql_ex_job(), return_exceptions=True
        )

        if isinstance(catalog_res, BaseException):
            log.error("gather_context 问数多路找表失败（含重试）", exc_info=catalog_res)
            s["catalog"] = {"items": [], "tableRelations": []}
            s["table_relations"] = []
            s.pop("catalog_directory_knowledge", None)
            _mark_hitl(s, "gather_context")
            s["hitl_question"] = (
                "知识库检索失败，请直接补充要查询的物理表名或指标口径后继续。"
            )
            s["reply"] = s["hitl_question"]
            await progress(f"候选表检索失败，转 HITL：{catalog_res}")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_ask_catalog",
                status="ERROR",
                error_message=str(catalog_res),
                **ctx,
            )
        else:
            catalog, catalog_ms = catalog_res
            items = catalog.get("items") or []
            slim_items = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "").strip()
                if not name:
                    continue
                slim_items.append(
                    {
                        "name": name,
                        "title": str(it.get("title") or name).strip(),
                        "description": str(it.get("description") or "").strip(),
                        "bodySummary": str(it.get("bodySummary") or "").strip(),
                        "score": it.get("score"),
                        "source": str(it.get("source") or "").strip(),
                    }
                )
            rels = [
                r
                for r in (catalog.get("tableRelations") or [])
                if isinstance(r, dict)
            ]
            s["catalog"] = {
                "items": slim_items,
                "question": catalog.get("question"),
                "entities": catalog.get("entities") or [],
                "entity": catalog.get("entity") or "",
                "english": catalog.get("english") or "",
                "entitiesZh": catalog.get("entitiesZh") or [],
                "entitiesEn": catalog.get("entitiesEn") or [],
                "documentIds": catalog.get("documentIds") or {},
                "paths": catalog.get("paths") or {},
                "tableRelations": rels,
                "graphId": catalog.get("graphId"),
            }
            s["table_relations"] = rels
            s.pop("catalog_directory_knowledge", None)
            n = len(slim_items)
            names = [it["name"] for it in slim_items if it.get("name")]
            score_bits = [
                f"{it['name']}={it.get('score')}"
                for it in slim_items
                if it.get("name")
            ]
            if names:
                await progress(
                    f"候选表召回完成，共 {n} 张"
                    + (f"（关系 {len(rels)} 条）" if rels else "")
                    + f"：{'、'.join(score_bits)}"
                )
            else:
                await progress("候选表召回完成，共 0 张")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_ask_catalog",
                status="OK",
                latency_ms=catalog_ms,
                payload_meta={
                    "hit_count": n,
                    "table_names": names,
                    "table_scores": [
                        {
                            "name": it.get("name"),
                            "score": it.get("score"),
                            "source": it.get("source"),
                        }
                        for it in slim_items
                        if it.get("name")
                    ],
                    "relation_count": len(rels),
                    "paths": catalog.get("paths") or {},
                    "entity_pairs": entity_pairs[:12],
                    "parallel": True,
                    "cache": catalog.get("__cache__"),
                },
                **ctx,
            )

        if isinstance(kg_res, BaseException):
            log.warning("gather_context 库通用知识检索失败", exc_info=kg_res)
            s.pop("db_general_knowledge", None)
            await progress(f"库通用知识检索失败（将继续）：{kg_res}")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="search_db_general_knowledge",
                status="ERROR",
                error_message=str(kg_res),
                **ctx,
            )
        else:
            kg_raw, kg_ms = kg_res
            kg, cache_status = unwrap_general_knowledge_result(
                kg_raw if isinstance(kg_raw, dict) else None
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
                latency_ms=kg_ms,
                payload_meta={
                    "hit": bool(kg),
                    "query": (kg or (kg_raw if isinstance(kg_raw, dict) else {}) or {}).get(
                        "query"
                    ),
                    "refId": (kg or {}).get("refId"),
                    "parallel": True,
                    "cache": cache_status,
                },
                **ctx,
            )

        if isinstance(sql_ex_res, BaseException):
            log.warning("gather_context SQL_EX 知识加载失败", exc_info=sql_ex_res)
            s.pop("sql_ex_knowledge", None)
            await progress(f"SQL 示例知识加载失败（将继续）：{sql_ex_res}")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="load_sql_ex_knowledge",
                status="ERROR",
                error_message=str(sql_ex_res),
                **ctx,
            )
        else:
            sql_ex_items, sql_ex_ms = sql_ex_res
            if sql_ex_items:
                s["sql_ex_knowledge"] = sql_ex_items
                titles = "、".join(
                    str(it.get("title") or "").strip() or "?" for it in sql_ex_items[:5]
                )
                await progress(f"SQL 示例已加载 {len(sql_ex_items)} 篇：{titles}")
            else:
                s.pop("sql_ex_knowledge", None)
                await progress("未配置 SQL_EX 示例知识（可在知识库维护）")
            await spans.record(
                session,
                phase="generate",
                kind="TOOL",
                name="load_sql_ex_knowledge",
                status="OK",
                latency_ms=sql_ex_ms,
                payload_meta={
                    "hit_count": len(sql_ex_items or []),
                    "titles": [it.get("title") for it in (sql_ex_items or [])[:10]],
                    "parallel": True,
                },
                **ctx,
            )

        parallel_ms: list[int | None] = []
        if not isinstance(catalog_res, BaseException):
            parallel_ms.append(catalog_res[1])
        if not isinstance(kg_res, BaseException):
            parallel_ms.append(kg_res[1])
        if not isinstance(sql_ex_res, BaseException):
            parallel_ms.append(sql_ex_res[1])
        graph_timer.add_parallel_ms(*parallel_ms)

        if not s.get("needs_hitl"):
            items = (s.get("catalog") or {}).get("items") or []
            picked: list[str] = []
            seen: set[str] = set()
            hitl = s.get("hitl_resolution") if isinstance(s.get("hitl_resolution"), dict) else {}
            for raw in (
                hitl.get("confirmed_table"),
                hitl.get("table"),
                *[
                    it.get("name")
                    for it in items
                    if isinstance(it, dict)
                ],
            ):
                name = physical_table_name(raw)
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                picked.append(name)
            s["recommended_tables"] = picked
            s["pre_described_tables"] = []
            if not picked:
                _mark_hitl(s, "gather_context")
                s["hitl_kind"] = "TABLE"
                s["hitl_question"] = (
                    "未找到符合命名规则的物理表，请补充要查询的表名（如 hr_employee）。"
                )
                s["reply"] = s["hitl_question"]
                await progress("表名检查未通过，需要您补充物理表名")
            else:
                await progress(
                    f"表语义匹配完成，共 {len(picked)} 张候选表（不预加载结构，生成时按需 describe）"
                )

        done = list(s.get("completed_nodes") or [])
        if "gather_context" not in done and not s.get("needs_hitl"):
            done.append("gather_context")
            s["completed_nodes"] = done
        await spans.record(
            session,
            phase="generate",
            kind="GRAPH",
            name="gather_context",
            status="OK",
            latency_ms=graph_timer.exclusive_ms(),
            **ctx,
        )
        return s

    def _session_prefix(s: GraphState) -> list[dict[str, Any]]:
        # 近窗已确认样本带入 QUERY 生成
        return build_session_prefix_messages(
            route=s.get("route") or "QUERY",
            recent_turns=s.get("recent_turns"),
            verified_samples=s.get("verified_samples"),
        )

    async def chat_reply(s: GraphState) -> GraphState:
        await progress("普通沟通：正在生成回复…")
        s["needs_hitl"] = False
        prefix = build_session_prefix_messages(
            route="CHAT",
            recent_turns=s.get("recent_turns"),
            verified_samples=None,
        )
        time_ctx = current_time_context()
        messages = [
            {
                "role": "system",
                "content": chat_system + "\n" + current_time_system_suffix(),
            },
            *prefix,
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": s.get("question"),
                        "current_time": time_ctx,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        resp = await llm.chat(
            messages=messages,
            tools=None,
            tool_choice=None,
            temperature=0.4,
            model=light_model,
        )
        chat_model = resp.get("model") or light_model
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name="chat_reply",
            model=chat_model,
            status="OK",
            latency_ms=resp.get("latency_ms"),
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            payload_meta=build_llm_rounds_meta(
                messages=messages,
                response=resp.get("message"),
                role="chat_reply",
            ),
            **ctx,
        )
        s["reply"] = ((resp.get("message") or {}).get("content") or "").strip() or (
            "您好！我是智能问数助手。直接描述要查的数据即可，例如「各部门在职员工人数」。"
        )
        await progress("闲聊回复完成")
        await spans.record(session, phase="generate", kind="GRAPH", name="chat_reply", status="OK", **ctx)
        return s

    async def hitl_node(s: GraphState) -> GraphState:
        if not s.get("interrupted_node"):
            _mark_hitl(s, "hitl")
        else:
            s["needs_hitl"] = True
        s["reply"] = s.get("hitl_question") or "需要您确认后继续。"
        await progress("等待您确认关键信息（表名/口径）…")
        await spans.record(session, phase="generate", kind="HITL", name="await_user", status="OK", **ctx)
        return s


    async def build_workflow_draft(s: GraphState) -> GraphState:
        if s.get("draft"):
            s["route"] = route_from_draft(s.get("draft"))
            return s
        regen = bool(s.get("verify_critique"))
        items = [
            it
            for it in ((s.get("catalog") or {}).get("items") or [])
            if isinstance(it, dict)
        ]
        await progress(
            "校验失败，带错误重新生成 SQL 草稿…"
            if regen
            else (
                f"正在生成 SQL 草稿（候选表 {len(items)} 张，含字段摘要与关系）…"
                if items
                else "正在生成 SQL 工作流草稿…"
            )
        )
        profiles = dict(s.get("column_profiles") or {})
        described_cols = dict(s.get("described_columns") or {})
        catalog_tables = [
            {
                "name": it.get("name"),
                "description": it.get("description") or "",
                "bodySummary": it.get("bodySummary") or "",
                "source": it.get("source") or "",
            }
            for it in items[:12]
        ]
        table_relations = [
            r
            for r in (s.get("table_relations") or (s.get("catalog") or {}).get("tableRelations") or [])
            if isinstance(r, dict)
        ][:40]
        user_payload: dict[str, Any] = {
            "question": s.get("question"),
            "catalog_tables": catalog_tables,
            "table_relations": table_relations,
            "workspace_id": s["workspace_id"],
            "connection_id": s["connection_id"],
            "database": s.get("database"),
            "schema": s.get("schema"),
            "hint": (
                "catalog_tables 已含表名/说明/字段压缩（bodySummary）；table_relations 含 JOIN 提示。"
                "选表可参考 bodySummary。"
                "WHERE 中每个 =/!=/IN/NOT IN 字面量条件：先对该表 describe_table（未描述过时），"
                "再对该列 get_column_profile(condition_value=用户原词或字面量)，按 action 写条件；"
                "禁止看完 describe 直接写中文/臆造码；禁止占位符。"
                "时间范围用 current_time 写成真实日期；金额等数值区间比较不调 profile。"
                "缺某张表的外键邻居再 list_table_relations；两表都已知只缺 JOIN 列再 query_table_relations。"
                "看完工具结果后只输出单节点 QUERY（优先 JOIN/子查询，尽量不要 WITH AS）；禁止多节点与 GOVERN。"
                "若有 hitl_confirmation：kind=COLUMN 时按其 column/text 写列名；"
                "码值按其 text 写过滤字面量；confirmed_table 仅在其为物理表名时采用。"
            ),
        }
        if s.get("recommended_tables"):
            user_payload["recommended_tables"] = list(s.get("recommended_tables") or [])[:12]
        if s.get("eval_mode"):
            user_payload["eval_alias_rules"] = (
                "测评模式：最外层 SELECT 中凡 COUNT(...) 投影必须使用别名 cnt（写作 AS cnt）；"
                "禁止 total/count/人数 等其它别名；ORDER BY 计数列时也用 cnt。"
            )
        if s.get("review_critique"):
            user_payload["review_critique"] = s.get("review_critique")
        if s.get("verify_critique"):
            user_payload["verify_critique"] = s.get("verify_critique")
        hitl_prompt = hitl_for_sql_prompt(s.get("hitl_resolution"))
        if hitl_prompt:
            user_payload["hitl_confirmation"] = hitl_prompt
            if hitl_prompt.get("confirmed_table"):
                user_payload["confirmed_table"] = hitl_prompt["confirmed_table"]
        kg_prompt = format_db_general_knowledge_for_prompt(s.get("db_general_knowledge"))
        if kg_prompt:
            user_payload["db_general_knowledge"] = kg_prompt
        sql_ex_prompt = format_sql_ex_knowledge_for_prompt(s.get("sql_ex_knowledge"))
        if sql_ex_prompt:
            user_payload["sql_ex_knowledge"] = sql_ex_prompt
        user_payload["current_time"] = current_time_context()
        messages = [
            {
                "role": "system",
                "content": build_system + "\n" + current_time_system_suffix(),
            },
            *_session_prefix(s),
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
            require_describe_tables=False,
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
        s["route"] = route_from_draft(draft)
        s["error"] = ""
        s["verify_action"] = ""
        await progress(
            f"草稿生成完成：{draft.get('name')}（{s['route']}，{len(draft.get('nodes') or [])} 节点）"
        )
        sql_log = _format_draft_sql_log(draft, title="草稿 SQL")
        if sql_log:
            await progress(sql_log)
        await spans.record(session, phase="generate", kind="GRAPH", name="build_workflow_draft", status="OK", **ctx)
        return s

    async def verify_nodes(s: GraphState) -> GraphState:
        draft = s.get("draft")
        if not draft:
            return s
        s["verify_action"] = ""
        await progress("正在校验 SQL（投影、画像、EXPLAIN）…")
        nodes = list(draft.get("nodes") or [])
        fixed = []
        profiles = dict(s.get("column_profiles") or {})
        # 兼容旧多节点草稿：展开后的 SQL，供下游 EXPLAIN 内联子查询
        expanded_upstream: dict[str, str] = {}

        async def fetch_profile(
            table: str,
            column: str,
            condition_value: str | None = None,
        ) -> dict[str, Any] | None:
            hint = f"校验条件探测：{table}.{column}"
            if condition_value:
                hint += f" = {condition_value!r}"
            await progress(hint)
            args: dict[str, Any] = {
                "workspace_id": s["workspace_id"],
                "connection_id": s["connection_id"],
                "table": table,
                "column": column,
            }
            if condition_value:
                args["condition_value"] = condition_value
            if s.get("database"):
                args["database"] = s["database"]
            if s.get("schema"):
                args["schema"] = s["schema"]
            return await tool_gateway.invoke("get_column_profile", args)

        for idx, n in enumerate(nodes, start=1):
            sql = n.get("sql") or ""
            node_id = str(n.get("id") or f"n{idx}")
            explain_sql = expand_node_refs_for_explain(sql, expanded_upstream)
            await progress(f"校验节点 {idx}/{len(nodes)}：{n.get('title') or n.get('id')}")
            result = await verify_sql(
                sqlwork=sqlwork,
                sql=sql,
                workspace_id=s["workspace_id"],
                connection_id=s["connection_id"],
                database=s.get("database"),
                schema=s.get("schema"),
                use_explain=True,
                column_profiles=profiles,
                fetch_profile=fetch_profile,
                explain_sql=explain_sql if explain_sql != sql else None,
            )
            if result.auto_added_eq_cols:
                await progress(
                    "已自动将 WHERE 等值列补入 SELECT："
                    + "、".join(result.auto_added_eq_cols)
                )
            if result.auto_added_group_cols:
                await progress(
                    "已自动将 GROUP BY 列补入 SELECT："
                    + "、".join(result.auto_added_group_cols)
                )
            if getattr(result, "auto_use_key_rewrites", None):
                await progress(
                    "已自动将字典条件改为 key："
                    + "、".join(result.auto_use_key_rewrites)
                )
            if not result.ok:
                if result.needs_hitl:
                    _mark_hitl(s, "verify")
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

                node_title = str(n.get("title") or node_id)
                critique = (
                    f"节点 {node_id}（{node_title}）机械校验失败。\n"
                    f"失败 SQL：\n{sql}\n\n"
                    f"错误：{result.message}\n"
                    "请对照 catalog 重新 describe_table（错表/错列须换表重探）；"
                    "WHERE 的 =/!=/IN/NOT IN 须再调 get_column_profile(condition_value=字面量)，"
                    "按 use_literal/use_key/follow_fk/retry_same_table 改写条件，"
                    "禁止原样重出上述失败 SQL。"
                    "若有 sql_ex_knowledge，须对照其中正确示例改写语法，禁止关键字粘连。"
                    "只输出单节点 QUERY（优先 JOIN/子查询，尽量不要 WITH AS），禁止多节点 GOVERN。"
                )
                rounds = int(s.get("verify_rounds") or 0)
                max_regen = int(settings.verify_max_regen_rounds)
                if rounds >= max_regen:
                    # 技术细节仅进日志/span；对用户给可理解的失败提示
                    s["error"] = (
                        f"节点 {node_id} 校验失败（已重写 {rounds} 次仍失败）: {result.message}"
                    )
                    s["reply"] = (
                        "抱歉，当前问题未能生成可用的查询 SQL。"
                        "可能是查询条件、字段或表关系较复杂，多次自动修正后仍未通过校验。"
                        "请尝试换一种问法、缩小查询范围，或补充更明确的表名与口径后再试。"
                    )
                    s["draft"] = None  # type: ignore[typeddict-item]
                    s["verify_action"] = ""
                    s["column_profiles"] = profiles
                    await progress("未能生成可用 SQL，请换种问法或补充更明确的条件后再试")
                    log.warning(
                        "verify 重写耗尽 session_id=%s node=%s msg=%s",
                        sid,
                        node_id,
                        result.message,
                    )
                    await spans.record(
                        session,
                        phase="generate",
                        kind="GRAPH",
                        name="verify",
                        status="ERROR",
                        error_message=result.message,
                        payload_meta={"action": "fail", "rounds": rounds},
                        **ctx,
                    )
                    return s

                s["verify_rounds"] = rounds + 1
                s["verify_critique"] = critique
                s["verify_action"] = "regen"
                s["error"] = ""
                s["draft"] = None  # type: ignore[typeddict-item]
                s["column_profiles"] = profiles
                await progress(
                    f"查询草稿未通过校验，正在自动修正（第 {s['verify_rounds']}/{max_regen} 次）…"
                )
                log.info(
                    "verify regen session_id=%s node=%s round=%s/%s msg=%s",
                    sid,
                    node_id,
                    s["verify_rounds"],
                    max_regen,
                    result.message[:200],
                )
                await spans.record(
                    session,
                    phase="generate",
                    kind="GRAPH",
                    name="verify",
                    status="OK",
                    error_message=result.message,
                    payload_meta={"action": "regen", "rounds": s["verify_rounds"]},
                    **ctx,
                )
                return s
            n = dict(n)
            kept = result.dialect_sql or sql
            n["type"] = "QUERY"
            n["readonly"] = True
            n["sql"] = kept
            fixed.append(n)
            # 兼容旧多节点：占位已内联为子查询
            expanded_upstream[node_id] = expand_node_refs_for_explain(kept, expanded_upstream)

        draft = dict(draft)
        draft["nodes"] = fixed
        s["draft"] = draft
        s["route"] = "QUERY"
        s["column_profiles"] = profiles
        s["verify_critique"] = ""
        s["verify_action"] = ""
        await progress("SQL 校验通过")
        sql_log = _format_draft_sql_log(draft, title="校验后 SQL")
        if sql_log:
            await progress(sql_log)
        await spans.record(session, phase="generate", kind="GRAPH", name="verify", status="OK", **ctx)
        return s

    async def review_sql(s: GraphState) -> GraphState:
        # GOVERN 语义评审已下线；旧 checkpoint 落到 review 时直接放行
        s["review_action"] = "pass"
        log.info("review_sql skipped (QUERY-only) session_id=%s", sid)
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
            sql_log = _format_draft_sql_log(draft, title="最终 SQL")
            if sql_log:
                await progress(sql_log)
            await spans.record(
                session, phase="generate", kind="GRAPH", name="present_eval_auto_save", status="OK", **ctx
            )
            return s
        s["reply"] = (
            f"已生成工作流草稿「{draft.get('name')}」，共 {len(draft.get('nodes') or [])} 个节点。"
            f"请确认保存后执行。\n\n```sql\n{sql_preview}\n```"
        )
        await progress("草稿已就绪，可保存并执行")
        sql_log = _format_draft_sql_log(draft, title="最终 SQL")
        if sql_log:
            await progress(sql_log)
        await spans.record(
            session, phase="generate", kind="GRAPH", name="present_save_and_execute_actions", status="OK", **ctx
        )
        return s

    def after_gate(s: GraphState) -> str:
        gate = s.get("intent_gate") or "DATA"
        if gate == "CHAT":
            log.info("after_gate session_id=%s next=chat", sid)
            return "chat"
        log.info("after_gate session_id=%s next=gather_context", sid)
        return "gather"

    def after_gather(s: GraphState) -> str:
        if s.get("needs_hitl"):
            return "hitl"
        return "build"

    def after_bootstrap(s: GraphState) -> str:
        """断点续跑入口：按 resume_from 跳过已完成节点。"""
        resume = str(s.get("resume_from") or "").strip().lower()
        if resume in ("build", "build_workflow_draft", "govern", "govern_plan"):
            return "build"
        if resume == "verify":
            return "verify"
        if resume == "review":
            return "review"
        if resume in ("fine_router", "gather", "gather_context"):
            return "gather"
        if resume == "hitl":
            return "hitl"
        return "intent_gate"

    def after_verify(s: GraphState) -> str:
        if s.get("needs_hitl"):
            return "present"
        if s.get("verify_action") == "regen":
            log.info(
                "after_verify session_id=%s next=build reason=verify_regen rounds=%s route=%s",
                sid,
                s.get("verify_rounds"),
                s.get("route"),
            )
            return "build"
        if s.get("error") or not s.get("draft"):
            return "present"
        # QUERY-only：机械校验通过即可，不再走语义 review
        log.info("after_verify session_id=%s next=present", sid)
        return "present"

    def after_review(s: GraphState) -> str:
        if s.get("needs_hitl"):
            return "hitl"
        if s.get("review_action") == "regen":
            return "build"
        return "present"

    async def bootstrap(s: GraphState) -> GraphState:
        return s

    g = StateGraph(GraphState)
    g.add_node("bootstrap", bootstrap)
    g.add_node("intent_gate", intent_gate)
    g.add_node("gather_context", gather_context)
    g.add_node("chat_reply", chat_reply)
    g.add_node("hitl", hitl_node)
    g.add_node("build_workflow_draft", build_workflow_draft)
    g.add_node("verify", verify_nodes)
    g.add_node("review", review_sql)
    g.add_node("present", present)
    g.set_entry_point("bootstrap")
    g.add_conditional_edges(
        "bootstrap",
        after_bootstrap,
        {
            "intent_gate": "intent_gate",
            "gather": "gather_context",
            "build": "build_workflow_draft",
            "verify": "verify",
            "review": "review",
            "hitl": "hitl",
        },
    )
    g.add_conditional_edges(
        "intent_gate",
        after_gate,
        {"chat": "chat_reply", "gather": "gather_context"},
    )
    g.add_conditional_edges(
        "gather_context",
        after_gather,
        {"build": "build_workflow_draft", "hitl": "hitl"},
    )
    g.add_edge("chat_reply", "present")
    g.add_edge("build_workflow_draft", "verify")
    g.add_edge("hitl", "present")
    g.add_conditional_edges(
        "verify",
        after_verify,
        {
            "review": "review",
            "present": "present",
            "build": "build_workflow_draft",
        },
    )
    g.add_conditional_edges(
        "review",
        after_review,
        {"hitl": "hitl", "build": "build_workflow_draft", "present": "present"},
    )
    g.add_edge("present", END)
    app = g.compile()
    await progress("开始处理您的请求…")
    return await app.ainvoke(state)

