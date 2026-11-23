from dbc_askdata.workflow.runner import (
    draft_as_single_query,
    expand_node_refs_for_explain,
    flatten_draft_to_inline_sql,
    rewrite_node_refs,
)


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


def test_expand_node_refs_for_explain_placeholder_with_alias():
    upstream = {"n1": "SELECT id, customer_id FROM company.sal_sales_order"}
    sql = "SELECT customer_id, SUM(1) AS amt FROM __node_n1__ t GROUP BY customer_id"
    out = expand_node_refs_for_explain(sql, upstream)
    assert "FROM (SELECT id, customer_id FROM company.sal_sales_order) t" in out
    assert "__node_n1__" not in out


def test_expand_node_refs_for_explain_bare_n1_keeps_where():
    upstream = {"n1": "SELECT id FROM company.sal_sales_order"}
    sql = "SELECT * FROM n1 WHERE id > 0"
    out = expand_node_refs_for_explain(sql, upstream)
    assert "FROM (SELECT id FROM company.sal_sales_order) AS n1 WHERE id > 0" in out


def test_expand_node_refs_for_explain_nested_uses_expanded_upstream():
    expanded_n1 = "SELECT id FROM company.sal_sales_order"
    expanded_n2 = expand_node_refs_for_explain(
        "SELECT * FROM __node_n1__",
        {"n1": expanded_n1},
    )
    out = expand_node_refs_for_explain(
        "SELECT * FROM n2 WHERE id = 1",
        {"n1": expanded_n1, "n2": expanded_n2},
    )
    assert "sal_sales_order" in out
    assert "__node_n1__" not in out
    assert "FROM n2" not in out


def test_flatten_draft_to_inline_sql_eval_shape():
    draft = {
        "name": "各客户有效订单额",
        "nodes": [
            {
                "id": "n1",
                "type": "GOVERN",
                "sql": "SELECT id, customer_id FROM company.sal_sales_order WHERE status = 'SIGNED'",
            },
            {
                "id": "n2",
                "type": "QUERY",
                "sql": "SELECT customer_id, COUNT(*) AS cnt FROM __node_n1__ GROUP BY customer_id",
            },
        ],
    }
    flat = flatten_draft_to_inline_sql(draft)
    assert flat is not None
    assert "__node_n1__" not in flat
    assert "sal_sales_order" in flat
    assert "GROUP BY" in flat.upper()
    single = draft_as_single_query(draft)
    assert single is not None
    assert len(single["nodes"]) == 1
    assert single["nodes"][0]["type"] == "QUERY"
    assert single["nodes"][0]["sql"] == flat
