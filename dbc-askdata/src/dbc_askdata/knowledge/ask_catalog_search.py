from __future__ import annotations

import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskKnowledgeBinding
from dbc_askdata.db.session import SessionLocal
from dbc_askdata.knowledge.table_intent import (
    ROLE_ATTR,
    ROLE_FILTER,
    ROLE_TABLE,
    normalize_entity_role,
)
from dbc_askdata.knowledge.table_knowledge import list_metadata_document_ids

log = logging.getLogger(__name__)

ASK_CATALOG_TOP_K = 5
_PATH_FETCH_K = 5


async def list_question_document_ids(
    session: AsyncSession,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
) -> list[int]:
    """已入库的问句知识文章 id（含未发布草稿的索引；检索时 memory 侧仅命中已发布）。"""
    if not connection_id or not (database or "").strip():
        return []
    stmt = select(AskKnowledgeBinding.document_id).where(
        AskKnowledgeBinding.deleted.is_(False),
        AskKnowledgeBinding.knowledge_category == "QUESTION",
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


def _hit_score(unit: dict[str, Any]) -> float:
    for key in ("score", "rerankScore", "rerank_score"):
        raw = unit.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return 0.0


async def _load_involved_tables_by_doc_ids(
    document_ids: list[int],
) -> dict[int, list[dict[str, str]]]:
    """documentId → [{name, description}, ...]，来自 ask_knowledge_binding.involved_tables。"""
    if not document_ids:
        return {}
    try:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(
                        AskKnowledgeBinding.document_id,
                        AskKnowledgeBinding.involved_tables,
                    ).where(
                        AskKnowledgeBinding.deleted.is_(False),
                        AskKnowledgeBinding.document_id.in_(
                            [int(x) for x in document_ids]
                        ),
                    )
                )
            ).all()
    except Exception:
        log.warning("加载问句涉表索引失败", exc_info=True)
        return {}
    out: dict[int, list[dict[str, str]]] = {}
    for doc_id, tables in rows:
        if doc_id is None:
            continue
        items: list[dict[str, str]] = []
        if isinstance(tables, list):
            for t in tables:
                if isinstance(t, dict):
                    name = str(t.get("name") or "").strip()
                    if name:
                        items.append(
                            {
                                "name": name,
                                "description": str(t.get("description") or "").strip(),
                            }
                        )
                elif isinstance(t, str) and t.strip():
                    items.append({"name": t.strip(), "description": ""})
        out[int(doc_id)] = items
    return out


def _units_to_table_rows(
    units: list[Any] | None,
    *,
    path: str,
) -> list[tuple[str, str, float, str]]:
    rows: list[tuple[str, str, float, str]] = []
    if not isinstance(units, list):
        return rows
    for u in units:
        if not isinstance(u, dict):
            continue
        name = str(u.get("title") or "").strip()
        if not name:
            continue
        desc = str(u.get("summary") or "").strip()
        rows.append((name, desc, _hit_score(u), path))
    return rows


async def _search_question_path(
    client: AdaMemoryClient,
    *,
    query: str,
    product: str,
    document_ids: list[int],
    involved_by_doc: dict[int, list[dict[str, str]]],
) -> list[tuple[str, str, float, str]]:
    q = (query or "").strip()
    if not q:
        return []
    try:
        result = await client.search(
            query=q,
            product_name=product,
            top_k=_PATH_FETCH_K,
            kinds="SLICE,DOCUMENT",
            document_ids=document_ids,
            category_code=None if document_ids else "QUESTION",
            rewrite=False,
            hydrate_body=False,
        )
    except Exception:
        log.warning("问数问句找表失败 query=%s", q[:80], exc_info=True)
        return []
    units = result.get("units") if isinstance(result, dict) else None
    if not isinstance(units, list):
        return []
    rows: list[tuple[str, str, float, str]] = []
    seen_doc: set[int] = set()
    for u in units:
        if not isinstance(u, dict):
            continue
        score = _hit_score(u)
        raw_doc = u.get("documentId") if u.get("documentId") is not None else u.get("refId")
        try:
            doc_id = int(raw_doc) if raw_doc is not None else None
        except (TypeError, ValueError):
            doc_id = None
        if doc_id is None or doc_id in seen_doc:
            continue
        seen_doc.add(doc_id)
        tables = (involved_by_doc or {}).get(doc_id) or []
        if tables:
            for t in tables:
                name = str(t.get("name") or "").strip()
                if name:
                    rows.append((name, str(t.get("description") or ""), score, "question"))
            continue
        title = str(u.get("title") or "").strip()
        name = title.rsplit(".", 1)[-1].strip() if title else ""
        if name:
            rows.append((name, str(u.get("summary") or ""), score, "question"))
    return rows


def _pair_zh_en(pair: dict[str, str] | None) -> tuple[str, str]:
    if not isinstance(pair, dict):
        return "", ""
    return str(pair.get("entity") or "").strip(), str(pair.get("english") or "").strip()


def build_table_search_queries(
    table_pairs: list[dict[str, str]],
    attr_pairs: list[dict[str, str]],
    *,
    question: str = "",
) -> dict[str, str | None]:
    """
    组装 ada-memory /search/tables 分字段参数：
    - descriptionQuery：主表中文（说明）
    - titleQuery：主表英文（标题）
    - bodySummaryQuery：字段「英文 中文 | …」
    - ftsQuery：表「英文 中文|…」+ 字段
    """
    primary = table_pairs[0] if table_pairs else None
    p_zh, p_en = _pair_zh_en(primary)
    title_q = p_en or None
    desc_q = p_zh or None

    attr_parts: list[str] = []
    for p in attr_pairs:
        zh, en = _pair_zh_en(p)
        chunk = " ".join(x for x in (en, zh) if x).strip()
        if chunk:
            attr_parts.append(chunk)
    body_summary_q = " | ".join(attr_parts) if attr_parts else None

    table_segs: list[str] = []
    for p in table_pairs:
        zh, en = _pair_zh_en(p)
        seg = " ".join(x for x in (en, zh) if x).strip()
        if seg:
            table_segs.append(seg)
    fts_parts: list[str] = []
    if table_segs:
        fts_parts.append("|".join(table_segs))
    if attr_parts:
        fts_parts.append(" | ".join(attr_parts))
    fts_q = "|".join(fts_parts) if fts_parts else None

    if not title_q and not desc_q and not body_summary_q and not fts_q:
        q = (question or "").strip()
        if q:
            desc_q = q
            fts_q = q

    return {
        "titleQuery": title_q,
        "descriptionQuery": desc_q,
        "bodySummaryQuery": body_summary_q,
        "ftsQuery": fts_q,
    }


def split_catalog_roles(
    entity_pairs: list[dict[str, str]] | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """拆成 table 锚点与 attr；filter 丢弃。"""
    tables: list[dict[str, str]] = []
    attrs: list[dict[str, str]] = []
    for raw in entity_pairs or []:
        if not isinstance(raw, dict):
            continue
        role = normalize_entity_role(raw.get("role"))
        if role == ROLE_FILTER:
            continue
        zh = str(raw.get("entity") or "").strip()
        en = str(raw.get("english") or "").strip()
        if not zh and not en:
            continue
        item = {"entity": zh, "english": en, "role": role}
        if role == ROLE_ATTR:
            attrs.append(item)
        else:
            tables.append(item)
    return tables, attrs


def catalog_search_pairs(
    entity_pairs: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    """兼容旧测试：返回会参与检索规划的实体（table + attr，无 filter）。"""
    tables, attrs = split_catalog_roles(entity_pairs)
    return [*tables, *attrs]


def _normalize_entity_pairs(
    entity_pairs: list[dict[str, str]] | None,
    *,
    entity_zh: str | None,
    entity_en: str | None,
) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in entity_pairs or []:
        if not isinstance(raw, dict):
            continue
        zh = str(raw.get("entity") or raw.get("entityZh") or "").strip()
        en = str(raw.get("english") or raw.get("entityEn") or "").strip()
        if not zh and not en:
            continue
        role = normalize_entity_role(raw.get("role"))
        key = f"{zh.lower()}|{en.lower()}|{role}"
        if key in seen:
            continue
        seen.add(key)
        pairs.append({"entity": zh, "english": en, "role": role})
    if not pairs:
        zh = (entity_zh or "").strip()
        en = (entity_en or "").strip()
        if zh or en:
            pairs.append({"entity": zh, "english": en, "role": ROLE_TABLE})
    return pairs


# 检索算法变更时递增，避免命中旧版错误候选表缓存
_ASK_CATALOG_CACHE_VER = "v6-related-score-minus-one"


def _plan_cache_fingerprint(
    table_pairs: list[dict[str, str]],
    attr_pairs: list[dict[str, str]],
) -> str:
    """检索计划指纹：同问句但选表计划不同时不应复用缓存。"""
    chunks: list[str] = []
    for p in table_pairs:
        chunks.append(
            "t:"
            + (p.get("entity") or "").strip().lower()
            + "|"
            + (p.get("english") or "").strip().lower()
        )
    for p in attr_pairs:
        chunks.append(
            "a:"
            + (p.get("entity") or "").strip().lower()
            + "|"
            + (p.get("english") or "").strip().lower()
        )
    raw = "\n".join(chunks)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _ask_catalog_cache_key_parts(
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    question: str,
    limit: int,
    plan_fp: str,
) -> tuple[str, ...]:
    """缓存键：版本 + 连接/库/模式/问句/计划指纹/topK。"""
    return (
        "tool",
        "ask_catalog",
        _ASK_CATALOG_CACHE_VER,
        str(int(connection_id)),
        str(database or "").strip(),
        str(schema or "").strip(),
        question.strip(),
        plan_fp or "-",
        str(limit),
    )


async def search_ask_catalog(
    settings: Settings,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    question: str,
    entity_pairs: list[dict[str, str]] | None = None,
    entity_zh: str | None = None,
    entity_en: str | None = None,
    top_k: int = ASK_CATALOG_TOP_K,
) -> dict[str, Any]:
    """
    问数专用找表（非 LLM tool 的 search_catalog）。

    1) 本地绑定取 METADATA documentIds + 可选 graphId
    2) POST /api/search/tables（中文→说明、英文→标题、字段→正文摘要、表|字段→fts）
    3) QUESTION 旁路仍可补表名（不驱动预选）
    """
    from dbc_askdata.api.table_relation_routes import find_binding_for_scope
    from dbc_askdata.redis.client import get_redis

    product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
    limit = max(1, min(int(top_k or ASK_CATALOG_TOP_K), ASK_CATALOG_TOP_K))
    pairs = _normalize_entity_pairs(entity_pairs, entity_zh=entity_zh, entity_en=entity_en)
    table_pairs, attr_pairs = split_catalog_roles(pairs)
    plan_fp = _plan_cache_fingerprint(table_pairs, attr_pairs)
    table_first = next(
        (p for p in pairs if normalize_entity_role(p.get("role")) == ROLE_TABLE),
        pairs[0] if pairs else {"entity": "", "english": "", "role": ROLE_TABLE},
    )
    zh_list = [p["entity"] for p in pairs if p.get("entity")]
    en_list = [p["english"] for p in pairs if p.get("english")]
    q = (question or "").strip()
    empty: dict[str, Any] = {
        "productName": product,
        "question": q,
        "entities": pairs,
        "entity": table_first.get("entity") or "",
        "english": table_first.get("english") or "",
        "entitiesZh": zh_list,
        "entitiesEn": en_list,
        "documentIds": {"metadata": [], "question": []},
        "paths": {},
        "items": [],
        "tableRelations": [],
        "graphId": None,
    }
    if not connection_id or not (database or "").strip():
        return empty

    redis = get_redis()
    cache_parts = _ask_catalog_cache_key_parts(
        connection_id=connection_id,
        database=database,
        schema=schema,
        question=q,
        limit=limit,
        plan_fp=plan_fp,
    )
    if redis is not None:
        cached = await redis.get_json(*cache_parts)
        # 空结果可能是瞬时失败写入的，不复用
        if isinstance(cached, dict) and "items" in cached and (cached.get("items") or []):
            out = dict(cached)
            out["__cache__"] = "hit"
            log.info(
                "ask_catalog 命中 Redis 缓存 connection_id=%s question=%r items=%s",
                connection_id,
                q[:80],
                len(out.get("items") or []),
            )
            return out
        if isinstance(cached, dict) and not (cached.get("items") or []):
            log.info(
                "ask_catalog 忽略空结果缓存 connection_id=%s question=%r",
                connection_id,
                q[:80],
            )
    else:
        log.info("ask_catalog 跳过 Redis（未连接） connection_id=%s", connection_id)

    from dbc_askdata.clients.ada_graph import AdaGraphClient
    from dbc_askdata.db.session import SessionLocal

    # 图谱：优先连接绑定；否则按配置编码（默认 default）解析
    graph_id: int | None = None
    try:
        async with SessionLocal() as session:
            binding = await find_binding_for_scope(
                session,
                connection_id=int(connection_id),
                database=database,
                schema=schema,
            )
            if binding is not None and binding.graph_id:
                graph_id = int(binding.graph_id)
    except Exception:
        log.warning(
            "ask_catalog 读取表关系绑定失败 connection_id=%s",
            connection_id,
            exc_info=True,
        )
    if graph_id is None:
        try:
            graph_id = await AdaGraphClient(settings).resolve_id()
        except Exception:
            log.warning("ask_catalog 按编码解析图谱失败", exc_info=True)
            graph_id = None
    meta_ids: list[int] = []
    q_ids: list[int] = []
    empty["documentIds"] = {"metadata": [], "question": []}
    empty["graphId"] = graph_id

    client = AdaMemoryClient(settings)
    path_meta: dict[str, int] = {}
    merged: dict[str, dict[str, Any]] = {}
    table_relations: list[dict[str, Any]] = []

    def _absorb_item(item: dict[str, Any], *, path: str) -> None:
        name = str(item.get("name") or item.get("title") or "").strip()
        if not name:
            return
        nk = name.lower()
        source = str(item.get("source") or path or "").strip()
        # 语义命中保留知识库得分；图谱邻接 RELATED 固定 -1
        if source.upper() == "RELATED":
            score = -1.0
        else:
            score_raw = item.get("score")
            try:
                score = float(score_raw) if score_raw is not None else 0.0
            except (TypeError, ValueError):
                score = 0.0
        prev = merged.get(nk)
        if prev is not None and score <= float(prev.get("score") or 0):
            # RELATED 可补字段摘要
            if not prev.get("bodySummary") and item.get("bodySummary"):
                prev["bodySummary"] = item.get("bodySummary")
            return
        merged[nk] = {
            "name": name,
            "title": item.get("title") or name,
            "description": item.get("description") or "",
            "bodySummary": item.get("bodySummary") or "",
            "score": score,
            "source": source or path,
            "path": path,
        }

    queries = build_table_search_queries(table_pairs, attr_pairs, question=q)
    log.info(
        "ask_catalog METADATA search_tables title=%r desc=%r bodySum=%r fts=%r graphId=%s",
        (queries.get("titleQuery") or "")[:40],
        (queries.get("descriptionQuery") or "")[:40],
        (queries.get("bodySummaryQuery") or "")[:80],
        (queries.get("ftsQuery") or "")[:120],
        graph_id,
    )
    try:
        table_res = await client.search_tables(
            product_name=product,
            category_code="METADATA",
            document_ids=meta_ids or None,
            top_k=max(limit, _PATH_FETCH_K),
            title_query=queries.get("titleQuery"),
            description_query=queries.get("descriptionQuery"),
            body_summary_query=queries.get("bodySummaryQuery"),
            fts_query=queries.get("ftsQuery"),
            graph_id=graph_id,
            rewrite=False,
        )
        tables = table_res.get("tables") if isinstance(table_res, dict) else None
        n_hit = 0
        if isinstance(tables, list):
            for t in tables:
                if isinstance(t, dict):
                    _absorb_item(t, path="metadata")
                    n_hit += 1
        path_meta["metadata"] = n_hit
        rels = table_res.get("tableRelations") if isinstance(table_res, dict) else None
        if isinstance(rels, list):
            table_relations = [r for r in rels if isinstance(r, dict)]
    except Exception:
        log.warning("问数 METADATA search_tables 失败", exc_info=True)
        path_meta["metadata"] = 0

    if q:
        q_rows = await _search_question_path(
            client,
            query=q,
            product=product,
            document_ids=None,
            involved_by_doc={},
        )
        path_meta["question"] = len(q_rows)
        for name, desc, score, p in q_rows:
            _absorb_item(
                {
                    "name": name,
                    "description": desc,
                    "score": score,
                    "source": "QUESTION",
                },
                path=p,
            )

    # 语义得分优先；RELATED(-1) 排后
    ranked = sorted(
        merged.values(),
        key=lambda x: float(x.get("score") if x.get("score") is not None else -1.0),
        reverse=True,
    )
    items = [
        {
            "name": r["name"],
            "title": r.get("title") or r["name"],
            "description": r.get("description") or "",
            "bodySummary": r.get("bodySummary") or "",
            "score": r.get("score"),
            "source": r.get("source") or "",
        }
        for r in ranked[: max(limit * 3, limit)]
    ]
    score_txt = "、".join(
        f"{it.get('name')}={it.get('score')}"
        f"[{str(it.get('source') or '').upper() or '-'}]"
        for it in items
        if it.get("name")
    )
    log.info(
        "ask_catalog 候选表得分 connection_id=%s question=%r count=%s tables=%s",
        connection_id,
        q[:80],
        len(items),
        score_txt or "-",
    )
    result: dict[str, Any] = {
        "productName": product,
        "question": q,
        "entities": pairs,
        "entity": table_first.get("entity") or "",
        "english": table_first.get("english") or "",
        "entitiesZh": zh_list,
        "entitiesEn": en_list,
        "documentIds": {"metadata": meta_ids, "question": q_ids},
        "paths": path_meta,
        "items": items,
        "tableRelations": table_relations,
        "graphId": graph_id,
    }
    if redis is not None and items:
        await redis.set_json(
            *cache_parts,
            value={k: v for k, v in result.items() if k != "__cache__"},
            ttl_seconds=settings.tool_cache_ttl_seconds,
        )
        result["__cache__"] = "set"
    elif redis is not None:
        result["__cache__"] = "skip_empty"
        log.info(
            "ask_catalog 空结果不写缓存 connection_id=%s question=%r paths=%s",
            connection_id,
            q[:80],
            path_meta,
        )
    else:
        result["__cache__"] = "disabled"
    return result
