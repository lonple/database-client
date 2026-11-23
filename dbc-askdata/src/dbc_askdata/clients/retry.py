from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


async def with_one_retry(label: str, fn: Callable[[], Awaitable[T]]) -> T:
    """失败后重试一次；第二次仍失败则抛出原异常。"""
    try:
        return await fn()
    except Exception as first:
        log.warning("%s 失败，重试一次", label, exc_info=True)
        try:
            return await fn()
        except Exception:
            log.error("%s 重试仍失败", label, exc_info=True)
            raise first
