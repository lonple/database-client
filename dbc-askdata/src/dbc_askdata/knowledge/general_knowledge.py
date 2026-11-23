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


def build_scope_knowledge_query(
    *,
    database: str | None,
    schema: str | None,
    suffix: str,
) -> str | None:
    """查询项：优先「模式名 + suffix」，无模式时退化为「库名 + suffix」。"""
    label = (suffix or "").strip()
    if not label:
        return None
    schema_s = (schema or "").strip()
    if schema_s:
        return f"{schema_s} {label}"
    database_s = (database or "").strip()
    if database_s:
        return f"{database_s} {label}"
    return None


def build_db_general_query(*, database: str | None, schema: str | None) -> str | None:
    """查询项：优先「模式名 + 库通用知识」，无模式时退化为「库名 + 库通用知识」。"""
    return build_scope_knowledge_query(database=database, schema=schema, suffix="库通用知识")


def build_catalog_directory_query(*, database: str | None, schema: str | None) -> str | None:
    """查询项：优先「模式名 + 库表目录」，无模式时退化为「库名 + 库表目录」。"""
    return build_scope_knowledge_query(database=database, schema=schema, suffix="库表目录")


def unwrap_general_knowledge_result(
    raw: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """剥离内部 __cache__ 标记；空命中返回 (None, cache_status)。"""
    if not isinstance(raw, dict):
        return None, None
    cache = raw.get("__cache__")
    if isinstance(cache, str):
        cache_s = cache
    else:
        cache_s = None
    if cache_s in ("hit_miss", "set_miss"):
        return None, cache_s
    body = (raw.get("body") or raw.get("summary") or "").strip()
    if not body:
        return None, cache_s
    clean = {k: v for k, v in raw.items() if k != "__cache__"}
    return clean, cache_s


def format_db_general_knowledge_for_prompt(kg: dict[str, Any] | None) -> dict[str, Any] | None:
    """将 state 中的库通用知识整理为生成 SQL 的 user 载荷字段。"""
    if not isinstance(kg, dict):
        return None
    content = (kg.get("body") or kg.get("summary") or "").strip()
    if not content:
        return None
    return {
        "title": kg.get("title"),
        "content": content,
        "instruction": (
            "以下为当前库/模式的通用业务知识（初始化检索命中一条）。"
            "生成与解释 SQL 时须参考其中业务口径、术语与常用关联；不得与之明显冲突。"
        ),
    }


def format_catalog_directory_knowledge_for_prompt(kg: dict[str, Any] | None) -> dict[str, Any] | None:
    """将「库表目录」切片整理为选表提示：中文表意优先，避免订单/报销等混淆。"""
    if not isinstance(kg, dict):
        return None
    content = (kg.get("body") or kg.get("summary") or "").strip()
    if not content:
        return None
    return {
        "title": kg.get("title"),
        "content": content,
        "instruction": (
            "以下为当前库/模式的库表目录说明（search_catalog 旁路命中一条切片）。"
            "选表时必须先对照其中「物理表名 ↔ 中文业务含义」与用户问题用语对齐；"
            "禁止仅凭表名英文单词或猜测选表，也不得把含义不同的表互相替代。"
        ),
    }


async def list_general_document_ids(
    session: AsyncSession,
    *,
    connection_id: int | None = None,
    database: str | None = None,
    schema: str | None = None,
) -> list[int]:
    """通用知识（GENERAL）文章 id；有作用域时按绑定过滤。"""
    stmt = select(AskKnowledgeBinding.document_id).where(
        AskKnowledgeBinding.deleted.is_(False),
        AskKnowledgeBinding.knowledge_category == "GENERAL",
    )
    if connection_id and (database or "").strip():
        stmt = stmt.where(
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
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


async def _search_general_slice(
    settings: Settings,
    *,
    query: str,
    log_label: str,
    connection_id: int | None = None,
    database: str | None = None,
    schema: str | None = None,
) -> dict[str, Any] | None:
    """GENERAL 范围内只检索切片（kinds=SLICE），topK=1，并 get_knowledge 拉正文。

    失败/未命中返回 None。命中结果写入 Redis（TTL=tool_cache_ttl_seconds）。
    """
    from dbc_askdata.redis.client import get_redis

    product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
    redis = get_redis()
    cache_parts = (
        "kg",
        "general",
        product,
        str(connection_id or ""),
        str(database or ""),
        str(schema or ""),
        query,
    )
    if redis is None:
        log.info("%s跳过 Redis（未连接）query=%s", log_label, query)
    else:
        cached = await redis.get_json(*cache_parts)
        if isinstance(cached, dict):
            if cached.get("__miss__"):
                log.info("%s命中 Redis 空缓存 query=%s", log_label, query)
                return {"__cache__": "hit_miss", "query": query}
            if cached.get("body") or cached.get("summary"):
                log.info("%s命中 Redis 缓存 query=%s refId=%s", log_label, query, cached.get("refId"))
                out = dict(cached)
                out["__cache__"] = "hit"
                return out

    client = AdaMemoryClient(settings)
    try:
        result = await client.search(
            query=query,
            product_name=product,
            top_k=1,
            kinds="SLICE",
            category_code="GENERAL",
            rewrite=False,
        )
    except Exception:
        log.error("%s检索失败 query=%s", log_label, query, exc_info=True)
        return None

    units_raw = result.get("units") if isinstance(result, dict) else None
    if not isinstance(units_raw, list) or not units_raw:
        log.info("%s未命中 query=%s", log_label, query)
        if redis is not None:
            # 空结果也短缓存，避免同 scope 反复打 knowledge
            await redis.set_json(
                *cache_parts,
                value={"__miss__": True, "query": query},
                ttl_seconds=min(300, max(60, int(settings.tool_cache_ttl_seconds))),
            )
        return {"__cache__": "set_miss", "query": query}

    u = units_raw[0]
    if not isinstance(u, dict):
        return None

    item: dict[str, Any] = {
        "query": query,
        "kind": u.get("kind") or "SLICE",
        "refId": u.get("refId"),
        "documentId": u.get("documentId"),
        "title": u.get("title"),
        "summary": u.get("summary"),
        "score": u.get("score"),
        "body": u.get("body"),
    }
    body = (item.get("body") or "").strip()
    summary = (item.get("summary") or "").strip()
    if not body and not summary:
        return None
    if not body:
        item["body"] = summary
    if redis is not None:
        await redis.set_json(
            *cache_parts,
            value={k: v for k, v in item.items() if k != "__cache__"},
            ttl_seconds=settings.tool_cache_ttl_seconds,
        )
        item["__cache__"] = "set"
    else:
        item["__cache__"] = "disabled"
    return item


async def search_db_general_knowledge(
    settings: Settings,
    *,
    connection_id: int | None = None,
    database: str | None,
    schema: str | None,
) -> dict[str, Any] | None:
    """
    初始化检索库通用知识：query=「模式名 库通用知识」，只取 1 条切片正文。
    失败或未命中返回 None，不阻断主流程。
    """
    query = build_db_general_query(database=database, schema=schema)
    if not query:
        return None
    return await _search_general_slice(
        settings,
        query=query,
        log_label="库通用知识",
        connection_id=connection_id,
        database=database,
        schema=schema,
    )


async def search_catalog_directory_knowledge(
    settings: Settings,
    *,
    connection_id: int | None = None,
    database: str | None,
    schema: str | None,
) -> dict[str, Any] | None:
    """
    search_catalog 旁路：query=「模式名 库表目录」，只取 1 条 GENERAL 切片。
    失败或未命中返回 None，不阻断目录主流程。
    """
    query = build_catalog_directory_query(database=database, schema=schema)
    if not query:
        return None
    return await _search_general_slice(
        settings,
        query=query,
        log_label="库表目录",
        connection_id=connection_id,
        database=database,
        schema=schema,
    )
