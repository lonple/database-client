"""问数 chat 进程内并发闸（单实例）。"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import HTTPException

log = logging.getLogger(__name__)

_DEFAULT = 20
_limit = _DEFAULT
_in_use = 0
_gate = asyncio.Lock()


def refresh_chat_semaphore(limit: int) -> None:
    """配置更新后调整上限；不重置 in_use（进行中的请求仍占槽直至结束）。"""
    global _limit
    n = max(1, min(500, int(limit)))
    _limit = n
    log.info("chat 并发闸已更新 limit=%s in_use=%s", n, _in_use)


def current_chat_limit() -> int:
    return _limit


def current_chat_in_use() -> int:
    return _in_use


@asynccontextmanager
async def acquire_chat_slot() -> AsyncIterator[None]:
    """非阻塞占槽；满则 429。用计数器，避免 wait_for(sem.acquire, timeout=0) 取消导致泄漏。"""
    global _in_use
    async with _gate:
        if _in_use >= _limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": f"问数并发已满（上限 {_limit}），请稍后重试",
                    "limit": _limit,
                    "inUse": _in_use,
                },
            )
        _in_use += 1
        held = _in_use
    log.debug("chat 占槽 in_use=%s/%s", held, _limit)
    try:
        yield
    finally:
        async with _gate:
            _in_use = max(0, _in_use - 1)
            left = _in_use
        log.debug("chat 释槽 in_use=%s/%s", left, _limit)
