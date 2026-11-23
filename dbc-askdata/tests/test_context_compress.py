from __future__ import annotations

import json

from dbc_askdata.context.compress import (
    estimate_messages_chars,
    fold_working_messages,
    slim_tool_result,
)


def test_slim_describe_table_keeps_columns_and_trims_knowledge() -> None:
    raw = {
        "columns": [
            {"name": "id", "dataType": "int", "nullable": False, "comment": "主键", "extra": "x"},
            {"name": "status", "dataType": "varchar", "nullable": True},
        ],
        "knowledge": {
            "query": "员工",
            "units": [
                {"title": "t1", "summary": "s1", "body": "很长" * 100},
                {"title": "t2", "summary": "s2"},
                {"title": "t3", "summary": "s3"},
                {"title": "t4", "summary": "s4"},
            ],
        },
    }
    out = slim_tool_result("describe_table", raw, max_chars=8000)
    data = json.loads(out)
    assert len(data["columns"]) == 2
    assert data["columns"][0]["name"] == "id"
    assert "extra" not in data["columns"][0]
    assert len(data["knowledge"]["units"]) == 3


def test_slim_respects_max_chars() -> None:
    raw = {"columns": [{"name": f"c{i}", "dataType": "int"} for i in range(200)]}
    out = slim_tool_result("describe_table", raw, max_chars=200)
    assert len(out) <= 200
    assert "truncated" in out


def test_fold_working_when_over_budget() -> None:
    messages: list[dict] = [{"role": "system", "content": "sys"}]
    for i in range(4):
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"tc{i}",
                        "type": "function",
                        "function": {"name": "describe_table", "arguments": "{}"},
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": f"tc{i}",
                "content": "x" * 5000,
            }
        )
    folded, meta = fold_working_messages(messages, budget_chars=8000, keep_recent_tool_rounds=1)
    assert meta["compressed"] is True
    assert meta["folded_tool_rounds"] >= 1
    assert estimate_messages_chars(folded) < estimate_messages_chars(messages)
    assert any("上下文压缩" in str(m.get("content") or "") for m in folded)


def test_fold_noop_when_under_budget() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    out, meta = fold_working_messages(messages, budget_chars=10_000)
    assert meta["compressed"] is False
    assert out == messages