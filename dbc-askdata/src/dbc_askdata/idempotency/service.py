from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.db.models import AskIdempotency
from dbc_askdata.redis.client import get_redis

log = logging.getLogger(__name__)


def _hash_body(payload: dict[str, Any] | None) -> str:
    raw = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def get_cached_response(
    session: AsyncSession,
    *,
    user_id: int,
    key: str,
    route: str,
) -> dict[str, Any] | None:
    row = (
        await session.execute(
            select(AskIdempotency).where(
                AskIdempotency.user_id == user_id,
                AskIdempotency.idempotency_key == key,
                AskIdempotency.route == route,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.status == "DONE" and isinstance(row.response_json, dict):
        return row.response_json
    if row.status == "RUNNING":
        raise HTTPException(status_code=409, detail="相同幂等键请求正在处理中")
    return None


async def begin_idempotent(
    session: AsyncSession,
    *,
    user_id: int,
    key: str,
    route: str,
    request_payload: dict[str, Any] | None = None,
) -> AskIdempotency:
    """创建 RUNNING 记录；重复 DONE 由调用方先 get_cached。"""
    redis = get_redis()
    req_hash = _hash_body(request_payload)

    async def _insert() -> AskIdempotency:
        existing = (
            await session.execute(
                select(AskIdempotency).where(
                    AskIdempotency.user_id == user_id,
                    AskIdempotency.idempotency_key == key,
                    AskIdempotency.route == route,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.status == "DONE" and isinstance(existing.response_json, dict):
                return existing
            if existing.status == "RUNNING":
                raise HTTPException(status_code=409, detail="相同幂等键请求正在处理中")
            existing.status = "RUNNING"
            existing.request_hash = req_hash
            existing.response_json = None
            existing.finished_at = None
            await session.commit()
            await session.refresh(existing)
            return existing
        row = AskIdempotency(
            user_id=user_id,
            idempotency_key=key,
            route=route,
            request_hash=req_hash,
            status="RUNNING",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row

    if redis is None:
        return await _insert()
    async with redis.lock("idem", str(user_id), route, key, ttl_seconds=60, wait_seconds=15):
        return await _insert()


async def finish_idempotent(
    session: AsyncSession,
    *,
    user_id: int,
    key: str,
    route: str,
    response: dict[str, Any],
) -> None:
    row = (
        await session.execute(
            select(AskIdempotency).where(
                AskIdempotency.user_id == user_id,
                AskIdempotency.idempotency_key == key,
                AskIdempotency.route == route,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return
    row.status = "DONE"
    row.response_json = response
    row.finished_at = datetime.now(timezone.utc)
    await session.commit()
