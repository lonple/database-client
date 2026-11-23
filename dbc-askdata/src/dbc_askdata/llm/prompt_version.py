"""本次 LLM 调用解析出的提示词版本，供日志在同一次调用后读取。"""

from __future__ import annotations

import contextvars

_current: contextvars.ContextVar[str] = contextvars.ContextVar(
    "askdata_prompt_version",
    default="",
)


def bind_prompt_version(version: str) -> None:
    _current.set((version or "").strip())


def current_prompt_version() -> str:
    return _current.get() or ""
