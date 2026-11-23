from dbc_askdata.verify.condition_match import (
    cosine,
    fk_targets,
    format_decision,
    match_dictionary,
    match_dictionary_cosine,
    mismatch_action,
    normalize_dictionary_pairs,
)


def test_normalize_dictionary_pairs_from_model() -> None:
    assert normalize_dictionary_pairs(
        [
            {"key": "planning", "value": "规划中"},
            {"key": "active", "value": "进行中"},
        ]
    ) == [("planning", "规划中"), ("active", "进行中")]
    assert normalize_dictionary_pairs("planning=规划中;active=进行中") == [
        ("planning", "规划中"),
        ("active", "进行中"),
    ]
    # 原文说明不再由代码拆
    assert (
        normalize_dictionary_pairs(
            "项目状态：`planning`=规划中、`active`=进行中、`closed`=已结项、`warranty`=质保中"
        )
        == []
    )


def test_match_dictionary_exact_then_cosine() -> None:
    pairs = [("1", "在职"), ("0", "离职")]
    assert match_dictionary("在职", pairs)["key"] == "1"
    pending = match_dictionary("在岗", pairs)
    assert pending["action"] == "need_similarity"
    hit = match_dictionary_cosine(
        pairs,
        [1.0, 0.0],
        [[0.9, 0.1], [0.0, 1.0]],
        threshold=0.75,
    )
    assert hit["action"] == "use_key"
    assert hit["key"] == "1"
    missed = match_dictionary_cosine(
        pairs,
        [0.0, 1.0],
        [[1.0, 0.0], [0.2, 0.1]],
        threshold=0.75,
    )
    assert missed["action"] == "hitl"
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_format_zh_matches_without_membership() -> None:
    decision = format_decision("财务部", ["研发部", "财务部", "A01"])
    assert decision["action"] == "use_literal"
    decision2 = format_decision("DEP-9", ["研发部", "财务部"])
    assert decision2["action"] == "format_mismatch"


def test_fk_targets_and_hop_cap() -> None:
    relations = [
        {
            "edges": [
                {
                    "fromTable": "hr_employee",
                    "fromColumn": "dept_id",
                    "toTable": "dept",
                    "toColumn": "id",
                }
            ]
        }
    ]
    targets = fk_targets("hr_employee", "dept_id", relations)
    assert targets == [{"table": "dept", "column": "id"}]
    followed = mismatch_action(hop=0, targets=targets, column_format_name="code", condition_format_name="zh")
    assert followed["action"] == "follow_fk"
    assert followed["nextHop"] == 1
    capped = mismatch_action(hop=3, targets=targets, column_format_name="code", condition_format_name="zh")
    assert capped["action"] == "hitl"
    same = mismatch_action(hop=0, targets=[], column_format_name="code", condition_format_name="zh")
    assert same["action"] == "retry_same_table"
