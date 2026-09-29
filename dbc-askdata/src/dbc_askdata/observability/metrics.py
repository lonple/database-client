from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

LLM_REQUESTS = Counter(
    "askdata_llm_requests_total",
    "LLM 请求次数",
    ["model", "residency", "status"],
)
LLM_LATENCY = Histogram(
    "askdata_llm_latency_ms",
    "LLM 延迟毫秒",
    ["model"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000),
)
LLM_TOKENS = Counter(
    "askdata_llm_tokens_total",
    "Token 用量",
    ["direction", "model"],
)
GRAPH_NODE_TOTAL = Counter(
    "askdata_graph_node_total",
    "图节点执行次数",
    ["node", "status"],
)
TOOL_CALLS = Counter(
    "askdata_tool_calls_total",
    "Tool 调用次数",
    ["tool", "status"],
)
HITL_WAIT_MS = Histogram(
    "askdata_hitl_wait_ms",
    "HITL 等待毫秒",
    buckets=(1000, 5000, 15000, 60000, 300000),
)
RUNS_IN_FLIGHT = Gauge("askdata_runs_in_flight", "进行中的工作流运行数")


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
