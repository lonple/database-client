from dbc_askdata.graph.hitl_ui import hitl_ui_for_state, infer_hitl_kind


def test_column_question_not_table_ui() -> None:
    state = {
        "interrupted_node": "fine_router",
        "hitl_question": (
            "请确认 `hr_employee` 表中用于判断在职状态的离职时间字段名是什么？"
            " (例如 `leave_date`, `termination_date` 等)"
        ),
        "catalog": {"items": [{"name": "hr_employee"}, {"name": "crm_customer"}]},
        "described_columns": {
            "company.hr_employee": ["id", "leave_date", "status", "name"],
        },
    }
    assert infer_hitl_kind(state) == "COLUMN"
    ui = hitl_ui_for_state(state)
    assert ui["kind"] == "COLUMN"
    assert ui["fields"][0]["key"] == "column"
    assert "leave_date" in (ui["fields"][0].get("candidates") or [])
    assert ui["title"] == "请确认字段名"


def test_table_question_stays_table_ui() -> None:
    state = {
        "interrupted_node": "fine_router",
        "hitl_question": "请确认查询表名（物理表）。",
        "catalog": {"items": [{"name": "hr_employee"}]},
    }
    assert infer_hitl_kind(state) == "TABLE"
    ui = hitl_ui_for_state(state)
    assert ui["kind"] == "TABLE"
    assert ui["fields"][0]["key"] == "table"


def test_explicit_hitl_kind_wins() -> None:
    state = {
        "hitl_kind": "EQ_LITERAL",
        "hitl_question": "请确认表名",  # 故意带「表」干扰
    }
    assert infer_hitl_kind(state) == "EQ_LITERAL"
    assert hitl_ui_for_state(state)["kind"] == "EQ_LITERAL"


def test_multi_question_open_clarification_is_scope() -> None:
    """多个是否/方案问题不得收成「请确认字段名」。"""
    state = {
        "interrupted_node": "fine_router",
        "hitl_question": (
            "请确认：1. 是否需要直接在SQL中通过 "
            "`CASE WHEN leave_date IS NULL THEN '在职' ELSE '已离职' END` "
            "来生成明确的在职结论？\n"
            "2. `employment_status` 字段的具体含义是否足以回答「人事状态」，"
            "还是需要关联其他字典表获取更详细的描述？"
        ),
        "catalog": {"items": [{"name": "hr_employee"}]},
        "described_columns": {
            "company.hr_employee": [
                "id",
                "leave_date",
                "employment_status",
                "name",
            ],
        },
    }
    assert infer_hitl_kind(state) == "SCOPE"
    ui = hitl_ui_for_state(state)
    assert ui["kind"] == "SCOPE"
    assert ui["fields"][0]["key"] == "text"
    assert ui["title"] == "请确认查询口径"


def test_whether_question_is_scope_not_column() -> None:
    state = {
        "interrupted_node": "fine_router",
        "hitl_question": "是否用 leave_date IS NULL 表示在职？",
        "described_columns": {"t": ["leave_date", "status"]},
    }
    assert infer_hitl_kind(state) == "SCOPE"
    assert hitl_ui_for_state(state)["kind"] == "SCOPE"
