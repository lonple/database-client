from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.redis.client import get_redis

log = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Shanghai")


class QuotaExceeded(Exception):
    def __init__(self, *, used: int, limit: int, usage_date: date) -> None:
        self.used = used
        self.limit = limit
        self.usage_date = usage_date
        super().__init__(f"今日 LLM token 额度已用尽 used={used} limit={limit}")


def today_shanghai() -> date:
    return datetime.now(_TZ).date()


async def get_daily_usage(session: AsyncSession, *, user_id: int, usage_date: date | None = None) -> int:
    d = usage_date or today_shanghai()
    row = (
        await session.execute(
            text(
                "SELECT tokens_used FROM askdata.ask_user_token_daily "
                "WHERE user_id = :uid AND usage_date = :d"
            ),
            {"uid": user_id, "d": d},
        )
    ).first()
    return int(row[0]) if row else 0


async def check_quota_or_raise(
    session: AsyncSession,
    settings: Settings,
    *,
    user_id: int,
    eval_mode: bool = False,
) -> None:
    """真人问数入口：超限抛 HTTP 429。测评跳过。"""
    if eval_mode:
        return
    limit = int(settings.daily_token_limit or 0)
    try:
        from dbc_askdata.app_config.service import get_askdata_runtime_config

        cfg = await get_askdata_runtime_config(session)
        limit = int(cfg.daily_token_limit)
    except Exception:
        log.debug("读取应用配置日限额失败，回退 Settings", exc_info=True)
    if limit <= 0:
        return
    used = await get_daily_usage(session, user_id=user_id)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "今日问数 LLM token 额度已用尽，请明日再试或联系管理员调高限额",
                "used": used,
                "limit": limit,
                "usageDate": str(today_shanghai()),
            },
        )


async def add_tokens(
    session: AsyncSession,
    settings: Settings,
    *,
    user_id: int,
    tokens: int,
    eval_mode: bool = False,
) -> int:
    """累加日用量；测评不计。返回累加后用量。"""
    if eval_mode or tokens <= 0:
        return await get_daily_usage(session, user_id=user_id)
    limit = int(settings.daily_token_limit or 0)
    if limit <= 0 and not settings.daily_token_track_when_unlimited:
        return 0
    d = today_shanghai()
    redis = get_redis()

    async def _do() -> int:
        await session.execute(
            text(
                """
                INSERT INTO askdata.ask_user_token_daily (user_id, usage_date, tokens_used, updated_at)
                VALUES (:uid, :d, :n, NOW())
                ON CONFLICT (user_id, usage_date)
                DO UPDATE SET
                    tokens_used = askdata.ask_user_token_daily.tokens_used + EXCLUDED.tokens_used,
                    updated_at = NOW()
                """
            ),
            {"uid": user_id, "d": d, "n": int(tokens)},
        )
        await session.commit()
        return await get_daily_usage(session, user_id=user_id, usage_date=d)

    if redis is None:
        return await _do()
    try:
        async with redis.lock("quota", str(user_id), str(d), ttl_seconds=15, wait_seconds=5):
            return await _do()
    except Exception:
        log.warning("配额累加加锁失败，降级直写 user_id=%s", user_id, exc_info=True)
        return await _do()
