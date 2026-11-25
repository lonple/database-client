from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from dbc_askdata.clients.retry import with_one_retry
from dbc_askdata.verify.service import explain_check


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_errors_are_not_retried(status):
    call = AsyncMock(side_effect=HTTPException(status, "denied"))
    with pytest.raises(HTTPException):
        await with_one_retry("downstream", call)
    assert call.await_count == 1


@pytest.mark.parametrize("status", [401, 403])
async def test_explain_auth_errors_do_not_fall_back_or_trigger_sql_repair(status):
    execute = AsyncMock(side_effect=HTTPException(status, "denied"))
    with pytest.raises(HTTPException):
        await explain_check(
            SimpleNamespace(execute=execute), workspace_id=1, connection_id=1, sql="SELECT 1"
        )
    assert execute.await_count == 1


async def test_explain_unsupported_format_still_falls_back():
    execute = AsyncMock(side_effect=[HTTPException(400, "unsupported format"), {}])
    result = await explain_check(
        SimpleNamespace(execute=execute), workspace_id=1, connection_id=1, sql="SELECT 1"
    )
    assert result.ok
    assert execute.await_count == 2
