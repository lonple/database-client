from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)

_redis: RedisFacade | None = None


class RedisFacade:
    """异步 Redis：分布式锁 + 工具结果缓存。锁语义对齐 SET NX EX（同 Redisson 用法）。"""

    def __init__(self, client: Any, *, key_prefix: str = "ask:") -> None:
        self._r = client
        self._prefix = key_prefix.rstrip(":") + ":"

    def _k(self, *parts: str) -> str:
        return self._prefix + ":".join(str(p) for p in parts if p is not None)

    async def get_json(self, *parts: str) -> Any | None:
        import json

        raw = await self._r.get(self._k(*parts))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            log.warning("Redis JSON 解析失败 key=%s", self._k(*parts), exc_info=True)
            return None

    async def set_json(self, *parts: str, value: Any, ttl_seconds: int) -> None:
        import json

        await self._r.set(
            self._k(*parts),
            json.dumps(value, ensure_ascii=False, default=str),
            ex=max(1, int(ttl_seconds)),
        )

    def key(self, *parts: str) -> str:
        return self._k(*parts)

    @property
    def raw(self) -> Any:
        return self._r

    async def incr(self, *parts: str) -> int:
        return int(await self._r.incr(self._k(*parts)))

    async def rpush(self, *parts: str, value: str) -> int:
        return int(await self._r.rpush(self._k(*parts), value))

    async def lrange(self, *parts: str, start: int = 0, end: int = -1) -> list[str]:
        rows = await self._r.lrange(self._k(*parts), start, end)
        return list(rows or [])

    async def delete(self, *parts: str) -> None:
        await self._r.delete(self._k(*parts))

    async def expire(self, *parts: str, ttl_seconds: int) -> None:
        await self._r.expire(self._k(*parts), max(1, int(ttl_seconds)))

    async def xadd(
        self,
        stream_parts: tuple[str, ...],
        fields: dict[str, str],
        *,
        maxlen: int = 200_000,
    ) -> str:
        return str(
            await self._r.xadd(
                self._k(*stream_parts),
                fields,
                maxlen=maxlen,
                approximate=True,
            )
        )

    async def xgroup_create(
        self,
        stream_parts: tuple[str, ...],
        group: str,
        *,
        mkstream: bool = True,
    ) -> None:
        try:
            await self._r.xgroup_create(self._k(*stream_parts), group, id="0", mkstream=mkstream)
        except Exception as ex:
            # BUSYGROUP = 已存在
            if "BUSYGROUP" not in str(ex).upper():
                raise

    async def xreadgroup(
        self,
        *,
        group: str,
        consumer: str,
        stream_parts: tuple[str, ...],
        count: int = 32,
        block_ms: int = 1000,
    ) -> list[Any]:
        return await self._r.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={self._k(*stream_parts): ">"},
            count=count,
            block=block_ms,
        )

    async def xack(self, stream_parts: tuple[str, ...], group: str, *ids: str) -> None:
        if not ids:
            return
        await self._r.xack(self._k(*stream_parts), group, *ids)

    @asynccontextmanager
    async def lock(self, *parts: str, ttl_seconds: int = 30, wait_seconds: float = 10.0) -> AsyncIterator[None]:
        """获取锁；超时抛 RuntimeError。"""
        import asyncio
        import time

        key = self._k("lock", *parts)
        token = str(uuid.uuid4())
        deadline = time.monotonic() + max(0.1, wait_seconds)
        acquired = False
        while time.monotonic() < deadline:
            ok = await self._r.set(key, token, nx=True, ex=max(1, int(ttl_seconds)))
            if ok:
                acquired = True
                break
            await asyncio.sleep(0.05)
        if not acquired:
            raise RuntimeError(f"获取分布式锁超时: {key}")
        try:
            yield
        finally:
            # 仅删除自己的锁
            lua = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            end
            return 0
            """
            try:
                await self._r.eval(lua, 1, key, token)
            except Exception:
                log.warning("释放分布式锁失败 key=%s", key, exc_info=True)


async def init_redis(settings: Settings) -> RedisFacade | None:
    global _redis
    if not settings.redis_enabled:
        log.info("Redis 未启用（DBC_ASKDATA_REDIS_ENABLED=false），锁与工具缓存降级为本地无锁")
        _redis = None
        return None
    try:
        from redis.asyncio import Redis

        client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=True,
        )
        await client.ping()
        _redis = RedisFacade(client, key_prefix=settings.redis_key_prefix)
        log.info("Redis 已连接 %s:%s db=%s", settings.redis_host, settings.redis_port, settings.redis_db)
        return _redis
    except Exception:
        log.error("Redis 连接失败，锁与工具缓存不可用", exc_info=True)
        if settings.redis_required:
            raise
        _redis = None
        return None


def get_redis() -> RedisFacade | None:
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is None:
        return
    try:
        await _redis._r.aclose()
    except Exception:
        log.warning("关闭 Redis 失败", exc_info=True)
    _redis = None
