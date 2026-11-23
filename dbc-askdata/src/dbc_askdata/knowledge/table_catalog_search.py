from __future__ import annotations

import logging
from typing import Any

from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.config import Settings
from dbc_askdata.db.session import SessionLocal
from dbc_askdata.knowledge.table_knowledge import list_metadata_document_ids

log = logging.getLogger(__name__)

CATALOG_TOP_K = 5


async def search_catalog_candidate_tables(
    settings: Settings,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    query: str,
    top_k: int = CATALOG_TOP_K,
) -> dict[str, Any]:
    """
    问数找表：在 METADATA（测表）文档 id 范围内，对知识库做切片语义检索（不改写）。
    只返回候选表名 + 表描述（title / summary），topK 默认 5。
    """
    q = (query or "").strip()
    product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
    limit = max(1, min(int(top_k or CATALOG_TOP_K), CATALOG_TOP_K))
    empty: dict[str, Any] = {
        "productName": product,
        "query": q,
        "documentIds": [],
        "items": [],
    }
    if not q:
        return empty
    if not connection_id or not (database or "").strip():
        return empty

    client = AdaMemoryClient(settings)
    doc_ids: list[int] = []
    try:
        result = await client.search(
            query=q,
            product_name=product,
            top_k=limit,
            kinds="SLICE",
            category_code="METADATA",
            rewrite=False,
            hydrate_body=False,
        )
    except Exception:
        log.error(
            "知识库语义找表失败 query=%s documentIds=%s",
            q,
            doc_ids,
            exc_info=True,
        )
        return {
            "productName": product,
            "query": q,
            "documentIds": doc_ids,
            "items": [],
            "error": "knowledge_search_failed",
        }

    units_raw = result.get("units") if isinstance(result, dict) else None
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    if isinstance(units_raw, list):
        for u in units_raw:
            if not isinstance(u, dict):
                continue
            name = str(u.get("title") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            desc = str(u.get("summary") or "").strip()
            items.append({"name": name, "description": desc})
            if len(items) >= limit:
                break

    return {
        "productName": product,
        "query": q,
        "documentIds": doc_ids,
        "items": items,
    }
