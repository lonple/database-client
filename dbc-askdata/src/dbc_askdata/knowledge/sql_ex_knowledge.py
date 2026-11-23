"""SQL_EX 分类知识：按分类拉取已发布原文正文（不分片），注入问数生成上下文。"""

from __future__ import annotations

import logging
from typing import Any

from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.config import Settings

log = logging.getLogger(__name__)

SQL_EX_CATEGORY = "SQL_EX"
SQL_EX_CATEGORY_NAME = "SQL示例"
_MAX_DOCS = 20
_MAX_BODY_CHARS = 8000


def format_sql_ex_knowledge_for_prompt(
    items: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """整理为 build user 载荷字段。"""
    if not items:
        return None
    examples: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        body = (it.get("body") or it.get("summary") or "").strip()
        if not body:
            continue
        if len(body) > _MAX_BODY_CHARS:
            body = body[:_MAX_BODY_CHARS] + "\n…(截断)"
        examples.append(
            {
                "title": it.get("title") or "SQL示例",
                "content": body,
                "documentId": it.get("documentId") or it.get("id"),
            }
        )
    if not examples:
        return None
    return {
        "category": SQL_EX_CATEGORY,
        "examples": examples,
        "instruction": (
            "以下为知识库分类 SQL_EX（SQL示例）中的已发布原文，生成 SQL 时须遵守其中语法与写法要求，"
            "对照正确示例，禁止再写出错误示例中的粘连/错误写法。"
        ),
    }


async def load_sql_ex_knowledge(
    settings: Settings,
    *,
    ensure_category: bool = True,
    limit: int = _MAX_DOCS,
) -> list[dict[str, Any]]:
    """按分类 SQL_EX 列出已发布原文，并拉取正文（不走切片检索）。"""
    client = AdaMemoryClient(settings)
    try:
        if ensure_category:
            cat_id = await client.ensure_category(SQL_EX_CATEGORY, name=SQL_EX_CATEGORY_NAME)
        else:
            cat_id = await client.category_id(SQL_EX_CATEGORY)
    except Exception:
        log.warning("SQL_EX 分类不可用，跳过 SQL 示例知识", exc_info=True)
        return []

    try:
        page = await client.list_published_documents(
            category_id=cat_id,
            page=1,
            size=min(max(1, int(limit)), 50),
        )
    except Exception:
        log.warning("列出 SQL_EX 已发布原文失败", exc_info=True)
        return []

    records = page.get("records") if isinstance(page, dict) else None
    if not isinstance(records, list) or not records:
        return []

    out: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        doc_id = int(row["id"])
        try:
            detail = await client.get_document(doc_id)
        except Exception:
            log.warning("拉取 SQL_EX 原文失败 document_id=%s", doc_id, exc_info=True)
            continue
        if not isinstance(detail, dict):
            continue
        body = (detail.get("body") or "").strip()
        summary = (detail.get("summary") or row.get("summary") or "").strip()
        if not body and not summary:
            continue
        out.append(
            {
                "documentId": doc_id,
                "title": (detail.get("title") or row.get("title") or "").strip() or f"doc-{doc_id}",
                "summary": summary,
                "body": body or summary,
            }
        )
    return out
