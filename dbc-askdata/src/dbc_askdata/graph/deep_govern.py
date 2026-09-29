from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.graph.tool_agent import ProgressFn, run_tool_agent
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.verify.repair import parse_workflow_draft

log = logging.getLogger(__name__)

SYSTEM = """你是企业智能问数的治理规划 Agent。
只能通过已提供的 tools 了解元数据，禁止编造表结构。
目标：把脏数据/多表问题拆成有序 GOVERN 节点（写清洗 SQL）+ 最终 QUERY 节点。
输出必须是 JSON：{"name":"...","nodes":[{"id":"n1","type":"GOVERN|QUERY","title":"...","sql":"...","readonly":false}]}
规则：
1. GOVERN 节点 SQL 必须是可落临时表的 SELECT（服务端会包装成 CREATE TABLE AS，表名由服务端生成）
2. 下游引用上游结果必须写 __node_<上游id>__ 或 FROM/JOIN <上游id>（如 FROM __node_n1__ / FROM n1），禁止自造临时表名
3. 源业务表必须带来源 schema（如 company.att_timesheet），禁止未限定表名
4. 最后一个节点必须是 QUERY 只读
5. 不要输出 EXPLAIN，不要多语句
6. 需要列结构时调用 describe_table；当 WHERE/分组依赖状态、类型、性别等离散码值时，先调用 get_column_profile，
   使用返回的 value_counts 真实码值，禁止用自然语言猜测（例如把 active 写成「在职」）
7. 若不涉及离散码值过滤，不要调用 get_column_profile
"""


async def run_deep_govern(
    *,
    settings: Settings,
    llm: LlmClient,
    gateway: ToolGateway,
    spans: SpanRecorder,
    session: AsyncSession,
    question: str,
    workspace_id: int,
    connection_id: int,
    database: str | None,
    schema: str | None,
    catalog_hint: dict[str, Any] | None,
    ctx: dict[str, Any],
    on_progress: ProgressFn | None = None,
) -> dict[str, Any] | None:
    """Deep Agents 风格：多轮 tool_call 后产出 GOVERN+QUERY 草稿。"""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": question,
                    "workspace_id": workspace_id,
                    "connection_id": connection_id,
                    "database": database,
                    "schema": schema,
                    "catalog_hint": catalog_hint,
                },
                ensure_ascii=False,
            ),
        },
    ]
    return await run_tool_agent(
        settings=settings,
        llm=llm,
        gateway=gateway,
        spans=spans,
        session=session,
        messages=messages,
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
        ctx=ctx,
        parent_span_name="deep_govern",
        max_steps=settings.deep_agent_max_steps,
        on_progress=on_progress,
        on_final_content=parse_workflow_draft,
    )
