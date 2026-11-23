"""千问适配入口（逻辑在 OpenAICompatibleAdapter + profile.yaml）。"""

from __future__ import annotations

from dbc_askdata.llm.adapters.openai_compatible import OpenAICompatibleAdapter


def create_adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter(
        provider_id="qwen",
        pass_enable_thinking=True,
        enable_thinking=False,
        default_enable_thinking=False,
    )
