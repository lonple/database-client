from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.graph.hitl_prompt import hitl_for_sql_prompt
from dbc_askdata.graph.tool_agent import ProgressFn, run_tool_agent
from dbc_askdata.knowledge.general_knowledge import (
    format_catalog_directory_knowledge_for_prompt,
    format_db_general_knowledge_for_prompt,
)
from dbc_askdata.llm.client import LlmClient
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.verify.repair import parse_workflow_draft

log = logging.getLogger(__name__)

SYSTEM = """你是企业智能问数的治理规划 Agent。
只能通过已提供的目录摘要与 tools 了解元数据，禁止编造表结构。
目标：把脏数据/多表问题拆成有序 GOVERN 节点（写清洗 SQL）+ 最终 QUERY 节点。
输出必须是 JSON：{"name":"...","nodes":[{"id":"n1","type":"GOVERN|QUERY","title":"...","sql":"...","readonly":false}]}
规则：
1. GOVERN 节点 SQL 必须是可落临时表的 SELECT（服务端会包装成 CREATE TABLE AS，表名由服务端生成）
2. 下游引用上游结果必须写 __node_<上游id>__ 或 FROM/JOIN <上游id>（如 FROM __node_n1__ / FROM n1），禁止自造临时表名
3. 源业务表必须带来源 schema（如 company.att_timesheet），禁止未限定表名
4. 最后一个节点必须是 QUERY 只读
5. 不要输出 EXPLAIN，不要多语句
6. 可见表目录已在上下文 catalog_hint 中，禁止再调用 search_catalog
7. 若上下文含 catalog_directory_knowledge：须先对照「表名↔中文业务含义」与用户话术对齐初选表，禁止凭英文表名猜测或互替
8. 若上下文含 hitl_confirmation：码值/口径用其原文写条件，仅标识符才当表名
9. 若上下文含 db_general_knowledge：须遵守其中业务口径、术语与常用关联约定
10. **强制**：凡 SQL 将引用的每一张源业务表，必须先调用 describe_table；列名必须来自返回的 columns，禁止臆造
11. describe_table 若返回 knowledge：须再次核对表业务含义是否匹配用户问题；不符则换表并重新 describe，禁止在错误表上硬写 SQL
12. 当 WHERE/分组依赖状态、类型、性别等离散码值时，**必须先**调用 get_column_profile，
   使用返回的 value_counts 真实码值，禁止用自然语言或用户话术直接当条件值；不确定则说明需人工确认
13. 若不涉及离散码值过滤，不要调用 get_column_profile
14. **明细查询**（无聚合、无 GROUP BY）：最外层 WHERE 等值（=/IN）列必须出现在 SELECT 投影中；
    范围条件列不必投影。GOVERN 与 QUERY 均遵守
15. 若上下文含 review_critique：必须按其中指出的漏过滤/错粒度改正，禁止原样重出
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
    db_general_knowledge: dict[str, Any] | None = None,
    catalog_directory_knowledge: dict[str, Any] | None = None,
    hitl_resolution: dict[str, Any] | None = None,
    ctx: dict[str, Any],
    on_progress: ProgressFn | None = None,
    column_profiles: dict[str, Any] | None = None,
    described_columns: dict[str, list[str]] | None = None,
    review_critique: str | None = None,
) -> dict[str, Any] | None:
    """Deep Agents 风格：多轮 tool_call 后产出 GOVERN+QUERY 草稿。"""
    user_payload: dict[str, Any] = {
        "question": question,
        "workspace_id": workspace_id,
        "connection_id": connection_id,
        "database": database,
        "schema": schema,
        "catalog_hint": catalog_hint,
    }
    dir_prompt = format_catalog_directory_knowledge_for_prompt(catalog_directory_knowledge)
    if dir_prompt:
        user_payload["catalog_directory_knowledge"] = dir_prompt
    hitl_prompt = hitl_for_sql_prompt(hitl_resolution)
    if hitl_prompt:
        user_payload["hitl_confirmation"] = hitl_prompt
    kg_prompt = format_db_general_knowledge_for_prompt(db_general_knowledge)
    if kg_prompt:
        user_payload["db_general_knowledge"] = kg_prompt
    if review_critique:
        user_payload["review_critique"] = review_critique
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False),
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
        exclude_tools={"search_catalog", "list_connections"},
        require_describe_tables=True,
        column_profiles=column_profiles,
        described_columns=described_columns,
    )
