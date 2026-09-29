from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


class LlmClient:
    """OpenAI 兼容 Chat Completions（含 tool_calls）。禁止本地假响应。"""

    def __init__(self, settings: Settings) -> None:
        settings.assert_llm_ready()
        self._settings = settings
        self._base = settings.resolved_llm_base_url()
        self._model = settings.llm_model
        self._key = settings.resolved_llm_api_key()
        self._timeout = settings.llm_timeout_seconds

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base}/chat/completions", headers=headers, json=body)
                if resp.status_code >= 400:
                    raise LlmError(f"LLM HTTP {resp.status_code}: {resp.text[:500]}")
                data = resp.json()
        except LlmError:
            raise
        except Exception as ex:
            log.warning("LLM 调用失败", exc_info=True)
            raise LlmError(f"LLM 调用失败: {ex}") from ex
        latency_ms = int((time.monotonic() - t0) * 1000)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return {
            "message": message,
            "latency_ms": latency_ms,
            "token_in": int(usage.get("prompt_tokens") or 0),
            "token_out": int(usage.get("completion_tokens") or 0),
            "raw": data,
            "model": data.get("model") or self._model,
        }

    async def chat_text(self, *, system: str, user: str, temperature: float = 0.1) -> dict[str, Any]:
        return await self.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tools=None,
            tool_choice=None,
            temperature=temperature,
        )
