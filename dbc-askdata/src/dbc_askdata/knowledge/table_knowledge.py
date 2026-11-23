from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskKnowledgeBinding
from dbc_askdata.db.session import SessionLocal

log = logging.getLogger(__name__)


async def list_metadata_document_ids(
    session: AsyncSession,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
) -> list[int]:
    """按连接+库+模式过滤元数据知识绑定，返回 memory 文章 id。"""
    if not connection_id or not (database or "").strip():
        return []
    stmt = select(AskKnowledgeBinding.document_id).where(
        AskKnowledgeBinding.deleted.is_(False),
        AskKnowledgeBinding.knowledge_category == "METADATA",
        AskKnowledgeBinding.connection_id == int(connection_id),
        AskKnowledgeBinding.database_name == database.strip(),
    )
    schema_s = (schema or "").strip()
    if schema_s:
        stmt = stmt.where(AskKnowledgeBinding.schema_name == schema_s)
    else:
        stmt = stmt.where(
            (AskKnowledgeBinding.schema_name.is_(None))
            | (AskKnowledgeBinding.schema_name == "")
        )
    result = await session.execute(stmt)
    ids = [int(x) for x in result.scalars().all() if x is not None]
    # 保序去重
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


async def search_table_knowledge(
    settings: Settings,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    table: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    本地索引取文章 id → memory 切片语义检索（documentIds + kinds=SLICE），
    再 get_knowledge 补正文。失败时降级为空命中，不阻断列结构查询。
    """
    table_name = (table or "").strip()
    product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
    empty = {
        "productName": product,
        "query": table_name,
        "documentIds": [],
        "units": [],
    }
    if not table_name:
        return empty

    client = AdaMemoryClient(settings)
    doc_ids: list[int] = []
    try:
        result = await client.search(
            query=table_name,
            product_name=product,
            top_k=top_k,
            kinds="SLICE",
            category_code="METADATA",
            rewrite=False,
        )
    except Exception:
        log.error(
            "memory 切片检索失败 table=%s documentIds=%s",
            table_name,
            doc_ids,
            exc_info=True,
        )
        return {
            "productName": product,
            "query": table_name,
            "documentIds": doc_ids,
            "units": [],
            "error": "knowledge_search_failed",
        }

    units_raw = result.get("units") if isinstance(result, dict) else None
    units: list[dict[str, Any]] = []
    if isinstance(units_raw, list):
        for u in units_raw[:top_k]:
            if isinstance(u, dict):
                units.append(u)

    return {
        "productName": product,
        "query": table_name,
        "documentIds": doc_ids,
        "units": units,
    }
