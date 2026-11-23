from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import uuid
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

STREAM = ("obs", "stream")
GROUP = "askdata-obs"
_LOCAL_MAX = 20_000

_local_q: asyncio.Queue[dict[str, Any]] | None = None
_worker_task: asyncio.Task[None] | None = None
_stopping = False


def _consumer_name() -> str:
    host = socket.gethostname()[:24]
    return f"{host}-{os.getpid()}"


def _ensure_local() -> asyncio.Queue[dict[str, Any]]:
    global _local_q
    if _local_q is None:
        _local_q = asyncio.Queue(maxsize=_LOCAL_MAX)
    return _local_q


async def enqueue(event: dict[str, Any]) -> None:
    """主流程只入队：优先 Redis Stream，失败降级进程内 Queue。"""
    payload = dict(event)
    payload.setdefault("eventId", str(uuid.uuid4()))
    payload.setdefault("enqueuedAt", datetime.now(timezone.utc).isoformat())
    raw = json.dumps(payload, ensure_ascii=False, default=str)

    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is not None:
        try:
            await redis.xadd(STREAM, {"payload": raw})
            return
        except Exception:
            log.warning("obs Redis Stream 入队失败，降级本地队列", exc_info=True)

    q = _ensure_local()
    try:
        q.put_nowait(payload)
    except asyncio.QueueFull:
        try:
            _ = q.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            log.error("obs 本地队列已满，丢弃事件 type=%s", payload.get("type"))


async def start_obs_worker() -> None:
    global _worker_task, _stopping
    _stopping = False
    if _worker_task and not _worker_task.done():
        return
    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is not None:
        try:
            await redis.xgroup_create(STREAM, GROUP, mkstream=True)
        except Exception:
            log.warning("创建 obs consumer group 失败", exc_info=True)
    _worker_task = asyncio.create_task(_worker_loop(), name="askdata-obs-worker")
    log.info("观测异步 worker 已启动")


async def stop_obs_worker() -> None:
    global _worker_task, _stopping
    _stopping = True
    t = _worker_task
    _worker_task = None
    if t is None:
        return
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    except Exception:
        log.warning("停止 obs worker 异常", exc_info=True)


async def _worker_loop() -> None:
    while not _stopping:
        try:
            n = await _drain_once()
            if n == 0:
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("obs worker 循环异常", exc_info=True)
            await asyncio.sleep(0.5)


async def _drain_once() -> int:
    handled = 0
    from dbc_askdata.redis.client import get_redis

    redis = get_redis()
    if redis is not None:
        try:
            rows = await redis.xreadgroup(
                group=GROUP,
                consumer=_consumer_name(),
                stream_parts=STREAM,
                count=64,
                block_ms=200,
            )
            if rows:
                for _stream, messages in rows:
                    ids: list[str] = []
                    for msg_id, fields in messages:
                        handled += 1
                        ids.append(str(msg_id))
                        raw = fields.get("payload") if isinstance(fields, dict) else None
                        if not raw:
                            continue
                        try:
                            ev = json.loads(raw)
                        except Exception:
                            log.warning("obs 事件 JSON 解析失败 id=%s", msg_id, exc_info=True)
                            continue
                        await _handle_event(ev)
                    await redis.xack(STREAM, GROUP, *ids)
        except Exception:
            log.warning("obs Redis 消费失败，改抽本地队列", exc_info=True)

    q = _local_q
    if q is not None:
        while True:
            try:
                ev = q.get_nowait()
            except asyncio.QueueEmpty:
                break
            handled += 1
            await _handle_event(ev)
    return handled


async def _handle_event(ev: dict[str, Any]) -> None:
    typ = str(ev.get("type") or "")
    try:
        if typ == "work_log":
            await _persist_work_log(ev)
        elif typ == "span_upsert":
            await _persist_span(ev)
        elif typ == "span_merge":
            await _merge_span(ev)
        elif typ == "turn_tokens":
            await _persist_turn_tokens(ev)
        elif typ == "audit_biz":
            await _persist_audit(ev)
        elif typ == "worklog_evict":
            # 缓存清理在入队侧同步做；此处兜底
            from dbc_askdata.observability.worklog import evict_turn_cache

            await evict_turn_cache(ev.get("turnId"))
        else:
            log.warning("未知 obs 事件 type=%s", typ)
    except Exception:
        log.warning("obs 事件处理失败 type=%s eventId=%s", typ, ev.get("eventId"), exc_info=True)


async def _persist_work_log(ev: dict[str, Any]) -> None:
    from dbc_askdata.db.models import AskWorkLog
    from dbc_askdata.db.session import SessionLocal

    turn_id = int(ev["turnId"])
    session_id = int(ev.get("sessionId") or 0)
    seq = int(ev["seq"])
    async with SessionLocal() as s:
        # 幂等：同 turn+seq 已存在则跳过
        from sqlalchemy import select

        exists = (
            await s.execute(
                select(AskWorkLog.id).where(
                    AskWorkLog.turn_id == turn_id, AskWorkLog.seq == seq
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            return
        s.add(
            AskWorkLog(
                turn_id=turn_id,
                session_id=session_id,
                seq=seq,
                level=str(ev.get("level") or "INFO")[:16],
                message=str(ev.get("message") or "")[:4000],
                created_at=_parse_ts(ev.get("at")),
            )
        )
        await s.commit()


async def _persist_span(ev: dict[str, Any]) -> None:
    from sqlalchemy import select

    from dbc_askdata.db.models import AskLlmSpan
    from dbc_askdata.db.session import SessionLocal

    span_key = str(ev.get("spanKey") or "")
    if not span_key:
        return
    parent_key = ev.get("parentSpanKey")
    parent_key_s = str(parent_key) if parent_key else None
    async with SessionLocal() as s:
        existing = (
            await s.execute(select(AskLlmSpan).where(AskLlmSpan.span_key == span_key))
        ).scalar_one_or_none()
        if existing is not None:
            return
        parent_id = None
        if parent_key_s:
            prow = (
                await s.execute(
                    select(AskLlmSpan.id).where(AskLlmSpan.span_key == parent_key_s)
                )
            ).scalar_one_or_none()
            if prow is not None:
                parent_id = int(prow)
        s.add(
            AskLlmSpan(
                span_key=span_key,
                parent_span_key=parent_key_s,
                parent_span_id=parent_id,
                trace_id=ev.get("traceId"),
                turn_id=ev.get("turnId"),
                workspace_id=ev.get("workspaceId"),
                project_id=ev.get("projectId"),
                session_id=ev.get("sessionId"),
                run_id=ev.get("runId"),
                user_id=ev.get("userId"),
                phase=str(ev.get("phase") or "generate")[:16],
                kind=str(ev.get("kind") or "GRAPH")[:16],
                name=str(ev.get("name") or "")[:128],
                residency=ev.get("residency"),
                model=ev.get("model"),
                status=str(ev.get("status") or "OK")[:16],
                latency_ms=ev.get("latencyMs"),
                token_in=ev.get("tokenIn"),
                token_out=ev.get("tokenOut"),
                error_code=ev.get("errorCode"),
                error_message=(str(ev["errorMessage"])[:1024] if ev.get("errorMessage") else None),
                payload_meta=ev.get("payloadMeta"),
                finished_at=_parse_ts(ev.get("finishedAt")) or datetime.now(timezone.utc),
            )
        )
        await s.commit()


async def _merge_span(ev: dict[str, Any]) -> None:
    from sqlalchemy import select

    from dbc_askdata.db.models import AskLlmSpan
    from dbc_askdata.db.session import SessionLocal

    span_key = str(ev.get("spanKey") or "")
    patch = ev.get("patch")
    if not span_key or not isinstance(patch, dict):
        return
    for attempt in range(8):
        async with SessionLocal() as s:
            span = (
                await s.execute(select(AskLlmSpan).where(AskLlmSpan.span_key == span_key))
            ).scalar_one_or_none()
            if span is None:
                await asyncio.sleep(0.05 * (attempt + 1))
                continue
            base = dict(span.payload_meta) if isinstance(span.payload_meta, dict) else {}
            base.update(patch)
            span.payload_meta = base
            await s.commit()
            return
    # 父 span 尚未落库：重新入队一次
    retry = int(ev.get("_retry") or 0)
    if retry < 5:
        ev2 = dict(ev)
        ev2["_retry"] = retry + 1
        await enqueue(ev2)


async def _persist_turn_tokens(ev: dict[str, Any]) -> None:
    from dbc_askdata.observability.turn import add_turn_tokens

    await add_turn_tokens(
        turn_id=ev.get("turnId"),
        token_in=ev.get("tokenIn"),
        token_out=ev.get("tokenOut"),
        bump_span=bool(ev.get("bumpSpan", True)),
    )


async def _persist_audit(ev: dict[str, Any]) -> None:
    from dbc_askdata import main as app_main

    client = app_main.audit_client
    if client is None:
        return
    await client.emit_biz_sync(
        action=str(ev.get("action") or ""),
        resource_type=str(ev.get("resourceType") or ""),
        resource_id=str(ev.get("resourceId") or ""),
        operator_user_id=int(ev.get("operatorUserId") or 0),
        operator_username=str(ev.get("operatorUsername") or ""),
        result=str(ev.get("result") or "SUCCESS"),
        fail_reason=ev.get("failReason"),
        details=ev.get("details") if isinstance(ev.get("details"), dict) else None,
        trace_id=ev.get("traceId"),
        client_ip=ev.get("clientIp"),
    )


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None
