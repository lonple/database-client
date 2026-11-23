"""进程级共享 httpx 客户端：max_connections = max(8, 2 * CPU)。"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

_clients: dict[str, httpx.AsyncClient] = {}
_limits: httpx.Limits | None = None


def httpx_max_connections() -> int:
    cpu = os.cpu_count() or 4
    return max(8, 2 * int(cpu))


def _get_limits() -> httpx.Limits:
    global _limits
    if _limits is None:
        n = httpx_max_connections()
        _limits = httpx.Limits(
            max_connections=n,
            max_keepalive_connections=max(4, n // 2),
        )
        log.info("httpx 连接池 limits max_connections=%s", n)
    return _limits


def shared_async_client(
    name: str,
    *,
    timeout: float | httpx.Timeout,
    trust_env: bool = False,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """按逻辑名复用 AsyncClient；须在 lifespan 结束时 close_all_httpx_clients。"""
    existing = _clients.get(name)
    if existing is not None and not existing.is_closed:
        return existing
    client = httpx.AsyncClient(
        timeout=timeout,
        trust_env=trust_env,
        limits=_get_limits(),
        **kwargs,
    )
    _clients[name] = client
    return client


async def close_all_httpx_clients() -> None:
    for name, client in list(_clients.items()):
        try:
            await client.aclose()
        except Exception:
            log.warning("关闭 httpx 客户端失败 name=%s", name, exc_info=True)
        _clients.pop(name, None)


async def warmup_shared_clients(targets: list[tuple[str, str, float]]) -> None:
    """启动时预建连接池并对下游发轻量探活，降低首个 TOOL 的 TCP/TLS 冷启动。

    targets: (pool_name, url, timeout_seconds)
    探活失败不阻断启动（下游可能尚未就绪）。
    """
    import asyncio

    async def _one(name: str, url: str, timeout: float) -> None:
        # 探活用短超时，避免 sqlwork/memory 业务超时把启动拖住
        probe_timeout = min(float(timeout), 3.0)
        try:
            client = shared_async_client(name, timeout=timeout, trust_env=False)
            await client.get(url, timeout=probe_timeout)
            log.info("httpx warmup ok name=%s url=%s", name, url)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as ex:
            log.warning(
                "httpx warmup 跳过（下游未就绪） name=%s url=%s err=%s",
                name,
                url,
                ex.__class__.__name__,
            )
        except Exception:
            log.warning("httpx warmup 失败 name=%s url=%s", name, url, exc_info=True)

    await asyncio.gather(*[_one(n, u, t) for n, u, t in targets])
