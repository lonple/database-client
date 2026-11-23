from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import HTTPException

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)


def parse_unit_kind(unit: dict[str, Any], default: str = "SLICE") -> str:
    kind = str(unit.get("kind") or default).strip().upper()
    return kind or default


def parse_unit_ref_id(unit: dict[str, Any]) -> int | None:
    """get_knowledge / GET /api/units 使用检索命中的 refId，不是列表项 id（unit_index.id）。"""
    raw = unit.get("refId")
    if raw is None:
        raw = unit.get("ref_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        log.warning("知识命中 refId 无法解析 value=%r", raw)
        return None


def merge_unit_detail(hit: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, Any]:
    """把 get_knowledge 正文合并进 search 命中（search 仅有 title/summary）。"""
    out = dict(hit)
    if not isinstance(detail, dict):
        return out
    body = detail.get("body")
    if body is not None:
        out["body"] = body
    if not out.get("title") and detail.get("title"):
        out["title"] = detail.get("title")
    if not out.get("summary") and detail.get("summary"):
        out["summary"] = detail.get("summary")
    if out.get("documentId") is None and detail.get("documentId") is not None:
        out["documentId"] = detail.get("documentId")
    return out


class AdaMemoryClient:
    """旁路调用 ada-memory REST；向量化由对方同步至 Milvus ada_document / ada_slice。"""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.ada_memory_base_url.rstrip("/")
        self._timeout = settings.ada_memory_timeout_seconds

    def _client(self):
        from dbc_askdata.clients.downstream_auth import AuthedHttp
        from dbc_askdata.httpx_pool import shared_async_client

        return AuthedHttp(shared_async_client("ada-memory", timeout=self._timeout, trust_env=False))

    async def _unwrap(self, resp: httpx.Response) -> Any:
        try:
            body = resp.json()
        except Exception as ex:
            log.error(
                "ada-memory 响应非 JSON url=%s status=%s body=%s",
                str(resp.request.url),
                resp.status_code,
                (resp.text or "")[:300],
                exc_info=True,
            )
            raise HTTPException(
                status_code=502, detail=f"ada-memory 响应非 JSON: {resp.status_code}"
            ) from ex
        if resp.status_code >= 400:
            msg = body.get("message") if isinstance(body, dict) else None
            raise HTTPException(status_code=resp.status_code, detail=msg or f"ada-memory HTTP {resp.status_code}")
        if isinstance(body, dict) and "code" in body:
            code = body.get("code")
            if code not in (0, "0", None):
                raise HTTPException(status_code=400, detail=body.get("message") or "ada-memory 业务失败")
            return body.get("data")
        return body

    async def list_documents(
        self,
        status: str | None = None,
        *,
        category_id: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if category_id is not None:
            params["categoryId"] = int(category_id)
        resp = await self._client().get(f"{self._base}/api/documents", params=params)
        data = await self._unwrap(resp)
        return data or []

    async def list_published_documents(
        self,
        *,
        category_id: int | None = None,
        category_code: str | None = None,
        q: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> dict[str, Any]:
        """GET /api/documents/published：已发布原文分页（可按分类）。"""
        params: dict[str, Any] = {
            "page": max(1, int(page)),
            "size": min(max(1, int(size)), 50),
        }
        cid = category_id
        code = (category_code or "").strip()
        if cid is None and code:
            cid = await self.category_id(code)
        if cid is not None:
            params["categoryId"] = int(cid)
        if (q or "").strip():
            params["q"] = q.strip()
        resp = await self._client().get(f"{self._base}/api/documents/published", params=params)
        data = await self._unwrap(resp)
        return data if isinstance(data, dict) else {"records": data or [], "total": 0}

    async def get_document(self, doc_id: int) -> dict[str, Any]:
        resp = await self._client().get(f"{self._base}/api/documents/{doc_id}")
        data = await self._unwrap(resp)
        if not data:
            raise HTTPException(status_code=404, detail="知识不存在")
        return data

    async def create_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client().post(f"{self._base}/api/documents", json=payload)
        data = await self._unwrap(resp)
        if not data:
            raise HTTPException(status_code=502, detail="ada-memory 创建原文失败")
        return data

    async def update_document(self, doc_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client().put(f"{self._base}/api/documents/{doc_id}", json=payload)
        return await self._unwrap(resp)

    async def start_update(
        self,
        doc_id: int,
        *,
        update_mode: str = "REPLACE_DOCUMENT",
        expire_slice_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """从已发布原文发起更新草稿。"""
        body: dict[str, Any] = {"updateMode": (update_mode or "REPLACE_DOCUMENT").strip()}
        if expire_slice_ids:
            body["expireSliceIds"] = [int(x) for x in expire_slice_ids]
        resp = await self._client().post(
            f"{self._base}/api/documents/{int(doc_id)}/start-update",
            json=body,
        )
        data = await self._unwrap(resp)
        if not data or data.get("id") is None:
            raise HTTPException(status_code=502, detail="ada-memory start-update 失败")
        return data

    async def save_slices(self, doc_id: int, slices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        resp = await self._client().put(
            f"{self._base}/api/documents/{doc_id}/slices",
            json={"slices": slices},
        )
        return (await self._unwrap(resp)) or []

    async def suggest_slices(
        self,
        doc_id: int,
        *,
        force: bool = True,
        orientation: str | None = "BOTH",
        slice_rule: str | None = None,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {}
        if orientation:
            body["orientation"] = orientation
        rule = (slice_rule or "").strip()
        if rule:
            body["sliceRule"] = rule
        resp = await self._client().post(
            f"{self._base}/api/documents/{doc_id}/suggest-slices",
            params={"force": str(force).lower()},
            json=body,
        )
        return (await self._unwrap(resp)) or []

    async def publish(self, doc_id: int) -> dict[str, Any]:
        resp = await self._client().post(f"{self._base}/api/documents/{doc_id}/publish")
        return await self._unwrap(resp)

    async def unpublish(self, doc_id: int) -> dict[str, Any]:
        resp = await self._client().post(f"{self._base}/api/documents/{doc_id}/unpublish")
        return await self._unwrap(resp)

    async def sync_vector(self, doc_id: int) -> dict[str, Any]:
        resp = await self._client().post(f"{self._base}/api/documents/{doc_id}/sync-vector")
        return await self._unwrap(resp)

    async def delete_document(self, doc_id: int) -> None:
        resp = await self._client().delete(f"{self._base}/api/documents/{doc_id}")
        await self._unwrap(resp)

    async def search(
        self,
        *,
        query: str,
        product_name: str,
        top_k: int = 5,
        kinds: str | None = "SLICE",
        document_ids: list[int] | None = None,
        category_id: int | None = None,
        category_code: str | None = None,
        rewrite: bool = True,
        hydrate_body: bool = True,
        include_body: bool = False,
        title_query: str | None = None,
        summary_query: str | None = None,
        fts_query: str | None = None,
    ) -> dict[str, Any]:
        """调用 GET /api/search。

        rewrite=False 时跳过 LLM/规则改写，适合表名等精确检索。
        include_body 默认 False（问数暂不传）：需要时再显式打开。
        search 默认只有标题与摘要；hydrate_body=True 时再 get_knowledge 补正文。
        """
        params: dict[str, Any] = {
            "q": query,
            "productName": product_name,
            "topK": top_k,
            "rewrite": str(rewrite).lower(),
        }
        if kinds:
            params["kinds"] = kinds
        if category_id is not None:
            params["categoryId"] = category_id
        code = (category_code or "").strip()
        if code:
            params["categoryCode"] = code
        if document_ids is not None:
            params["documentIds"] = ",".join(str(int(x)) for x in document_ids)
        if include_body:
            params["includeBody"] = "true"
        tq = (title_query or "").strip()
        sq = (summary_query or "").strip()
        fq = (fts_query or "").strip()
        if tq:
            params["titleQuery"] = tq
        if sq:
            # 与 memory descriptionQuery 对齐；服务端仍兼容 summaryQuery
            params["descriptionQuery"] = sq
            params["summaryQuery"] = sq
        if fq:
            params["ftsQuery"] = fq
        from dbc_askdata.clients.retry import with_one_retry

        async def _once() -> dict[str, Any]:
            client = self._client()
            resp = await client.get(f"{self._base}/api/search", params=params)
            data = await self._unwrap(resp)
            result = data if isinstance(data, dict) else {"units": data or []}
            if hydrate_body:
                result["units"] = await self._hydrate_units(client, result.get("units"))
            return result

        return await with_one_retry("ada-memory search", _once)

    async def search_tables(
        self,
        *,
        product_name: str,
        document_ids: list[int] | None = None,
        category_code: str | None = None,
        top_k: int = 10,
        title_query: str | None = None,
        description_query: str | None = None,
        body_summary_query: str | None = None,
        fts_query: str | None = None,
        graph_id: int | None = None,
        rewrite: bool = False,
    ) -> dict[str, Any]:
        """POST /api/search/tables：表语义找表（含邻接展开与表关系）。"""
        payload: dict[str, Any] = {
            "productName": product_name,
            "topK": int(top_k),
            "rewrite": bool(rewrite),
        }
        if document_ids is not None:
            payload["documentIds"] = [int(x) for x in document_ids]
        code = (category_code or "").strip()
        if code:
            payload["categoryCode"] = code
        tq = (title_query or "").strip()
        dq = (description_query or "").strip()
        bq = (body_summary_query or "").strip()
        fq = (fts_query or "").strip()
        if tq:
            payload["titleQuery"] = tq
        if dq:
            payload["descriptionQuery"] = dq
        if bq:
            payload["bodySummaryQuery"] = bq
        if fq:
            payload["ftsQuery"] = fq
        if graph_id is not None:
            payload["graphId"] = int(graph_id)

        from dbc_askdata.clients.retry import with_one_retry

        async def _once() -> dict[str, Any]:
            resp = await self._client().post(f"{self._base}/api/search/tables", json=payload)
            data = await self._unwrap(resp)
            return data if isinstance(data, dict) else {"tables": data or [], "tableRelations": []}

        return await with_one_retry("ada-memory search_tables", _once)

    async def list_table_relations(
        self,
        *,
        graph_id: int,
        table: str,
        max_depth: int = 1,
        limit: int = 50,
    ) -> dict[str, Any]:
        """POST /api/search/table-relations：按单表查图谱邻接，返回与 search/tables 相同的 tableRelations。"""
        payload = {
            "graphId": int(graph_id),
            "table": table.strip(),
            "maxDepth": int(max_depth),
            "limit": int(limit),
        }
        from dbc_askdata.clients.retry import with_one_retry

        async def _once() -> dict[str, Any]:
            resp = await self._client().post(f"{self._base}/api/search/table-relations", json=payload)
            data = await self._unwrap(resp)
            return data if isinstance(data, dict) else {"table": table, "tableRelations": []}

        return await with_one_retry("ada-memory table-relations", _once)

    async def category_id(self, code: str) -> int:
        """按分类编码取 id。问数写入原文时带上该分类。"""
        want = (code or "").strip().upper()
        resp = await self._client().get(f"{self._base}/api/categories/tree")
        data = await self._unwrap(resp)

        def walk(nodes) -> int | None:
            if not isinstance(nodes, list):
                return None
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                if str(node.get("code") or "").strip().upper() == want and node.get("id") is not None:
                    return int(node["id"])
                found = walk(node.get("children"))
                if found is not None:
                    return found
            return None

        found = walk(data)
        if found is None:
            raise HTTPException(status_code=502, detail=f"知识分类不存在: {want}")
        return found

    async def ensure_category(self, code: str, *, name: str | None = None) -> int:
        """分类不存在则创建；已存在返回 id。"""
        want = (code or "").strip().upper()
        if not want:
            raise HTTPException(status_code=400, detail="category code 为空")
        try:
            return await self.category_id(want)
        except HTTPException as ex:
            if ex.status_code != 502:
                raise
        label = (name or want).strip() or want
        resp = await self._client().post(
            f"{self._base}/api/categories",
            json={"code": want, "name": label, "sortNo": 90},
        )
        data = await self._unwrap(resp)
        if isinstance(data, dict) and data.get("id") is not None:
            return int(data["id"])
        # 并发创建时可能已存在
        return await self.category_id(want)

    async def get_unit(
        self,
        kind: str,
        unit_id: int,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """对应 MCP get_knowledge：按 kind + refId 取单元详情（含正文）。"""
        kind_s = (kind or "").strip().upper() or "SLICE"

        async def _get(c: httpx.AsyncClient) -> dict[str, Any]:
            resp = await c.get(f"{self._base}/api/units/{kind_s}/{int(unit_id)}")
            data = await self._unwrap(resp)
            if not data:
                raise HTTPException(status_code=404, detail="知识单元不存在")
            return data

        return await _get(client or self._client())

    async def _hydrate_units(
        self,
        client: httpx.AsyncClient,
        units_raw: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(units_raw, list):
            return []

        async def _one(raw: Any) -> dict[str, Any] | None:
            if not isinstance(raw, dict):
                return None
            item: dict[str, Any] = {
                "kind": parse_unit_kind(raw),
                "refId": parse_unit_ref_id(raw),
                "documentId": raw.get("documentId")
                if raw.get("documentId") is not None
                else raw.get("document_id"),
                "title": raw.get("title"),
                "summary": raw.get("summary"),
                "score": raw.get("score"),
                "body": raw.get("body"),
            }
            if str(item.get("body") or "").strip():
                return item
            ref_id = item.get("refId")
            if ref_id is None:
                log.warning(
                    "search 命中无 refId，跳过 get_knowledge kind=%s title=%s",
                    item.get("kind"),
                    item.get("title"),
                )
                return item
            try:
                detail = await self.get_unit(str(item["kind"]), int(ref_id), client=client)
                return merge_unit_detail(item, detail)
            except Exception:
                log.error(
                    "get_knowledge 拉取正文失败 kind=%s refId=%s",
                    item.get("kind"),
                    ref_id,
                    exc_info=True,
                )
                return item

        hydrated = await asyncio.gather(*[_one(u) for u in units_raw])
        return [u for u in hydrated if isinstance(u, dict)]
