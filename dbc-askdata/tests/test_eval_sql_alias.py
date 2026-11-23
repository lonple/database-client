from dbc_askdata.eval.sql_alias import (
    normalize_count_aliases_in_sql,
    rewrite_required_columns_by_sql,
    rewrite_result_columns_by_sql,
    select_alias_to_source,
)


def test_alias_map_column_as():
    m = select_alias_to_source("SELECT e.dept_name AS dn, e.id FROM company.org_department e")
    assert m["dn"] == "dept_name"
    assert m["id"] == "id"


def test_alias_map_cast_column():
    m = select_alias_to_source("SELECT cast(id AS text) AS id_txt, dept_name FROM t")
    assert m["id_txt"] == "id"
    assert m["dept_name"] == "dept_name"


def test_alias_map_count_to_cnt():
    m = select_alias_to_source("SELECT count(*)::bigint AS total, dept_id FROM t GROUP BY dept_id")
    assert m["total"] == "cnt"
    assert m["dept_id"] == "dept_id"

    m2 = select_alias_to_source("SELECT count(id) AS c FROM t")
    assert m2["c"] == "cnt"

    m3 = select_alias_to_source("SELECT count(*) AS cnt FROM t")
    assert m3["cnt"] == "cnt"


def test_rewrite_count_alias_to_cnt():
    result = {"columns": [{"name": "total"}], "rows": [[42]], "rowCount": 1}
    out, notes = rewrite_result_columns_by_sql(result, "SELECT count(*) AS total FROM hr_employee")
    assert notes == ["total->cnt"]
    assert out["columns"][0]["name"] == "cnt"


def test_normalize_count_aliases_in_sql():
    out = normalize_count_aliases_in_sql(
        "SELECT d.dept_name, count(*)::bigint AS total "
        "FROM t e JOIN d ON e.dept_id = d.id GROUP BY d.dept_name ORDER BY total DESC"
    )
    low = " ".join(out.lower().split())
    assert "as cnt" in low
    assert "as total" not in low
    assert "order by cnt" in low


def test_alias_map_sum_to_source_column():
    m = select_alias_to_source(
        "SELECT d.dept_name, SUM(r.total_amount) AS total_reimbursed "
        "FROM t r JOIN d ON r.dept_id = d.id GROUP BY d.dept_name"
    )
    assert m["total_reimbursed"] == "total_amount"
    assert m["dept_name"] == "dept_name"

    m2 = select_alias_to_source(
        "SELECT coalesce(sum(r.total_amount),0) AS amt, dept_name FROM t GROUP BY dept_name"
    )
    assert m2["amt"] == "total_amount"


def test_rewrite_sum_alias_and_required_to_source():
    expect_sql = (
        "SELECT d.dept_name, coalesce(sum(r.total_amount),0) AS amt "
        "FROM company.fin_reimburse r JOIN company.org_department d ON d.id = r.dept_id "
        "GROUP BY d.dept_name"
    )
    ask_sql = (
        "SELECT d.dept_name, SUM(r.total_amount) AS total_reimbursed "
        "FROM company.fin_reimburse AS r JOIN company.org_department AS d "
        "ON r.dept_id = d.id GROUP BY d.dept_name"
    )
    ask_result = {
        "columns": [{"name": "dept_name"}, {"name": "total_reimbursed"}],
        "rows": [["销售部", 1]],
        "rowCount": 1,
    }
    expect_result = {
        "columns": [{"name": "dept_name"}, {"name": "amt"}],
        "rows": [["销售部", 1]],
        "rowCount": 1,
    }
    ask_out, ask_notes = rewrite_result_columns_by_sql(ask_result, ask_sql)
    expect_out, expect_notes = rewrite_result_columns_by_sql(expect_result, expect_sql)
    assert "total_reimbursed->total_amount" in ask_notes
    assert "amt->total_amount" in expect_notes
    assert [c["name"] for c in ask_out["columns"]] == ["dept_name", "total_amount"]
    assert [c["name"] for c in expect_out["columns"]] == ["dept_name", "total_amount"]

    spec = {"columns": ["dept_name", "amt"]}
    spec2, n2 = rewrite_required_columns_by_sql(spec, expect_sql)
    assert "amt->total_amount" in n2
    assert spec2["columns"] == ["dept_name", "total_amount"]


def test_rewrite_result_columns():
    result = {
        "columns": [{"name": "dn"}, {"name": "amt"}],
        "rows": [["销售部", 1]],
        "rowCount": 1,
    }
    out, notes = rewrite_result_columns_by_sql(
        result,
        "SELECT dept_name AS dn, amt FROM t",
    )
    assert notes == ["dn->dept_name"]
    assert out is not None
    assert out["columns"][0]["name"] == "dept_name"
    assert out["columns"][1]["name"] == "amt"
    assert out["rows"] == [["销售部", 1]]


def test_rewrite_required_columns_same_as_result():
    sql = "SELECT dept_name AS dn, count(*)::bigint AS total FROM t GROUP BY dept_name"
    spec = {"requiredColumns": ["dn", "total", "dept_name"]}
    out, notes = rewrite_required_columns_by_sql(spec, sql)
    assert notes == ["dn->dept_name", "total->cnt"]
    assert out["requiredColumns"] == ["dept_name", "cnt"]
    assert spec["requiredColumns"] == ["dn", "total", "dept_name"]


def test_rewrite_required_columns_unchanged_when_already_source():
    spec = {"columns": ["dept_name", "id"]}
    out, notes = rewrite_required_columns_by_sql(
        spec, "SELECT dept_name, id FROM t"
    )
    assert notes == []
    assert out is spec


def test_rewrite_multi_statement_uses_last_select():
    sql = "CREATE TEMP TABLE x AS SELECT 1; SELECT emp_no AS eno FROM hr_employee"
    result = {"columns": [{"name": "eno"}], "rows": [["E1"]], "rowCount": 1}
    out, notes = rewrite_result_columns_by_sql(result, sql)
    assert notes == ["eno->emp_no"]
    assert out["columns"][0]["name"] == "emp_no"
