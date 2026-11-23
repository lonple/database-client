from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.context.compress import (
    estimate_messages_chars,
    fold_working_messages,
    slim_tool_result,
)
from dbc_askdata.graph.sql_tables import (
    described_key_from_args,
    source_tables_from_draft,
)
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.llm_exchange import build_llm_rounds_meta
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.verify.semantic import store_profile
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.tools.schema_slim import build_scope_args

log = logging.getLogger(__name__)

ProgressFn = Callable[[str], Awaitable[None]]


def _split_table_key(key: str) -> tuple[str | None, str]:
    if "." in key:
        schema, name = key.rsplit(".", 1)
        return schema, name
    return None, key


async def run_tool_agent(
    *,
    settings: Settings,
    llm: LlmClient,
    gateway: ToolGateway,
    spans: SpanRecorder,
    session: AsyncSession,
    messages: list[dict[str, Any]],
    workspace_id: int,
    connection_id: int,
    database: str | None,
    schema: str | None,
    ctx: dict[str, Any],
    parent_span_name: str,
    max_steps: int | None = None,
    on_progress: ProgressFn | None = None,
    on_final_content: Callable[[str], Any] | None = None,
    exclude_tools: set[str] | None = None,
    require_describe_tables: bool = True,
    column_profiles: dict[str, Any] | None = None,
    described_columns: dict[str, list[str]] | None = None,
) -> Any:
    """多轮 tool_call；默认要求 SQL 涉表均已 describe_table，否则拒收并补探测。"""
    blocked = exclude_tools or set()
    tools = gateway.openai_tools(exclude=blocked)
    scope_args = build_scope_args(
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
    )
    steps = max_steps if max_steps is not None else settings.llm_max_tool_rounds
    profiles = column_profiles if column_profiles is not None else {}
    described_cols = described_columns if described_columns is not None else {}
    parent_span = await spans.record(
        session,
        phase="generate",
        kind="GRAPH",
        name=parent_span_name,
        status="OK",
        **ctx,
    )
    working = list(messages)
    # 细路由预 describe / 历史 described_columns：视为已探测，避免强制再调工具
    described: set[str] = {str(k).strip().lower() for k in described_cols.keys() if str(k).strip()}
    # 同时登记 bare 表名，兼容 SQL 只写表名的校验
    for k in list(described):
        if "." in k:
            described.add(k.rsplit(".", 1)[-1])
    describe_nudge_used = False
    json_nudge_used = False
    collected_rounds: list[dict[str, Any]] = []

    async def _flush_parent_rounds() -> None:
        if parent_span is None:
            return
        await spans.merge_payload_meta(
            parent_span,
            {"llmRounds": collected_rounds, "llmRoundCount": len(collected_rounds)},
        )

    async def _invoke_tool(name: str, args: dict[str, Any], tool_call_id: str) -> None:
        nonlocal described
        status = "OK"
        err = None
        cache_status = None
        t_tool = time.monotonic()
        try:
            if name in blocked:
                raise ValueError(f"本阶段禁止调用 Tool: {name}（目录已在上下文中）")
            # 上下文已预加载该表结构时，跳过真实 describe，避免重复探测与 Token
            skip_describe = False
            skip_payload: dict[str, Any] | None = None
            if name == "describe_table":
                key = described_key_from_args(args, default_schema=schema)
                bare = str(args.get("table") or "").strip().lower()
                if "." in bare:
                    bare = bare.rsplit(".", 1)[-1]
                already = bool(
                    key
                    and (
                        key in described
                        or bare in described
                        or any(
                            d == key or d == bare or d.endswith(f".{bare}")
                            for d in described
                        )
                    )
                )
                if already and key:
                    names = list(described_cols.get(key) or [])
                    if not names and bare:
                        for dk, dv in described_cols.items():
                            if dk == bare or dk.endswith(f".{bare}"):
                                names = list(dv or [])
                                break
                    skip_describe = True
                    cache_status = "prefetched_skip"
                    skip_payload = {
                        "skipped": True,
                        "reason": "already_in_context",
                        "table": args.get("table"),
                        "schema": args.get("schema") or schema,
                        "columns": [{"name": n} for n in names],
                        "hint": (
                            "表结构已在上下文，请直接使用下列列名，勿再 describe。"
                            "若某列画像失败（列不存在），请换真实列名，禁止反复 describe 同一张表。"
                        ),
                    }
                    described.add(key)
                    if bare:
                        described.add(bare)
            if on_progress:
                hint = name
                if name == "get_column_profile":
                    hint = f"枚举/列画像探测：{args.get('table')}.{args.get('column')}"
                elif name == "describe_table":
                    if skip_describe:
                        hint = f"跳过重复探测（已描述）：{args.get('table')}"
                    else:
                        hint = f"探测表结构：{args.get('table')}"
                elif name == "search_catalog":
                    hint = f"检索目录：{args.get('keyword') or ''}"
                elif name == "list_table_relations":
                    hint = f"查表外键邻居：{args.get('table') or ''}"
                elif name == "query_table_relations":
                    ft = args.get("fromTable") or args.get("from_table") or ""
                    tt = args.get("toTable") or args.get("to_table") or ""
                    hint = f"查表关联：{ft} ↔ {tt}"
                await on_progress(hint)
            if skip_describe and skip_payload is not None:
                result = skip_payload
            else:
                result = await gateway.invoke(name, args, scope=scope_args)
            if isinstance(result, dict) and "__cache__" in result:
                cache_status = result.pop("__cache__", None)
            if name == "describe_table" and not skip_describe:
                key = described_key_from_args(args, default_schema=schema)
                if key:
                    described.add(key)
                    bare = str(args.get("table") or "").strip().lower()
                    if bare:
                        described.add(bare)
                if isinstance(result, dict):
                    names: list[str] = []
                    for c in result.get("columns") or []:
                        if not isinstance(c, dict):
                            continue
                        cname = str(c.get("name") or c.get("columnName") or "").strip()
                        if cname:
                            names.append(cname)
                    if key and names:
                        described_cols[key] = names
            if name == "get_column_profile" and isinstance(result, dict):
                store_profile(
                    profiles,
                    table=str(args.get("table") or result.get("table") or ""),
                    column=str(args.get("column") or result.get("column") or ""),
                    schema=args.get("schema_name") or args.get("schema") or schema,
                    profile=result,
                )
            payload = slim_tool_result(
                name,
                result,
                max_chars=settings.context_tool_result_max_chars,
            )
        except Exception as ex:
            log.warning("tool_agent 调用失败 name=%s", name, exc_info=True)
            status = "ERROR"
            err = str(ex)
            hint = ""
            if name == "get_column_profile":
                hint = (
                    "列画像失败时：若该表已 describe，勿再 describe；"
                    "请改用 describe 返回的真实列名；table 只传物理表名（不要 schema.table）。"
                )
            payload = json.dumps(
                {"error": err, **({"hint": hint} if hint else {})},
                ensure_ascii=False,
            )

        await spans.record(
            session,
            phase="generate",
            kind="TOOL",
            name=name,
            status=status,
            latency_ms=int((time.monotonic() - t_tool) * 1000),
            error_message=err,
            parent_span_id=parent_span,
            payload_meta={
                "args_keys": sorted(args.keys()),
                "result_chars": len(payload),
                "cache": cache_status,
            },
            **ctx,
        )
        working.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": payload,
            }
        )

    async def _auto_describe(missing: set[str]) -> None:
        """服务端补调 describe_table，把结构注入对话后再让模型重出 SQL。"""
        if on_progress:
            await on_progress(f"强制探测表结构：{', '.join(sorted(missing))}")
        tool_calls_payload: list[dict[str, Any]] = []
        for i, key in enumerate(sorted(missing)):
            sch, name = _split_table_key(key)
            # 对话里只暴露业务字段；作用域由 invoke(scope=) 注入
            args: dict[str, Any] = {"table": name}
            if sch:
                args["schema"] = sch
            tc_id = f"auto_describe_{i}_{name}"
            tool_calls_payload.append(
                {
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": "describe_table",
                        "arguments": json.dumps(args, ensure_ascii=False),
                    },
                }
            )
        working.append(
            {
                "role": "assistant",
                "content": "服务端要求：先对 SQL 涉表完成 describe_table。",
                "tool_calls": tool_calls_payload,
            }
        )
        for tc in tool_calls_payload:
            fn = tc["function"]
            args = json.loads(fn["arguments"])
            await _invoke_tool("describe_table", args, tc["id"])
        working.append(
            {
                "role": "user",
                "content": (
                    "以上为涉表 describe_table 结果（含 knowledge 切片若有）。"
                    "请先用 knowledge/列含义再次核对所选表是否匹配用户问题；不符则换表并重新 describe。"
                    "确认无误后，仅使用真实列名重写工作流 JSON；禁止臆造列名；不要再省略 describe。"
                ),
            }
        )

    for step in range(steps):
        working, fold_meta = fold_working_messages(
            working,
            budget_chars=settings.context_working_budget_chars,
            keep_recent_tool_rounds=settings.context_keep_recent_tool_rounds,
        )
        if fold_meta.get("compressed"):
            await spans.record(
                session,
                phase="generate",
                kind="GRAPH",
                name="context_fold_working",
                status="OK",
                parent_span_id=parent_span,
                payload_meta={
                    **fold_meta,
                    "parent": parent_span_name,
                    "tool_agent_step": step,
                },
                **ctx,
            )
        prompt_messages = list(working)
        resp = await llm.chat(messages=working, tools=tools, tool_choice="auto")
        msg = resp["message"]
        round_meta = build_llm_rounds_meta(
            messages=prompt_messages,
            response=msg,
            step=step,
            role=parent_span_name,
        )
        collected_rounds.extend(round_meta.get("llmRounds") or [])
        from dbc_askdata.llm.registry import resolve_model_name

        step_model = resp.get("model") or resolve_model_name(settings, tier="default")
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name=f"{parent_span_name}#llm{step}",
            model=step_model,
            status="OK",
            latency_ms=resp.get("latency_ms"),
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            parent_span_id=parent_span,
            payload_meta={
                "tool_agent_step": step,
                "parent": parent_span_name,
                "working_chars": estimate_messages_chars(working),
                **round_meta,
            },
            **ctx,
        )
        tool_calls = msg.get("tool_calls") or []
        working.append(msg)
        if tool_calls:
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name") or ""
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                args.setdefault("workspace_id", workspace_id)
                args.setdefault("connection_id", connection_id)
                if database:
                    args.setdefault("database", database)
                if schema:
                    args.setdefault("schema", schema)
                await _invoke_tool(name, args, tc.get("id") or name)
            continue

        content = msg.get("content") or ""
        if not on_final_content:
            await _flush_parent_rounds()
            return content

        draft = on_final_content(content)
        if not isinstance(draft, dict):
            if not json_nudge_used and step + 1 < steps:
                json_nudge_used = True
                log.info("工作流 JSON 解析失败，要求模型重出 parent=%s", parent_span_name)
                working.append(
                    {
                        "role": "user",
                        "content": (
                            "上轮输出无法解析为工作流 JSON。请只输出严格 JSON（不要 Markdown、不要解释）："
                            '{"name":"工作流名","nodes":[{"id":"n1","type":"QUERY","title":"...","sql":"SELECT ...","readonly":true}]}'
                        ),
                    }
                )
                continue
            await _flush_parent_rounds()
            return draft
        if not require_describe_tables:
            await _flush_parent_rounds()
            return draft

        needed = source_tables_from_draft(draft, default_schema=schema)
        missing: set[str] = set()
        for key in needed:
            bare = key.rsplit(".", 1)[-1]
            if key in described or bare in described:
                continue
            if any(d == key or d == bare or d.endswith(f".{bare}") for d in described):
                continue
            missing.add(key)

        if not missing:
            await _flush_parent_rounds()
            return draft

        if not describe_nudge_used and step + 1 < steps:
            describe_nudge_used = True
            log.info(
                "SQL 涉表未 describe，服务端补探测 parent=%s missing=%s",
                parent_span_name,
                sorted(missing),
            )
            await _auto_describe(missing)
            continue

        log.warning(
            "涉表仍未完成 describe，拒绝草稿 parent=%s missing=%s",
            parent_span_name,
            sorted(missing),
        )
        await _flush_parent_rounds()
        return None

    log.warning("tool_agent 超过最大步数 parent=%s", parent_span_name)
    await _flush_parent_rounds()
    return None
