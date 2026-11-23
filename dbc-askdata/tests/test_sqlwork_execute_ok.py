import pytest
from fastapi import HTTPException

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.tools.registry import ToolDecl, ToolGateway, ToolRegistry
from pydantic import BaseModel


def test_ensure_execute_ok_raises_on_statement_failure():
    data = {
        "totalCount": 1,
        "successCount": 0,
        "stoppedOnError": True,
        "message": "第 1 条失败: column does not exist",
        "statements": [
            {
                "index": 1,
                "success": False,
                "message": 'ERROR: column "project_id" does not exist',
            }
        ],
    }
    with pytest.raises(HTTPException) as ei:
        SqlworkClient.ensure_execute_ok(data)
    assert "project_id" in str(ei.value.detail)


def test_ensure_execute_ok_passes_when_all_success():
    data = {
        "totalCount": 1,
        "successCount": 1,
        "stoppedOnError": False,
        "statements": [{"index": 1, "success": True, "message": "ok"}],
    }
    assert SqlworkClient.ensure_execute_ok(data) is data


class _Args(BaseModel):
    x: int = 1


def test_openai_tools_exclude():
    reg = ToolRegistry()

    async def h(args):
        return args

    reg.register(ToolDecl(name="search_catalog", description="d", parameters_model=_Args, handler=h))
    reg.register(ToolDecl(name="describe_table", description="d", parameters_model=_Args, handler=h))
    gw = ToolGateway(reg)
    names = {t["function"]["name"] for t in gw.openai_tools(exclude={"search_catalog"})}
    assert names == {"describe_table"}
