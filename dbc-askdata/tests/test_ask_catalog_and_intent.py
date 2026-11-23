from __future__ import annotations

from dbc_askdata.knowledge.ask_catalog_search import (
    _hit_score,
    build_table_search_queries,
    catalog_search_pairs,
    split_catalog_roles,
)
from dbc_askdata.knowledge.table_intent import (
    normalize_entity_role,
    parse_table_intent_pair,
    parse_table_intent_pairs,
    parse_table_intent_payload,
    parse_table_intents,
)


def test_parse_intent_pairs_many() -> None:
    raw = (
        '{"entities":[{"entity":"加班","english":"overtime"},'
        '{"entity":"报销","english":"reimburse"}]}'
    )
    pairs = parse_table_intent_pairs(raw)
    assert pairs == [
        {"entity": "加班", "english": "overtime", "role": "table"},
        {"entity": "报销", "english": "reimburse", "role": "table"},
    ]


def test_parse_intent_pairs_with_roles() -> None:
    raw = (
        '{"entities":['
        '{"entity":"发布部署记录","english":"deploy","role":"table"},'
        '{"entity":"版本号","english":"version","role":"attr"},'
        '{"entity":"dep-00001","english":"","role":"filter"}'
        "]}"
    )
    pairs = parse_table_intent_pairs(raw)
    assert [p["role"] for p in pairs] == ["table", "attr", "filter"]
    assert pairs[0]["entity"] == "发布部署记录"
    assert pairs[2]["entity"] == "dep-00001"


def test_parse_intent_pair_compat_first() -> None:
    zh, en = parse_table_intent_pair('{"entity":"员工","english":""}')
    assert zh == "员工"
    assert en == ""


def test_parse_intent_legacy_arrays_zip() -> None:
    pairs = parse_table_intent_pairs(
        '{"tables":["订单主表","客户"],"englishHints":["order","customer"]}'
    )
    assert pairs[0] == {"entity": "订单主表", "english": "order", "role": "table"}
    assert pairs[1] == {"entity": "客户", "english": "customer", "role": "table"}


def test_parse_table_intent_payload_compat() -> None:
    zh, en = parse_table_intent_payload(
        '{"entities":[{"entity":"订单主表","english":"order"}]}'
    )
    assert zh == ["订单主表"]
    assert en == ["order"]


def test_parse_table_intents_compat() -> None:
    assert parse_table_intents(
        '{"entities":[{"entity":"订单主表","english":"order"},{"entity":"客户","english":"customer"}]}'
    ) == ["订单主表", "客户"]


def test_normalize_entity_role() -> None:
    assert normalize_entity_role(None) == "table"
    assert normalize_entity_role("") == "table"
    assert normalize_entity_role("ATTR") == "attr"
    assert normalize_entity_role("value") == "filter"
    assert normalize_entity_role("anchor") == "table"


def test_catalog_search_pairs_skips_filter() -> None:
    pairs = [
        {"entity": "发布部署记录", "english": "deploy", "role": "table"},
        {"entity": "版本号", "english": "version", "role": "attr"},
        {"entity": "dep-00001", "english": "", "role": "filter"},
    ]
    search = catalog_search_pairs(pairs)
    assert [p["role"] for p in search] == ["table", "attr"]
    assert all(p["entity"] != "dep-00001" for p in search)


def test_split_catalog_roles() -> None:
    tables, attrs = split_catalog_roles(
        [
            {"entity": "发布部署记录", "english": "deploy", "role": "table"},
            {"entity": "版本号", "english": "version", "role": "attr"},
            {"entity": "状态", "english": "status", "role": "attr"},
            {"entity": "dep-00001", "english": "", "role": "filter"},
        ]
    )
    assert len(tables) == 1
    assert tables[0]["entity"] == "发布部署记录"
    assert [a["entity"] for a in attrs] == ["版本号", "状态"]


def test_build_table_search_queries_mapping() -> None:
    q = build_table_search_queries(
        [{"entity": "员工", "english": "hr_employee", "role": "table"}],
        [
            {"entity": "状态", "english": "status", "role": "attr"},
            {"entity": "工号", "english": "emp_no", "role": "attr"},
        ],
    )
    assert q["titleQuery"] == "hr_employee"
    assert q["descriptionQuery"] == "员工"
    assert q["bodySummaryQuery"] == "status 状态 | emp_no 工号"
    assert q["ftsQuery"] == "hr_employee 员工|status 状态 | emp_no 工号"


def test_catalog_search_pairs_attr_only_kept() -> None:
    """无 table 时仍保留 attr，供仅正文 fts 回退。"""
    search = catalog_search_pairs(
        [{"entity": "版本号", "english": "version", "role": "attr"}]
    )
    assert len(search) == 1
    assert search[0]["role"] == "attr"
    tables, attrs = split_catalog_roles(search)
    assert tables == []
    assert len(attrs) == 1


def test_hit_score() -> None:
    assert _hit_score({"score": 0.8}) == 0.8
    assert _hit_score({"rerankScore": 1.2}) == 1.2
    assert _hit_score({}) == 0.0
