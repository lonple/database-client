from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from dbc_askdata.config import Settings
from dbc_askdata.llm.protocol import ChatRequest, ModelTier
from dbc_askdata.llm.registry import get_provider_profile, resolve_model_name

log = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


class LlmClient:
    """OpenAI 兼容 Chat Completions 门面：委托当前 Provider Profile 的 Adapter。"""

    def __init__(self, settings: Settings) -> None:
        settings.assert_llm_ready()
        self._settings = settings
        self._profile = get_provider_profile()
        self._adapter = self._profile.adapter
        # base_url：Settings 优先；若仍为千问默认而 provider 非 qwen，可改用 profile.default_base_url
        self._base = self._resolve_base_url()
        self._model = resolve_model_name(settings, tier="default", profile=self._profile)
        self._key = settings.resolved_llm_api_key()
        self._timeout = settings.llm_timeout_seconds
        if not self._model:
            raise LlmError(
                f"LLM 未解析到 default 模型（provider={self._profile.id}）；"
                "请在 profile.models.default 或 DBC_ASKDATA_LLM_MODEL 配置"
            )

    def _resolve_base_url(self) -> str:
        configured = self._settings.resolved_llm_base_url()
        profile_base = (self._profile.default_base_url or "").strip()
        if not profile_base:
            return configured
        # Settings 仍是千问默认、但 provider 已切换时，改用 profile 默认根
        qwen_default = "https://dashscope.aliyuncs.com/compatible-mode"
        configured_root = (self._settings.llm_base_url or "").strip().rstrip("/")
        if (
            self._profile.id != "qwen"
            and configured_root in ("", qwen_default, f"{qwen_default}/v1")
            and profile_base
        ):
            u = profile_base.rstrip("/")
            return u if u.endswith("/v1") else f"{u}/v1"
        return configured

    @property
    def provider_id(self) -> str:
        return self._profile.id

    @property
    def profile(self):
        return self._profile

    def model_for(self, tier: ModelTier = "default", *, explicit: str | None = None) -> str:
        return resolve_model_name(
            self._settings, tier=tier, explicit=explicit, profile=self._profile
        )

    def get_prompt(self, key: str, *, fallback: str = "") -> str:
        return self._profile.get_prompt(key, fallback=fallback)

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
        temperature: float = 0.1,
        model: str | None = None,
        enable_thinking: bool | None = None,
        tier: ModelTier | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        use_model = (model or "").strip() or (
            self.model_for(tier) if tier else self._model
        )
        req = ChatRequest(
            messages=messages,
            model=use_model,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            enable_thinking=enable_thinking,
        )
        body = self._adapter.build_body(req)
        t0 = time.monotonic()
        try:
            from dbc_askdata.httpx_pool import shared_async_client

            client = shared_async_client("llm", timeout=self._timeout, trust_env=False)
            resp = await client.post(
                f"{self._base}/chat/completions", headers=headers, json=body
            )
            if resp.status_code >= 400:
                body_preview = (resp.text or "")[:500]
                log.error(
                    "LLM HTTP 失败 status=%s provider=%s model=%s body=%s",
                    resp.status_code,
                    self._profile.id,
                    use_model,
                    body_preview,
                )
                raise LlmError(f"LLM HTTP {resp.status_code}: {body_preview}")
            data = resp.json()
        except LlmError:
            raise
        except Exception as ex:
            log.warning(
                "LLM 调用失败 provider=%s model=%s",
                self._profile.id,
                use_model,
                exc_info=True,
            )
            raise LlmError(f"LLM 调用失败: {ex}") from ex
        latency_ms = int((time.monotonic() - t0) * 1000)
        parsed = self._adapter.parse_response(
            data, requested_model=use_model, latency_ms=latency_ms
        )
        served_model = (parsed.model or use_model or "").strip()
        prompt_version = self._profile.prompt_version_for(served_model)
        from dbc_askdata.llm.prompt_version import bind_prompt_version

        bind_prompt_version(prompt_version)
        return {
            "message": parsed.message,
            "latency_ms": parsed.latency_ms,
            "token_in": parsed.token_in,
            "token_out": parsed.token_out,
            "raw": parsed.raw,
            "model": parsed.model,
            "provider": self._profile.id,
            "prompt_version": prompt_version,
        }

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """OpenAI 兼容 POST /embeddings。失败带栈抛出。"""
        payload = [str(item or "") for item in texts]
        if not payload:
            return []
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        body = {"model": self._settings.llm_embed_model, "input": payload}
        try:
            from dbc_askdata.httpx_pool import shared_async_client

            client = shared_async_client("llm", timeout=self._timeout, trust_env=False)
            resp = await client.post(f"{self._base}/embeddings", headers=headers, json=body)
            if resp.status_code >= 400:
                preview = (resp.text or "")[:500]
                log.error(
                    "embedding HTTP 失败 status=%s model=%s body=%s",
                    resp.status_code,
                    self._settings.llm_embed_model,
                    preview,
                )
                raise LlmError(f"embedding HTTP {resp.status_code}: {preview}")
            data = resp.json()
            rows = data.get("data") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                raise LlmError("embedding 响应缺少 data")
            ordered = sorted(rows, key=lambda row: int(row.get("index") or 0))
            vectors: list[list[float]] = []
            for row in ordered:
                emb = row.get("embedding") if isinstance(row, dict) else None
                if not isinstance(emb, list) or not emb:
                    raise LlmError("embedding 向量为空")
                vectors.append([float(x) for x in emb])
            if len(vectors) != len(payload):
                raise LlmError("embedding 条数与输入不一致")
            return vectors
        except LlmError:
            raise
        except Exception as ex:
            log.warning("embedding 调用失败 model=%s", self._settings.llm_embed_model, exc_info=True)
            raise LlmError(f"embedding 调用失败: {ex}") from ex

    async def chat_text(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.1,
        model: str | None = None,
        tier: ModelTier | None = None,
    ) -> dict[str, Any]:
        return await self.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tools=None,
            tool_choice=None,
            temperature=temperature,
            model=model,
            tier=tier,
        )
