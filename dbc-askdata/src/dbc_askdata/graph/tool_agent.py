from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.graph.sql_tables import (
    described_key_from_args,
    source_tables_from_draft,
)
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.verify.semantic import store_profile
from dbc_askdata.tools.registry import ToolGateway

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
    described: set[str] = set()
    describe_nudge_used = False
    json_nudge_used = False

    async def _invoke_tool(name: str, args: dict[str, Any], tool_call_id: str) -> None:
        nonlocal described
        if on_progress:
            hint = name
            if name == "get_column_profile":
                hint = f"枚举/列画像探测：{args.get('table')}.{args.get('column')}"
            elif name == "describe_table":
                hint = f"探测表结构：{args.get('table')}"
            elif name == "search_catalog":
                hint = f"检索目录：{args.get('keyword') or ''}"
            await on_progress(hint)

        status = "OK"
        err = None
        try:
            if name in blocked:
                raise ValueError(f"本阶段禁止调用 Tool: {name}（目录已在上下文中）")
            result = await gateway.invoke(name, args)
            if name == "describe_table":
                key = described_key_from_args(args, default_schema=schema)
                if key:
                    described.add(key)
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
            payload = json.dumps(result, ensure_ascii=False, default=str)[:8000]
        except Exception as ex:
            log.warning("tool_agent 调用失败 name=%s", name, exc_info=True)
            status = "ERROR"
            err = str(ex)
            payload = json.dumps({"error": err}, ensure_ascii=False)

        await spans.record(
            session,
            phase="generate",
            kind="TOOL",
            name=name,
            status=status,
            error_message=err,
            parent_span_id=parent_span,
            payload_meta={"args_keys": sorted(args.keys())},
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
            args: dict[str, Any] = {
                "workspace_id": workspace_id,
                "connection_id": connection_id,
                "table": name,
            }
            if database:
                args["database"] = database
            if sch or schema:
                args["schema"] = sch or schema
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
        resp = await llm.chat(messages=working, tools=tools, tool_choice="auto")
        msg = resp["message"]
        await spans.record(
            session,
            phase="generate",
            kind="LLM",
            name=resp.get("model") or settings.llm_model,
            status="OK",
            latency_ms=resp.get("latency_ms"),
            token_in=resp.get("token_in"),
            token_out=resp.get("token_out"),
            parent_span_id=parent_span,
            payload_meta={"tool_agent_step": step, "parent": parent_span_name},
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
            return draft
        if not require_describe_tables:
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
        return None

    log.warning("tool_agent 超过最大步数 parent=%s", parent_span_name)
    return None
