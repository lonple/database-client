"""校验侧：按 SQL 条件值探测画像并判定放行/打回。"""

import pytest

from dbc_askdata.verify.condition_match import accept_sql_literal
from dbc_askdata.verify.repair import _check_eq_literals_with_probe
from dbc_askdata.verify.semantic import rewrite_use_key_literals


def test_accept_use_literal() -> None:
    assert accept_sql_literal(
        "平台研发部",
        {"action": "use_literal", "value_counts": [{"value": "产品部", "count": 1}]},
    )["ok"] is True


def test_accept_use_key_rewritable() -> None:
    v = accept_sql_literal("在职", {"action": "use_key", "key": "1"})
    assert v["ok"] is False
    assert v["rewritable"] is True
    assert v["key"] == "1"


def test_rewrite_use_key_literals_eq() -> None:
    sql = "SELECT id, status FROM hr_employee e WHERE e.status = '在职'"
    new_sql, labels = rewrite_use_key_literals(
        sql,
        [{"table": "hr_employee", "column": "status", "from": "在职", "to": "1"}],
    )
    assert "在职" not in new_sql
    assert "'1'" in new_sql or new_sql.endswith("= 1") or "= '1'" in new_sql
    assert labels


def test_accept_follow_fk() -> None:
    v = accept_sql_literal(
        "平台研发部",
        {
            "action": "follow_fk",
            "targets": [{"table": "org_department", "column": "dept_name"}],
        },
    )
    assert v["ok"] is False
    assert v["action"] == "follow_fk"


@pytest.mark.asyncio
async def test_probe_pass_and_fail() -> None:
    async def fetch_ok(table: str, column: str, condition_value: str | None = None):
        return {
            "action": "use_literal",
            "value_counts": [{"value": "产品部", "count": 1}],
        }

    profiles: dict = {}
    sql = "SELECT id, dept_name FROM org_department d WHERE d.dept_name = '平台研发部'"
    new_sql, rewrites, err = await _check_eq_literals_with_probe(
        sql, profiles=profiles, schema=None, fetch_profile=fetch_ok
    )
    assert err is None
    assert new_sql
    assert rewrites == []

    async def fetch_mismatch(table: str, column: str, condition_value: str | None = None):
        assert condition_value == "在职"
        return {
            "action": "format_mismatch",
            "columnFormat": "code",
            "conditionFormat": "zh",
            "message": "格式不一致",
        }

    profiles2: dict = {}
    sql2 = "SELECT id, status FROM hr_employee e WHERE e.status = '在职'"
    _sql, _rw, result = await _check_eq_literals_with_probe(
        sql2, profiles=profiles2, schema=None, fetch_profile=fetch_mismatch
    )
    assert result is not None
    assert result.ok is False
    assert result.needs_hitl is False
    assert result.code == "EQ_LITERAL_MISMATCH"
    assert "在职" in result.message


@pytest.mark.asyncio
async def test_probe_auto_rewrite_use_key() -> None:
    async def fetch_key(table: str, column: str, condition_value: str | None = None):
        assert condition_value == "在职"
        return {"action": "use_key", "key": "1", "dictionary": True}

    profiles: dict = {}
    sql = "SELECT id, status FROM hr_employee e WHERE e.status = '在职'"
    new_sql, rewrites, err = await _check_eq_literals_with_probe(
        sql, profiles=profiles, schema=None, fetch_profile=fetch_key
    )
    assert err is None
    assert rewrites
    assert "在职" not in new_sql
    assert "1" in new_sql