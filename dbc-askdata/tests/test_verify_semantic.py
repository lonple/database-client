from dbc_askdata.verify.semantic import (
    check_eq_literals_against_profiles,
    check_eq_projection,
    ensure_eq_projection_in_select,
    ensure_group_by_cols_in_select,
    is_detail_select,
    outer_eq_predicates,
    select_output_columns,
)


def test_is_detail_select_plain():
    assert is_detail_select("SELECT id, name FROM t WHERE status = 'a'")
    assert not is_detail_select("SELECT COUNT(*) FROM t WHERE status = 'a'")
    assert not is_detail_select("SELECT dept_id, COUNT(*) FROM t GROUP BY dept_id")


def test_outer_eq_predicates_skips_range():
    sql = (
        "SELECT id FROM hr_employee e "
        "WHERE e.status = 'active' AND e.age > 30 AND e.name LIKE '%张%'"
    )
    preds = outer_eq_predicates(sql)
    cols = {p.column.lower() for p in preds}
    assert "status" in cols
    assert "age" not in cols
    assert "name" not in cols


def test_outer_eq_predicates_includes_neq_and_not_in():
    sql = (
        "SELECT id, status, dept_id FROM hr_employee e "
        "WHERE e.status != 'LEFT' AND e.dept_id NOT IN (1, 2)"
    )
    preds = outer_eq_predicates(sql)
    by_col = {p.column.lower(): p.op for p in preds}
    assert by_col.get("status") == "!="
    assert by_col.get("dept_id") == "not_in"


def test_eq_projection_missing():
    sql = "SELECT id, name FROM hr_employee WHERE status = 'active'"
    issue = check_eq_projection(sql)
    assert issue is not None
    assert "status" in issue.missing_eq_cols


def test_eq_projection_ok():
    sql = "SELECT id, name, status FROM hr_employee WHERE status = 'active'"
    assert check_eq_projection(sql) is None


def test_ensure_eq_projection_adds_bare_col():
    sql = "SELECT id, name FROM hr_employee WHERE status = 'active'"
    fixed, added = ensure_eq_projection_in_select(sql)
    assert "status" in {a.lower() for a in added}
    assert check_eq_projection(fixed) is None
    assert "status" in fixed.lower()


def test_ensure_eq_projection_adds_qualified_col():
    sql = (
        "SELECT t1.customer_code, t1.customer_name "
        "FROM company.crm_customer AS t1 "
        "INNER JOIN company.sal_sales_order AS t2 ON t1.id = t2.customer_id "
        "WHERE t2.order_no = 'SO1'"
    )
    fixed, added = ensure_eq_projection_in_select(sql)
    assert any("order_no" in a.lower() for a in added)
    assert check_eq_projection(fixed) is None
    assert "order_no" in fixed.lower()


def test_ensure_eq_projection_noop_when_ok():
    sql = "SELECT id, status FROM hr_employee WHERE status = 'active'"
    fixed, added = ensure_eq_projection_in_select(sql)
    assert added == []
    assert fixed == sql or check_eq_projection(fixed) is None


def test_ensure_group_by_cols_adds_simple_cols():
    sql = "SELECT COUNT(*) AS cnt FROM hr_employee GROUP BY dept_id, status"
    fixed, added = ensure_group_by_cols_in_select(sql)
    assert {"dept_id", "status"} <= {a.lower() for a in added}
    out = select_output_columns(fixed)
    assert out is not None
    assert "dept_id" in out and "status" in out
    assert "count" in fixed.lower() or "cnt" in fixed.lower()


def test_ensure_group_by_cols_qualified():
    sql = (
        "SELECT COUNT(*) AS cnt FROM company.hr_employee AS e "
        "GROUP BY e.dept_id"
    )
    fixed, added = ensure_group_by_cols_in_select(sql)
    assert any("dept_id" in a.lower() for a in added)
    assert "dept_id" in fixed.lower()


def test_ensure_group_by_skips_expression():
    sql = (
        "SELECT COUNT(*) AS cnt FROM hr_employee "
        "GROUP BY date_trunc('month', hire_date)"
    )
    fixed, added = ensure_group_by_cols_in_select(sql)
    assert added == []
    assert fixed == sql or "date_trunc" in fixed.lower()


def test_ensure_group_by_noop_when_already_selected():
    sql = "SELECT dept_id, COUNT(*) AS cnt FROM hr_employee GROUP BY dept_id"
    fixed, added = ensure_group_by_cols_in_select(sql)
    assert added == []


def test_eq_projection_star_ok():
    sql = "SELECT * FROM hr_employee WHERE status = 'active'"
    assert check_eq_projection(sql) is None


def test_eq_projection_skip_aggregate():
    sql = "SELECT dept_id, COUNT(*) AS c FROM hr_employee WHERE status = 'active' GROUP BY dept_id"
    assert check_eq_projection(sql) is None


def test_select_output_columns_alias():
    cols = select_output_columns("SELECT e.status AS st, e.id FROM hr_employee e")
    assert cols is not None
    assert "st" in cols
    assert "status" in cols
    assert "id" in cols


def test_verify_need_profile_when_missing():
    sql = "SELECT id, status FROM hr_employee WHERE status = '在职'"
    issue = check_eq_literals_against_profiles(sql, {})
    assert issue is not None
    assert issue.code == "EQ_LITERAL_NEED_PROFILE"
    assert any(i.get("column", "").lower() == "status" for i in issue.need_profile)


def test_verify_mismatch_zh_on_code_column():
    """中文条件打在码值列上 → 格式不匹配，应打回。"""
    sql = "SELECT id, status FROM hr_employee WHERE status = '在职'"
    profiles = {
        "hr_employee.status": {
            "enum_like": True,
            "value_counts": [{"value": "ACTIVE", "count": 10}, {"value": "LEFT", "count": 2}],
        }
    }
    issue = check_eq_literals_against_profiles(sql, profiles)
    assert issue is not None
    assert issue.code == "EQ_LITERAL_MISMATCH"


def test_verify_pass_zh_on_zh_column_even_if_not_in_topn():
    """格式同类即放行；字面量不必出现在 value_counts。"""
    sql = "SELECT id, dept_name FROM org_department WHERE dept_name = '平台研发部'"
    profiles = {
        "org_department.dept_name": {
            "enum_like": True,
            "value_counts": [
                {"value": "产品部", "count": 3},
                {"value": "财务部", "count": 2},
            ],
        }
    }
    assert check_eq_literals_against_profiles(sql, profiles) is None


def test_verify_use_key_sync_flags_mismatch_until_rewrite():
    """同步检查仍报不匹配；异步探测路径会代码改写为 key。"""
    sql = "SELECT id, status FROM hr_employee WHERE status = '在职'"
    profiles = {
        "hr_employee.status": {
            "action": "use_key",
            "key": "1",
            "dictionary": True,
            "value_counts": [{"value": "1", "count": 10}],
        }
    }
    issue = check_eq_literals_against_profiles(sql, profiles)
    assert issue is not None
    assert issue.code == "EQ_LITERAL_MISMATCH"

    sql_ok = "SELECT id, status FROM hr_employee WHERE status = '1'"
    assert check_eq_literals_against_profiles(sql_ok, profiles) is None
