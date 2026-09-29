from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.tools.registry import ToolGateway

log = logging.getLogger(__name__)

ProgressFn = Callable[[str], Awaitable[None]]


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
) -> Any:
    """多轮 tool_call：模型自行决定是否探测；结束后把最后一条文本交给 on_final_content。"""
    tools = gateway.openai_tools()
    steps = max_steps if max_steps is not None else settings.llm_max_tool_rounds
    parent_span = await spans.record(
        session,
        phase="generate",
        kind="GRAPH",
        name=parent_span_name,
        status="OK",
        **ctx,
    )
    working = list(messages)

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
        if not tool_calls:
            content = msg.get("content") or ""
            if on_final_content:
                return on_final_content(content)
            return content

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
                result = await gateway.invoke(name, args)
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
                    "tool_call_id": tc.get("id") or name,
                    "content": payload,
                }
            )

    log.warning("tool_agent 超过最大步数 parent=%s", parent_span_name)
    return None
