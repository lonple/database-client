from dbc_askdata.eval.table_select import (
    judge_table_select,
    resolve_ask_sql_for_tables,
    table_names_from_sql,
)


def test_table_names_ignore_schema() -> None:
    assert table_names_from_sql(
        "SELECT a.status, a.amount FROM company.fin_receipt a WHERE a.receipt_no = 'RCP000001'"
    ) == ["fin_receipt"]


def test_skip_hitl_no_supplement() -> None:
    j = judge_table_select(
        expect_sql="SELECT 1 FROM company.fin_receipt",
        ask_sql="SELECT 1 FROM company.hr_employee",
        govern_subtype="HITL_NO_SUPPLEMENT",
    )
    assert j["scored"] is False
    assert j["reason"] == "hitl_no_supplement"
    assert j["ok"] is None


def test_skip_empty_or_refuse_mode() -> None:
    j = judge_table_select(
        expect_sql=None,
        ask_sql=None,
        compare_mode="empty_or_refuse",
    )
    assert j["scored"] is False
    assert j["reason"] == "empty_or_refuse"


def test_match_ok() -> None:
    j = judge_table_select(
        expect_sql="SELECT receipt_no, status, amount FROM company.fin_receipt WHERE receipt_no = 'RCP000001'",
        ask_sql="SELECT status, amount FROM company.fin_receipt WHERE receipt_no = 'RCP000001'",
    )
    assert j["scored"] is True
    assert j["ok"] is True
    assert j["expectTables"] == ["fin_receipt"]
    assert j["askTables"] == ["fin_receipt"]


def test_match_fail_extra_missing() -> None:
    j = judge_table_select(
        expect_sql="SELECT * FROM company.fin_receipt r JOIN company.crm_customer c ON c.id = r.customer_id",
        ask_sql="SELECT * FROM company.fin_receipt",
    )
    assert j["scored"] is True
    assert j["ok"] is False
    assert j["missing"] == ["crm_customer"]
    assert j["extra"] == []


def test_multi_node_expand_placeholders() -> None:
    draft = {
        "name": "demo",
        "nodes": [
            {
                "id": "n1",
                "type": "QUERY",
                "sql": "SELECT id, customer_id FROM company.fin_receipt WHERE receipt_no = 'RCP000001'",
            },
            {
                "id": "n2",
                "type": "QUERY",
                "sql": "SELECT c.customer_name FROM __node_n1__ r JOIN company.crm_customer c ON c.id = r.customer_id",
            },
        ],
    }
    flat = resolve_ask_sql_for_tables(draft=draft)
    assert flat is not None
    assert "__node_" not in flat.lower()
    names = table_names_from_sql(flat)
    assert set(names) == {"fin_receipt", "crm_customer"}

    j = judge_table_select(
        expect_sql=(
            "SELECT c.customer_name FROM company.fin_receipt r "
            "JOIN company.crm_customer c ON c.id = r.customer_id "
            "WHERE r.receipt_no = 'RCP000001'"
        ),
        draft=draft,
    )
    assert j["scored"] is True
    assert j["ok"] is True
    assert set(j["askTables"]) == {"fin_receipt", "crm_customer"}
