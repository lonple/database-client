from __future__ import annotations

from dbc_askdata.graph.time_context import current_time_context, current_time_system_suffix


def test_current_time_context_shanghai_fields():
    ctx = current_time_context()
    assert ctx["timezone"] == "Asia/Shanghai"
    assert isinstance(ctx["year"], int) and ctx["year"] >= 2024
    assert str(ctx["today"]).startswith(str(ctx["year"]))
    assert "旧年份" in str(ctx["instruction"])
    assert str(ctx["year"]) in current_time_system_suffix()
