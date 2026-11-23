from dbc_askdata.context.session_context import (
    build_session_prefix_messages,
    user_questions_from_turns,
)


def test_user_questions_from_turns() -> None:
    turns = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "您好"},
        {"role": "user", "content": "平台研发部有哪些员工？"},
    ]
    assert user_questions_from_turns(turns) == ["你好", "平台研发部有哪些员工？"]


def test_chat_prefix_keeps_dialogue() -> None:
    prefix = build_session_prefix_messages(
        route="CHAT",
        recent_turns=[
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "您好，有什么可以帮您"},
        ],
        verified_samples=None,
    )
    assert len(prefix) == 1
    assert "近窗对话" in prefix[0]["content"]
    assert "assistant" in prefix[0]["content"]


def test_query_prefix_questions_and_useful_tables_only() -> None:
    prefix = build_session_prefix_messages(
        route="QUERY",
        recent_turns=[
            {"role": "user", "content": "各部门人数？"},
            {"role": "assistant", "content": "已生成 SQL"},
            {"role": "user", "content": "平台研发部有哪些员工？"},
        ],
        verified_samples=[
            {
                "question": "各部门人数？",
                "tables": ["company.hr_employee", "company.org_department"],
            }
        ],
    )
    assert len(prefix) == 2
    assert "近窗用户问句" in prefix[0]["content"]
    assert "各部门人数？" in prefix[0]["content"]
    assert "平台研发部有哪些员工？" in prefix[0]["content"]
    # assistant 原文不进 QUERY 近窗
    assert "已生成 SQL" not in prefix[0]["content"]
    assert "已确认有用" in prefix[1]["content"]
    assert "hr_employee" in prefix[1]["content"]


def test_query_prefix_without_useful_has_questions_only() -> None:
    prefix = build_session_prefix_messages(
        route="GOVERN",
        recent_turns=[{"role": "user", "content": "统计一下请假"}],
        verified_samples=[],
    )
    assert len(prefix) == 1
    assert "近窗用户问句" in prefix[0]["content"]
    assert "请假" in prefix[0]["content"]


def test_followup_questions_available_for_gate() -> None:
    """门闩用：近窗问句可还原『朱婷杰呢』承接『请假几天』。"""
    turns = [
        {"role": "user", "content": "他今年请了几天假？"},
        {"role": "assistant", "content": "已生成草稿"},
        {"role": "user", "content": "朱婷杰呢？"},
    ]
    # routes 会在进图前去掉本轮 user，门闩侧看到的是此前问句
    prior = turns[:-1]
    qs = user_questions_from_turns(prior)
    assert qs == ["他今年请了几天假？"]
