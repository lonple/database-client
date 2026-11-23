"""进程内运行时覆盖（管理台保存后生效，不改环境变量）。"""

from __future__ import annotations

_llm_provider: str | None = None


def set_llm_provider(provider: str | None) -> None:
    global _llm_provider
    p = (provider or "").strip().lower()
    _llm_provider = p or None


def get_llm_provider_override() -> str | None:
    return _llm_provider
