"""OpenAI 兼容 Chat Completions 基类适配器。"""

from __future__ import annotations

from typing import Any

from dbc_askdata.llm.protocol import ChatRequest, ChatResponse


class OpenAICompatibleAdapter:
    """通用 OpenAI 兼容协议；子类可覆盖 body 增删字段。"""

    provider_id: str = "openai_compatible"

    def __init__(
        self,
        *,
        provider_id: str | None = None,
        enable_thinking: bool | None = None,
        default_enable_thinking: bool = False,
        pass_enable_thinking: bool = False,
    ) -> None:
        if provider_id:
            self.provider_id = provider_id
        # pass_enable_thinking=True：请求体写入 enable_thinking（千问 DashScope）
        self._pass_enable_thinking = pass_enable_thinking
        self._default_enable_thinking = default_enable_thinking
        # profile 级固定值；None 表示跟随请求
        self._fixed_enable_thinking = enable_thinking

    def build_body(self, req: ChatRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": req.model,
            "messages": req.messages,
            "temperature": req.temperature,
        }
        if req.tools:
            body["tools"] = req.tools
            if req.tool_choice is not None:
                body["tool_choice"] = req.tool_choice
        if self._pass_enable_thinking:
            if self._fixed_enable_thinking is not None:
                thinking = self._fixed_enable_thinking
            elif req.enable_thinking is not None:
                thinking = req.enable_thinking
            else:
                thinking = self._default_enable_thinking
            body["enable_thinking"] = bool(thinking)
        if req.extra:
            body.update(req.extra)
        return body

    def parse_response(
        self, data: dict[str, Any], *, requested_model: str, latency_ms: int
    ) -> ChatResponse:
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return ChatResponse(
            message=message if isinstance(message, dict) else {},
            latency_ms=latency_ms,
            token_in=int(usage.get("prompt_tokens") or 0),
            token_out=int(usage.get("completion_tokens") or 0),
            model=str(data.get("model") or requested_model),
            raw=data if isinstance(data, dict) else {},
        )
