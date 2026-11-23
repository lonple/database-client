from dbc_askdata.graph.sql_review import parse_review_verdict


def test_review_pass():
    v = parse_review_verdict('{"ok":true,"action":"pass","critique":"覆盖完整"}')
    assert v.ok
    assert v.action == "pass"


def test_review_regen_dropped_filter():
    v = parse_review_verdict(
        '{"ok":false,"action":"regen","critique":"问句提到产品，SQL 未过滤"}'
    )
    assert not v.ok
    assert v.action == "regen"
    assert "产品" in v.critique


def test_review_hitl():
    v = parse_review_verdict(
        '{"ok":false,"action":"hitl","critique":"多个产品候选",'
        '"hitl_question":"请确认完整产品名"}'
    )
    assert v.action == "hitl"
    assert v.hitl_question == "请确认完整产品名"


def test_review_invalid_json_fail_closed_hitl():
    v = parse_review_verdict("not json")
    assert not v.ok
    assert v.action == "hitl"


def test_review_ok_false_defaults_regen():
    v = parse_review_verdict('{"ok":false,"critique":"漏条件"}')
    assert v.action == "regen"
