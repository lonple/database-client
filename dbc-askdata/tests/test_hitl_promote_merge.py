from dbc_askdata.knowledge.hitl_card import build_hitl_card_fields, normalize_surface
from dbc_askdata.knowledge.hitl_promote import (
    merge_field_dict_into_metadata_body,
    merge_intent_mapping_body,
)
from dbc_askdata.db.models import AskHitl


def test_normalize_surface() -> None:
    assert normalize_surface("  在职 员工 ") == "在职 员工"
    assert normalize_surface("ABC") == "abc"


def test_merge_intent_append_and_count() -> None:
    body, action = merge_intent_mapping_body("", surface="请假", table="hr.leave_req")
    assert action == "appended"
    assert "`请假` → `hr.leave_req`" in body

    body2, action2 = merge_intent_mapping_body(body, surface="请假", table="hr.leave_req")
    assert action2 == "merged"
    assert "(x2)" in body2


def test_merge_intent_conflict() -> None:
    body, _ = merge_intent_mapping_body("", surface="订单", table="ord_header")
    body2, action = merge_intent_mapping_body(body, surface="订单", table="ord_order")
    assert action == "conflict"
    assert "CONFLICT" in body2
    assert "`ord_header`" in body2
    assert "`ord_order`" in body2


def test_merge_field_dict_under_table_section() -> None:
    src = """# 数据库结构

## demo.public.emp

### 列

- `status` varchar

## demo.public.dept

### 列

- `id` int
"""
    body, action = merge_field_dict_into_metadata_body(
        src,
        table="emp",
        column="status",
        surface="在职",
        code="1",
        database="demo",
        schema="public",
    )
    assert action == "appended"
    assert "人工确认·字段字典" in body
    assert "`status`: `在职` → `1`" in body
    # 仍保留后续表章节
    assert "## demo.public.dept" in body

    body2, action2 = merge_field_dict_into_metadata_body(
        body,
        table="emp",
        column="status",
        surface="在职",
        code="1",
        database="demo",
        schema="public",
    )
    assert action2 == "merged"
    assert "(x2)" in body2


def test_merge_field_dict_conflict() -> None:
    src = "## demo.emp\n\n### 人工确认·字段字典\n\n- `status`: `在职` → `1`\n"
    body, action = merge_field_dict_into_metadata_body(
        src,
        table="emp",
        column="status",
        surface="在职",
        code="ACTIVE",
        database="demo",
        schema=None,
    )
    assert action == "conflict"
    assert "CONFLICT" in body


def test_build_hitl_card_fields_table() -> None:
    hitl = AskHitl(
        id=1,
        session_id=9,
        question="请确认表",
        status="RESOLVED",
        options={"question": "查一下请假单", "ui": {"kind": "TABLE"}},
    )
    fields = build_hitl_card_fields(
        hitl=hitl,
        resolution={"table": "leave_req", "kind": "TABLE"},
        connection_id=3,
        database="demo",
        schema="public",
        project_id=1,
        owner_user_id=7,
    )
    assert fields["kind"] == "TABLE"
    assert fields["target_table"] == "leave_req"
    assert fields["status"] == "PENDING"
    assert "请假" in fields["surface"]
