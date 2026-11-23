from dbc_askdata.graph.hitl_prompt import hitl_for_sql_prompt, physical_table_name


def test_physical_table_name_accepts_ident() -> None:
    assert physical_table_name("prd_product") == "prd_product"
    assert physical_table_name("company.prd_product") == "company.prd_product"


def test_physical_table_name_rejects_code_value() -> None:
    assert physical_table_name("DBC 智能问数") is None
    assert physical_table_name("智能问数") is None
    assert physical_table_name("") is None


def test_hitl_prompt_keeps_code_as_text_not_table() -> None:
    payload = hitl_for_sql_prompt({"ack": True, "text": "DBC 智能问数", "table": "DBC 智能问数"})
    assert payload is not None
    assert payload["text"] == "DBC 智能问数"
    assert "confirmed_table" not in payload
