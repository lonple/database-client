from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskLlmSpan
from dbc_askdata.observability.metrics import (
    GRAPH_NODE_TOTAL,
    HITL_WAIT_MS,
    LLM_LATENCY,
    LLM_REQUESTS,
    LLM_TOKENS,
    RUNS_IN_FLIGHT,
    TOOL_CALLS,
)

log = logging.getLogger(__name__)


def _filter_payload(settings: Settings, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return payload
    if settings.llm_residency.lower() != "cloud":
        if settings.store_prompt:
            return payload
        # local 默认也不存全量 prompt
        cleaned = dict(payload)
        cleaned.pop("prompt", None)
        cleaned.pop("sample_rows", None)
        return cleaned
    cleaned = dict(payload)
    for key in ("prompt", "sample_rows", "rows", "content"):
        cleaned.pop(key, None)
    return cleaned


class SpanRecorder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def record(
        self,
        session: AsyncSession,
        *,
        phase: str,
        kind: str,
        name: str,
        status: str = "OK",
        trace_id: str | None = None,
        parent_span_id: int | None = None,
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
    ) -> int | None:
        try:
            span = AskLlmSpan(
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                workspace_id=workspace_id,
                project_id=project_id,
                session_id=session_id,
                run_id=run_id,
                user_id=user_id,
                phase=phase,
                kind=kind,
                name=name,
                residency=residency or self._settings.llm_residency,
                model=model or self._settings.llm_model,
                status=status,
                latency_ms=latency_ms,
                token_in=token_in,
                token_out=token_out,
                error_code=error_code,
                error_message=(error_message or "")[:1024] if error_message else None,
                payload_meta=_filter_payload(self._settings, payload_meta),
                finished_at=datetime.now(timezone.utc),
            )
            session.add(span)
            await session.commit()
            await session.refresh(span)
            self._observe_metrics(kind=kind, name=name, status=status, latency_ms=latency_ms,
                                  token_in=token_in, token_out=token_out, model=model)
            return span.id
        except Exception:
            log.warning("llm span failed", exc_info=True)
            try:
                await session.rollback()
            except Exception:
                log.warning("span rollback failed", exc_info=True)
            return None

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
        model_label = model or self._settings.llm_model
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
    if delta >= 0:
        RUNS_IN_FLIGHT.inc(delta)
    else:
        RUNS_IN_FLIGHT.dec(abs(delta))
