from dbc_askdata.knowledge.table_intent import parse_table_intent_pairs, parse_table_intents


def test_parse_table_intents_json() -> None:
    assert parse_table_intents(
        '{"entities":[{"entity":"订单主表","english":"order"},{"entity":"客户","english":"customer"}]}'
    ) == ["订单主表", "客户"]


def test_parse_table_intents_fenced() -> None:
    raw = """```json
{"entities":[{"entity":"员工花名册","english":"employee"}]}
```"""
    assert parse_table_intents(raw) == ["员工花名册"]


def test_parse_pairs_aligned() -> None:
    pairs = parse_table_intent_pairs(
        '{"entities":[{"entity":"加班","english":"overtime"},{"entity":"部门","english":"department"}]}'
    )
    assert len(pairs) == 2
    assert pairs[0]["entity"] == "加班"
    assert pairs[0]["english"] == "overtime"
    assert pairs[0]["role"] == "table"


def test_parse_pairs_role_filter_default_table() -> None:
    pairs = parse_table_intent_pairs(
        '{"entities":['
        '{"entity":"订单主表","english":"order","role":"table"},'
        '{"entity":"金额","english":"amount","role":"attr"},'
        '{"entity":"2024-01-01","english":"","role":"filter"}'
        "]}"
    )
    assert [p["role"] for p in pairs] == ["table", "attr", "filter"]
