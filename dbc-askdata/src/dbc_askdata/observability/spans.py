from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.observability.metrics import (
    GRAPH_NODE_TOTAL,
    HITL_WAIT_MS,
    LLM_LATENCY,
    LLM_REQUESTS,
    LLM_TOKENS,
    RUNS_IN_FLIGHT,
    TOOL_CALLS,
)
from dbc_askdata.observability.turn import get_bound_turn_id

log = logging.getLogger(__name__)

# 详设 §6.4 / §7.4：只允许这四类，便于审计中心按 kind 聚合
SPAN_KINDS = frozenset({"LLM", "GRAPH", "TOOL", "HITL"})


class ScopeTimer:
    """节点自有耗时：墙钟减去已登记的子 span（LLM/TOOL 等）耗时。"""

    __slots__ = ("_t0", "_child_ms")

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self._child_ms = 0

    def add_child_ms(self, ms: int | None) -> None:
        if ms is None:
            return
        self._child_ms += max(0, int(ms))

    def add_parallel_ms(self, *values: int | None) -> None:
        """并行子任务只计最慢一路，避免 exclusive 被重复扣减。"""
        nums = [max(0, int(v)) for v in values if v is not None]
        if nums:
            self._child_ms += max(nums)

    def exclusive_ms(self) -> int:
        wall = int((time.monotonic() - self._t0) * 1000)
        return max(0, wall - self._child_ms)


def _filter_payload(settings: Settings, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """写入 span 前清洗：样本行剔除；llmRounds（已截断）始终保留供监控详情。"""
    del settings  # 保留参数以兼容调用方；策略固定为审计可见
    if not payload:
        return payload
    cleaned = dict(payload)
    for key in ("sample_rows", "rows"):
        cleaned.pop(key, None)
    if "llmRounds" in cleaned:
        cleaned.pop("content", None)
    return cleaned


def _default_session_factory() -> AsyncSession:
    from dbc_askdata.db.session import SessionLocal

    return SessionLocal()


class SpanRecorder:
    def __init__(
        self,
        settings: Settings,
        *,
        session_factory: Callable[[], AsyncSession] | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory or _default_session_factory

    def _default_model_label(self) -> str:
        try:
            from dbc_askdata.llm.registry import resolve_model_name

            return resolve_model_name(self._settings, tier="default") or "unknown"
        except Exception:
            return (self._settings.llm_model or "unknown").strip() or "unknown"

    async def record(
        self,
        session: AsyncSession | None = None,
        *,
        phase: str,
        kind: str,
        name: str,
        status: str = "OK",
        trace_id: str | None = None,
        turn_id: int | None = None,
        parent_span_id: int | str | None = None,
        parent_span_key: str | None = None,
        workspace_id: int | None = None,
        project_id: int | None = None,
        session_id: int | None = None,
        run_id: int | None = None,
        user_id: int | None = None,
        residency: str | None = None,
        model: str | None = None,
        latency_ms: int | None = None,
        token_in: int | None = None,
        token_out: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        payload_meta: dict[str, Any] | None = None,
        span_key: str | None = None,
    ) -> str | None:
        """入队异步落库，立即返回 span_key（UUID）。Prometheus / 配额仍同步。

        `parent_span_id` 兼容旧调用：若传入 str 则视为 parent_span_key。
        """
        del session
        if kind not in SPAN_KINDS:
            log.warning("llm span skipped: unknown kind=%s name=%s", kind, name)
            return None

        key = (span_key or str(uuid.uuid4())).strip()
        resolved_turn_id = turn_id if turn_id is not None else get_bound_turn_id()

        pkey = parent_span_key
        if pkey is None and isinstance(parent_span_id, str) and parent_span_id:
            pkey = parent_span_id
        elif pkey is None and parent_span_id is not None and not isinstance(parent_span_id, str):
            # 旧 int id 无法在异步路径可靠关联，忽略并打日志
            log.debug("span parent_span_id(int) ignored under async sink name=%s", name)

        try:
            self._observe_metrics(
                kind=kind,
                name=name,
                status=status,
                latency_ms=latency_ms,
                token_in=token_in,
                token_out=token_out,
                model=model,
            )
        except Exception:
            log.warning("span metrics failed", exc_info=True)

        if kind == "LLM":
            try:
                await self._account_quota(user_id=user_id, token_in=token_in, token_out=token_out)
            except Exception:
                log.warning("quota account failed", exc_info=True)

        from dbc_askdata.observability.obs_queue import enqueue

        await enqueue(
            {
                "type": "span_upsert",
                "spanKey": key,
                "parentSpanKey": pkey,
                "traceId": trace_id,
                "turnId": resolved_turn_id,
                "workspaceId": workspace_id,
                "projectId": project_id,
                "sessionId": session_id,
                "runId": run_id,
                "userId": user_id,
                "phase": phase,
                "kind": kind,
                "name": name,
                "residency": residency or self._settings.llm_residency,
                "model": (model or self._default_model_label()) if kind == "LLM" else model,
                "status": status,
                "latencyMs": latency_ms,
                "tokenIn": token_in,
                "tokenOut": token_out,
                "errorCode": error_code,
                "errorMessage": (error_message or "")[:1024] if error_message else None,
                "payloadMeta": _filter_payload(self._settings, payload_meta),
                "finishedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
        await enqueue(
            {
                "type": "turn_tokens",
                "turnId": resolved_turn_id,
                "tokenIn": token_in if kind == "LLM" else 0,
                "tokenOut": token_out if kind == "LLM" else 0,
                "bumpSpan": True,
            }
        )
        return key

    async def merge_payload_meta(
        self,
        span_id: int | str | None,
        patch: dict[str, Any] | None,
    ) -> None:
        """按 span_key 异步合并 payload_meta。兼容旧 int（无法映射则跳过）。"""
        if span_id is None or not patch:
            return
        if not isinstance(span_id, str):
            log.debug("merge_payload_meta skipped non-key id=%s", span_id)
            return
        from dbc_askdata.observability.obs_queue import enqueue

        await enqueue(
            {
                "type": "span_merge",
                "spanKey": span_id,
                "patch": _filter_payload(self._settings, patch) or {},
            }
        )

    async def _account_quota(
        self,
        *,
        user_id: int | None,
        token_in: int | None,
        token_out: int | None,
    ) -> None:
        from dbc_askdata.db.session import SessionLocal
        from dbc_askdata.quota.context import quota_eval_mode, quota_user_id
        from dbc_askdata.quota.service import add_tokens

        uid = user_id if user_id is not None else quota_user_id.get()
        if uid is None:
            return
        total = int(token_in or 0) + int(token_out or 0)
        if total <= 0:
            return
        async with SessionLocal() as q_session:
            await add_tokens(
                q_session,
                self._settings,
                user_id=int(uid),
                tokens=total,
                eval_mode=bool(quota_eval_mode.get()),
            )

    def _observe_metrics(
        self,
        *,
        kind: str,
        name: str,
        status: str,
        latency_ms: int | None,
        token_in: int | None,
        token_out: int | None,
        model: str | None,
    ) -> None:
        if not self._settings.metrics_enabled:
            return
        model_label = model or self._default_model_label()
        residency = self._settings.llm_residency
        if kind == "LLM":
            LLM_REQUESTS.labels(model=model_label, residency=residency, status=status).inc()
            if latency_ms is not None:
                LLM_LATENCY.labels(model=model_label).observe(latency_ms)
            if token_in:
                LLM_TOKENS.labels(direction="in", model=model_label).inc(token_in)
            if token_out:
                LLM_TOKENS.labels(direction="out", model=model_label).inc(token_out)
        elif kind == "TOOL":
            TOOL_CALLS.labels(tool=name, status=status).inc()
        elif kind == "GRAPH":
            GRAPH_NODE_TOTAL.labels(node=name, status=status).inc()
        elif kind == "HITL" and latency_ms is not None:
            HITL_WAIT_MS.observe(latency_ms)


def mark_run_inflight(delta: int) -> None:
    try:
        if delta >= 0:
            RUNS_IN_FLIGHT.inc(delta)
        else:
            RUNS_IN_FLIGHT.dec(abs(delta))
    except Exception:
        log.warning("runs_in_flight metric failed", exc_info=True)
