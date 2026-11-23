from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from dbc_askdata.tools.registry import ToolDecl, ToolGateway, ToolRegistry
from dbc_askdata.tools.schema_slim import (
    build_scope_args,
    merge_tool_args,
    openai_tool_from_decl,
    slim_json_schema,
)


class DescribeArgs(BaseModel):
    workspace_id: int
    connection_id: int
    table: str
    database: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


def test_slim_hides_scope_and_noise():
    raw = DescribeArgs.model_json_schema()
    slim = slim_json_schema(raw, hide_scope=True)
    props = slim["properties"]
    assert set(props.keys()) == {"table"}
    assert "title" not in slim
    assert "title" not in props["table"]
    assert slim["required"] == ["table"]


def test_openai_tool_from_decl_short():
    tool = openai_tool_from_decl(
        name="describe_table",
        description="查看表列结构（名称/类型/注释），并附带该连接/库/模式下元数据知识库中与表名相关的切片",
        parameters_schema=DescribeArgs.model_json_schema(),
    )
    assert tool["function"]["name"] == "describe_table"
    assert len(tool["function"]["description"]) <= 96
    assert set(tool["function"]["parameters"]["properties"].keys()) == {"table"}
    before = len(json.dumps({"parameters": DescribeArgs.model_json_schema()}, ensure_ascii=False))
    after = len(json.dumps(tool["function"]["parameters"], ensure_ascii=False))
    assert after < before


def test_merge_scope_server_wins_identity():
    merged = merge_tool_args(
        {"workspace_id": 99, "table": "t1"},
        scope=build_scope_args(workspace_id=1, connection_id=2, database="db", schema="public"),
    )
    assert merged["workspace_id"] == 1
    assert merged["connection_id"] == 2
    assert merged["table"] == "t1"
    assert merged["database"] == "db"
    assert merged["schema"] == "public"


def test_merge_keeps_explicit_schema():
    merged = merge_tool_args(
        {"table": "emp", "schema": "hr"},
        scope=build_scope_args(workspace_id=1, connection_id=2, schema="public"),
    )
    assert merged["schema"] == "hr"


@pytest.mark.asyncio
async def test_gateway_invoke_injects_scope():
    reg = ToolRegistry()
    seen: dict = {}

    async def h(args):
        seen.update(args)
        return {"ok": True}

    reg.register(
        ToolDecl(
            name="describe_table",
            description="d",
            parameters_model=DescribeArgs,
            handler=h,
        )
    )
    gw = ToolGateway(reg)
    tools = gw.openai_tools()
    assert tools[0]["function"]["parameters"]["properties"].keys() == {"table"}

    await gw.invoke(
        "describe_table",
        {"table": "hr_employee"},
        scope=build_scope_args(workspace_id=1, connection_id=12, schema="company"),
    )
    assert seen["workspace_id"] == 1
    assert seen["connection_id"] == 12
    assert seen["table"] == "hr_employee"
    assert seen["schema_name"] == "company"
