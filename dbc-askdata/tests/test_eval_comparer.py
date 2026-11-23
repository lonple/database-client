from dbc_askdata.eval.comparer import compare_results, pick_sort_columns
from dbc_askdata.eval.expect_sql import normalize_execute_payload


def test_scalar_single_column_pass():
    expect = {"columns": [{"name": "cnt"}], "rows": [[10]]}
    ask = {"columns": [{"name": "total"}], "rows": [[10]]}
    r = compare_results(
        expect=expect,
        ask=ask,
        compare_mode="scalar",
        compare_spec={"columns": ["cnt"]},
    )
    assert r["score"] == 1.0
    assert r["status"] == "PASSED"
    assert r["detail"]["mode"] == "single_column"


def test_empty_or_refuse_ok():
    r = compare_results(
        expect=None,
        ask={"columns": [], "rows": []},
        compare_mode="empty_or_refuse",
        compare_spec={},
        refused=True,
    )
    assert r["status"] == "REFUSED_OK"


def test_empty_or_refuse_leak():
    r = compare_results(
        expect=None,
        ask={"columns": [{"name": "x"}], "rows": [[1]]},
        compare_mode="empty_or_refuse",
        compare_spec={},
        refused=False,
    )
    assert r["status"] == "REFUSED_BAD"


def test_normalize_sqlwork_statements_payload():
    raw = {
        "totalCount": 1,
        "successCount": 1,
        "statements": [
            {
                "success": True,
                "columns": [{"name": "dept_name"}, {"name": "amt"}],
                "rows": [["销售部", 10]],
                "rowCount": 1,
            }
        ],
    }
    out = normalize_execute_payload(raw)
    assert out["rowCount"] == 1
    assert out["columns"][0]["name"] == "dept_name"
    assert out["rows"] == [["销售部", 10]]


def test_missing_required_column():
    expect = {
        "columns": [{"name": "dept_name"}, {"name": "amt"}],
        "rows": [["销售部", 1]],
    }
    ask = {
        "columns": [{"name": "dept_id"}, {"name": "amt"}],
        "rows": [[2, 1]],
    }
    r = compare_results(
        expect=expect,
        ask=ask,
        compare_mode="order_by",
        compare_spec={"columns": ["dept_name", "amt"]},
    )
    assert r["status"] == "MISSING_REQUIRED"
    assert "dept_name" in (r["detail"].get("missingInAsk") or [])


def test_multi_column_same_names_pass():
    expect = {
        "columns": [{"name": "dept_name"}, {"name": "amt"}],
        "rows": [["销售部", 160781.8], ["人力资源部", 240009.97]],
    }
    ask = {
        "columns": [{"name": "dept_name"}, {"name": "amt"}],
        "rows": [["人力资源部", 240009.97], ["销售部", 160781.8]],
    }
    r = compare_results(
        expect=expect,
        ask=ask,
        compare_mode="order_by",
        compare_spec={"columns": ["dept_name", "amt"]},
    )
    assert r["status"] == "PASSED", r
    assert r["detail"]["sortColumns"] == ["dept_name"]


def test_ask_extra_rows_penalize():
    expect = {
        "columns": [{"name": "status"}, {"name": "cnt"}],
        "rows": [["a", 1], ["b", 2]],
    }
    ask = {
        "columns": [{"name": "status"}, {"name": "cnt"}],
        "rows": [["a", 1], ["b", 2], ["c", 3]],
    }
    r = compare_results(
        expect=expect,
        ask=ask,
        compare_mode="order_by",
        compare_spec={"requiredColumns": ["status", "cnt"]},
    )
    # paired match 2, excess 1 → matched' = 1, score = 1/2 = 0.5
    assert r["score"] == 0.5
    assert r["status"] == "FAILED_COMPARE"


def test_expect_more_rows_ratio():
    expect = {
        "columns": [{"name": "status"}, {"name": "cnt"}],
        "rows": [["a", 1], ["b", 2], ["c", 3]],
    }
    ask = {
        "columns": [{"name": "status"}, {"name": "cnt"}],
        "rows": [["a", 1], ["b", 2]],
    }
    r = compare_results(
        expect=expect,
        ask=ask,
        compare_mode="order_by",
        compare_spec={"columns": ["status", "cnt"]},
    )
    assert abs(r["score"] - 2 / 3) < 1e-9


def test_single_row_direct_compare():
    expect = {
        "columns": [{"name": "emp_no"}, {"name": "name"}],
        "rows": [["E1", "A"]],
    }
    ask = {
        "columns": [{"name": "emp_no"}, {"name": "name"}],
        "rows": [["E1", "A"]],
    }
    r = compare_results(
        expect=expect,
        ask=ask,
        compare_mode="scalar",
        compare_spec={"columns": ["emp_no", "name"]},
    )
    assert r["status"] == "PASSED"
    assert r["detail"]["mode"] == "single_row"


def test_pick_sort_required_unique_first():
    e_rows = [
        {"dept_name": "a", "emp_no": "E1", "total_amount": 1},
        {"dept_name": "b", "emp_no": "E2", "total_amount": 2},
    ]
    cols = pick_sort_columns(
        ["dept_name", "total_amount"],
        expect_rows=e_rows,
        ask_rows=e_rows,
        expect_cols=["dept_name", "emp_no", "total_amount"],
        ask_cols=["dept_name", "emp_no", "total_amount"],
    )
    assert cols == ["dept_name"]


def test_pick_sort_optional_unique_when_required_not_unique():
    e_rows = [
        {"status": "a", "emp_no": "E1", "cnt": 1},
        {"status": "a", "emp_no": "E2", "cnt": 1},
    ]
    cols = pick_sort_columns(
        ["status", "cnt"],
        expect_rows=e_rows,
        ask_rows=e_rows,
        expect_cols=["status", "emp_no", "cnt"],
        ask_cols=["status", "emp_no", "cnt"],
    )
    assert cols == ["emp_no"]


def test_pick_sort_two_lowest_dup_when_no_unique():
    e_rows = [
        {"a": "x", "b": "1", "c": "p"},
        {"a": "x", "b": "2", "c": "p"},
        {"a": "y", "b": "1", "c": "q"},
        {"a": "y", "b": "2", "c": "q"},
    ]
    cols = pick_sort_columns(
        ["a", "b", "c"],
        expect_rows=e_rows,
        ask_rows=e_rows,
        expect_cols=["a", "b", "c"],
        ask_cols=["a", "b", "c"],
    )
    assert len(cols) == 2
