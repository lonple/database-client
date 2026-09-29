from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import Header, Request

# 与 ask_llm_span.trace_id String(64) 对齐；允许 UUID / 网关常见格式
_TRACE_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def resolve_trace_id(raw: str | None) -> str:
    """规范化入站 TraceId；缺省或非法则服务端生成 UUID（无连字符，32 位）。"""
    if raw:
        tid = raw.strip()
        if _TRACE_RE.fullmatch(tid):
            return tid[:64]
    return uuid.uuid4().hex


def get_trace_id(
    request: Request,
    x_trace_id: Annotated[str | None, Header(alias="X-Trace-Id")] = None,
) -> str:
    """优先用中间件已解析的 request.state.trace_id，否则解析请求头。"""
    existing = getattr(request.state, "trace_id", None)
    if isinstance(existing, str) and existing:
        return existing
    tid = resolve_trace_id(x_trace_id)
    request.state.trace_id = tid
    return tid
