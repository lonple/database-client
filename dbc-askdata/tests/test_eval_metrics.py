from types import SimpleNamespace

from dbc_askdata.eval.metrics import aggregate_metrics


def test_by_category_pass_rate():
    cases = [
        SimpleNamespace(status="PASSED", category="SINGLE_FILTER", govern_subtype=None, compare_score=1, ask_row_count=1, started_at=None, finished_at=None, compare_detail_json=None),
        SimpleNamespace(status="ASK_FAILED", category="SINGLE_FILTER", govern_subtype=None, compare_score=None, ask_row_count=None, started_at=None, finished_at=None, compare_detail_json=None),
        SimpleNamespace(status="REFUSED_OK", category="MULTI_GOVERN_FILTER", govern_subtype="HITL_NO_SUPPLEMENT", compare_score=None, ask_row_count=0, started_at=None, finished_at=None, compare_detail_json=None),
        SimpleNamespace(status="PASSED", category="MULTI_GOVERN_FILTER", govern_subtype="BOARD", compare_score=1, ask_row_count=2, started_at=None, finished_at=None, compare_detail_json=None),
    ]
    m = aggregate_metrics(cases)
    assert m["total"] == 4
    assert m["passed"] == 3
    assert m["passRate"] == 75.0
    by_cat = {x["category"]: x for x in m["byCategory"]}
    assert by_cat["SINGLE_FILTER"]["total"] == 2
    assert by_cat["SINGLE_FILTER"]["passed"] == 1
    assert by_cat["SINGLE_FILTER"]["passRate"] == 50.0
    assert by_cat["MULTI_GOVERN_FILTER"]["passed"] == 2
    assert by_cat["MULTI_GOVERN_FILTER"]["passRate"] == 100.0


def test_unknown_category_when_missing():
    cases = [
        SimpleNamespace(status="PENDING", category=None, govern_subtype=None, compare_score=None, ask_row_count=None, started_at=None, finished_at=None, compare_detail_json=None),
    ]
    m = aggregate_metrics(cases)
    assert m["byCategory"][0]["category"] == "未知"
    assert m["byCategory"][0]["passRate"] == 0.0


def test_table_select_rate_skips_unscored():
    cases = [
        SimpleNamespace(
            status="PASSED",
            category="SINGLE_FILTER",
            govern_subtype=None,
            compare_score=1,
            ask_row_count=1,
            started_at=None,
            finished_at=None,
            compare_detail_json={"tableSelect": {"scored": True, "ok": True}},
        ),
        SimpleNamespace(
            status="FAILED_COMPARE",
            category="SINGLE_FILTER",
            govern_subtype=None,
            compare_score=0,
            ask_row_count=1,
            started_at=None,
            finished_at=None,
            compare_detail_json={"tableSelect": {"scored": True, "ok": False}},
        ),
        SimpleNamespace(
            status="REFUSED_OK",
            category="MULTI_GOVERN_FILTER",
            govern_subtype="HITL_NO_SUPPLEMENT",
            compare_score=None,
            ask_row_count=0,
            started_at=None,
            finished_at=None,
            compare_detail_json={"tableSelect": {"scored": False, "reason": "hitl_no_supplement"}},
        ),
    ]
    m = aggregate_metrics(cases)
    assert m["tableSelectScored"] == 2
    assert m["tableSelectOk"] == 1
    assert m["tableSelectRate"] == 50.0

