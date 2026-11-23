from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select

from dbc_askdata.observability.turn import get_bound_turn_id

log = logging.getLogger(__name__)

_lock = asyncio.Lock()
# Redis 不可用时的本机热缓存：turn_id -> lines
_local_by_turn: dict[int, list[dict[str, Any]]] = {}
_WORKLOG_TTL = 6 * 3600  # turn 异常未结束时的兜底过期


async def clear_work_logs(session_id: int) -> None:
    """清空某会话全部工作日志（热缓存 + DB）。用于清空会话消息。"""
    # 先查该会话相关 turn，再删 redis
    turn_ids: list[int] = []
    try:
        from dbc_askdata.db.models import AskTurn, AskWorkLog
        from dbc_askdata.db.session import SessionLocal

        async with SessionLocal() as s:
            turn_ids = [
                int(x)
                for x in (
                    await s.execute(
                        select(AskTurn.id).where(AskTurn.session_id == int(session_id))
                    )
                )
                .scalars()
                .all()
            ]
            await s.execute(delete(AskWorkLog).where(AskWorkLog.session_id == int(session_id)))
            await s.commit()
    except Exception:
        log.warning("clear_work_logs db failed session_id=%s", session_id, exc_info=True)

    for tid in turn_ids:
        await evict_turn_cache(tid)
    async with _lock:
        for tid in list(_local_by_turn.keys()):
            buf = _local_by_turn.get(tid) or []
            if any(x.get("sessionId") == session_id for x in buf):
                _local_by_turn.pop(tid, None)


async def evict_turn_cache(turn_id: int | None) -> None:
    """整轮 turn 结束后移除热缓存（Redis + 本地）。"""
    if turn_id is None:
        return
    tid = int(turn_id)
    async with _lock:
        _local_by_turn.pop(tid, None)
    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is None:
        return
    try:
        await redis.delete("worklog", "turn", str(tid))
        await redis.delete("worklog", "seq", str(tid))
    except Exception:
        log.warning("evict worklog redis failed turn_id=%s", tid, exc_info=True)


async def append_work_log(
    session_id: int | None,
    message: str,
    *,
    level: str = "INFO",
    turn_id: int | None = None,
) -> None:
    """写热缓存（Redis 优先）并入队异步落库。主流程不等待 DB。"""
    tid = int(turn_id) if turn_id is not None else get_bound_turn_id()
    sid = int(session_id) if session_id else 0
    text = (message or "").strip()
    if not text or tid is None:
        if tid is None:
            log.debug("append_work_log skipped: no turn_id session_id=%s", sid)
        return

    seq = await _next_seq(tid)
    at = datetime.now(timezone.utc).isoformat()
    lvl = (level or "INFO").upper()[:16]
    line = {
        "id": seq,  # 前端 after 游标用 seq
        "seq": seq,
        "at": at,
        "level": lvl,
        "message": text[:4000],
        "sessionId": sid,
        "turnId": tid,
    }
    await _cache_append(tid, line)

    from dbc_askdata.observability.obs_queue import enqueue

    await enqueue(
        {
            "type": "work_log",
            "turnId": tid,
            "sessionId": sid,
            "seq": seq,
            "level": lvl,
            "message": text[:4000],
            "at": at,
        }
    )


async def list_work_logs(
    session_id: int,
    *,
    turn_id: int | None = None,
    after: int = 0,
) -> dict[str, Any]:
    """热缓存优先；未命中读库。读库结果不回填缓存。"""
    sid = int(session_id)
    tid = int(turn_id) if turn_id is not None else await _latest_turn_id(sid)
    after_id = max(0, int(after or 0))
    if tid is None:
        return {"total": 0, "items": [], "next": after_id, "turnId": None}

    cached = await _cache_list(tid)
    if cached is not None:
        items = [x for x in cached if int(x.get("seq") or x.get("id") or 0) > after_id]
        next_id = after_id
        for x in items:
            n = int(x.get("seq") or x.get("id") or 0)
            if n > next_id:
                next_id = n
        return {
            "total": len(cached),
            "items": [_public(x) for x in items],
            "next": next_id,
            "turnId": tid,
        }

    # DB
    try:
        from dbc_askdata.db.models import AskWorkLog
        from dbc_askdata.db.session import SessionLocal

        async with SessionLocal() as s:
            q = (
                select(AskWorkLog)
                .where(AskWorkLog.turn_id == tid, AskWorkLog.session_id == sid)
                .order_by(AskWorkLog.seq.asc().nulls_last(), AskWorkLog.id.asc())
            )
            rows = (await s.execute(q.limit(2000))).scalars().all()
            all_items = [
                {
                    "id": int(r.seq if r.seq is not None else r.id),
                    "seq": int(r.seq if r.seq is not None else r.id),
                    "at": r.created_at.isoformat() if r.created_at else "",
                    "level": r.level or "INFO",
                    "message": r.message,
                }
                for r in rows
            ]
            items = [x for x in all_items if x["seq"] > after_id]
            next_id = after_id
            for x in items:
                if x["seq"] > next_id:
                    next_id = x["seq"]
            return {
                "total": len(all_items),
                "items": [_public(x) for x in items],
                "next": next_id,
                "turnId": tid,
            }
    except Exception:
        log.warning("list_work_logs db failed turn_id=%s", tid, exc_info=True)
        return {"total": 0, "items": [], "next": after_id, "turnId": tid}


def _public(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id") or x.get("seq"),
        "at": x.get("at") or "",
        "level": x.get("level") or "INFO",
        "message": x.get("message") or "",
    }


async def _next_seq(turn_id: int) -> int:
    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is not None:
        try:
            return await redis.incr("worklog", "seq", str(turn_id))
        except Exception:
            log.warning("worklog seq incr redis failed", exc_info=True)
    async with _lock:
        buf = _local_by_turn.setdefault(turn_id, [])
        return len(buf) + 1


async def _cache_append(turn_id: int, line: dict[str, Any]) -> None:
    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is not None:
        try:
            await redis.rpush(
                "worklog",
                "turn",
                str(turn_id),
                value=json.dumps(line, ensure_ascii=False, default=str),
            )
            await redis.expire("worklog", "turn", str(turn_id), ttl_seconds=_WORKLOG_TTL)
            await redis.expire("worklog", "seq", str(turn_id), ttl_seconds=_WORKLOG_TTL)
            return
        except Exception:
            log.warning("worklog redis rpush failed，降级本地", exc_info=True)
    async with _lock:
        buf = _local_by_turn.setdefault(turn_id, [])
        buf.append(line)
        if len(buf) > 500:
            del buf[: len(buf) - 500]


async def _cache_list(turn_id: int) -> list[dict[str, Any]] | None:
    """有缓存返回 list（可空列表表示 turn 已建但尚无行）；无 key 返回 None → 走 DB。"""
    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is not None:
        try:
            raw_rows = await redis.lrange("worklog", "turn", str(turn_id), start=0, end=-1)
            if raw_rows:
                out: list[dict[str, Any]] = []
                for raw in raw_rows:
                    try:
                        out.append(json.loads(raw))
                    except Exception:
                        continue
                return out
            # key 不存在 vs 空 list：用 EXISTS 区分
            exists = await redis.raw.exists(redis.key("worklog", "turn", str(turn_id)))
            if exists:
                return []
        except Exception:
            log.warning("worklog redis lrange failed", exc_info=True)

    async with _lock:
        if turn_id in _local_by_turn:
            return list(_local_by_turn[turn_id])
    return None


async def _latest_turn_id(session_id: int) -> int | None:
    """未指定 turn 时：优先进行中的 RUNNING/HITL，避免锁死在上一轮已结束 turn。"""
    try:
        from dbc_askdata.db.models import AskTurn
        from dbc_askdata.db.session import SessionLocal
        from dbc_askdata.observability.turn import TURN_STATUS_HITL, TURN_STATUS_RUNNING

        async with SessionLocal() as s:
            active = (
                await s.execute(
                    select(AskTurn.id)
                    .where(
                        AskTurn.session_id == int(session_id),
                        AskTurn.status.in_((TURN_STATUS_RUNNING, TURN_STATUS_HITL)),
                    )
                    .order_by(AskTurn.id.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if active is not None:
                return int(active)
            row = (
                await s.execute(
                    select(AskTurn.id)
                    .where(AskTurn.session_id == int(session_id))
                    .order_by(AskTurn.id.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            return int(row) if row is not None else None
    except Exception:
        log.warning("latest turn lookup failed session_id=%s", session_id, exc_info=True)
        return None
