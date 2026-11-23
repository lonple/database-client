import pytest

from dbc_askdata.config import Settings
from dbc_askdata.observability.spans import SPAN_KINDS, SpanRecorder, mark_run_inflight


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch):
    events: list[dict] = []

    async def _enqueue(ev: dict) -> None:
        events.append(ev)

    monkeypatch.setattr("dbc_askdata.observability.obs_queue.enqueue", _enqueue)
    return events


@pytest.mark.parametrize("kind", sorted(SPAN_KINDS))
async def test_record_four_kinds_enqueue_uuid(kind: str, enqueued: list):
    key = await SpanRecorder(Settings(metrics_enabled=False)).record(
        None,
        phase="generate",
        kind=kind,
        name="router" if kind != "LLM" else "qwen",
    )
    assert isinstance(key, str) and len(key) >= 32
    upserts = [e for e in enqueued if e.get("type") == "span_upsert"]
    assert len(upserts) == 1
    assert upserts[0]["spanKey"] == key
    assert upserts[0]["kind"] == kind


async def test_unknown_kind_skipped(enqueued: list):
    key = await SpanRecorder(Settings(metrics_enabled=False)).record(
        None, phase="generate", kind="WORKFLOW", name="x"
    )
    assert key is None
    assert enqueued == []


async def test_metrics_failure_still_returns_key(monkeypatch: pytest.MonkeyPatch, enqueued: list):
    recorder = SpanRecorder(Settings(metrics_enabled=True))

    def _boom(**_kwargs):
        raise RuntimeError("metrics down")

    monkeypatch.setattr(recorder, "_observe_metrics", _boom)
    key = await recorder.record(None, phase="execute", kind="GRAPH", name="n1", status="OK")
    assert isinstance(key, str)
    assert any(e.get("type") == "span_upsert" for e in enqueued)


async def test_merge_enqueues_by_span_key(enqueued: list):
    rec = SpanRecorder(Settings(metrics_enabled=False))
    await rec.merge_payload_meta("abc-uuid", {"llmRounds": []})
    merges = [e for e in enqueued if e.get("type") == "span_merge"]
    assert len(merges) == 1
    assert merges[0]["spanKey"] == "abc-uuid"


def test_mark_run_inflight_swallows_metric_error(monkeypatch: pytest.MonkeyPatch):
    def _boom(*_a, **_k):
        raise RuntimeError("metrics down")

    monkeypatch.setattr("dbc_askdata.observability.spans.RUNS_IN_FLIGHT.inc", _boom)
    monkeypatch.setattr("dbc_askdata.observability.spans.RUNS_IN_FLIGHT.dec", _boom)
    mark_run_inflight(1)
    mark_run_inflight(-1)
