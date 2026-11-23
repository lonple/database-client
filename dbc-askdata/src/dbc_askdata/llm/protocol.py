"""LLM 厂商适配协议：请求组装与响应归一化。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

ModelTier = Literal["default", "light"]

PROMPT_KEYS = (
    "gate_system",
    "fine_router_system",
    "chat_system",
    "build_system",
    "govern_system",
    "review_system",
    "table_intent_system",
)


@dataclass
class ChatRequest:
    messages: list[dict[str, Any]]
    model: str
    temperature: float = 0.1
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = "auto"
    enable_thinking: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    message: dict[str, Any]
    latency_ms: int
    token_in: int
    token_out: int
    model: str
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LlmAdapter(Protocol):
    """厂商请求差异关在 Adapter；图编排不得按厂商名分支。"""

    provider_id: str

    def build_body(self, req: ChatRequest) -> dict[str, Any]:
        """组装 POST /chat/completions JSON body。"""
        ...

    def parse_response(self, data: dict[str, Any], *, requested_model: str, latency_ms: int) -> ChatResponse:
        ...
