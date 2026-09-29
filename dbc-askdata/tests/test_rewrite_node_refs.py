from dbc_askdata.workflow.runner import rewrite_node_refs


def test_rewrite_node_refs_placeholder_and_bare():
    outputs = {"n1": "public.askdata_tmp_8_n1", "n2": "public.askdata_tmp_8_n2"}
    sql = "SELECT a.* FROM __node_n1__ a JOIN n2 b ON a.id = b.id"
    out = rewrite_node_refs(sql, outputs)
    assert "public.askdata_tmp_8_n1" in out
    assert "public.askdata_tmp_8_n2" in out
    assert "FROM n2" not in out
    assert "__node_n1__" not in out


def test_rewrite_ignores_unknown_table():
    sql = "SELECT * FROM company.hr_employee e"
    assert rewrite_node_refs(sql, {"n1": "public.askdata_tmp_1_n1"}) == sql
