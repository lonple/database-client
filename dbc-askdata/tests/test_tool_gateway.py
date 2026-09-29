from dbc_askdata.tools.registry import ToolGateway, ToolRegistry, ToolDecl
from pydantic import BaseModel
import pytest


class _Args(BaseModel):
    x: int


@pytest.mark.asyncio
async def test_unknown_tool_rejected():
    reg = ToolRegistry()

    async def h(args):
        return args

    reg.register(ToolDecl(name="ok_tool", description="d", parameters_model=_Args, handler=h))
    gw = ToolGateway(reg)
    with pytest.raises(ValueError, match="未知"):
        await gw.invoke("raw_execute", {"sql": "select 1"})
