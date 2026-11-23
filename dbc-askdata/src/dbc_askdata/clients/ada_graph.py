# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)


class AdaGraphClient:
    """旁路调用 ada-graph：图谱列表、两表 JOIN 最短路径。"""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.ada_graph_base_url.rstrip("/")
        self._timeout = settings.ada_graph_timeout_seconds

    def _client(self):
        from dbc_askdata.clients.downstream_auth import AuthedHttp
        from dbc_askdata.httpx_pool import shared_async_client

        return AuthedHttp(shared_async_client("ada-graph", timeout=self._timeout, trust_env=False))

    async def _unwrap(self, resp: httpx.Response) -> Any:
        try:
            body = resp.json()
        except Exception as ex:
            log.error(
                "ada-graph 响应非 JSON url=%s status=%s body=%s",
                str(resp.request.url),
                resp.status_code,
                (resp.text or "")[:300],
                exc_info=True,
            )
            raise HTTPException(
                status_code=502, detail=f"ada-graph 响应非 JSON: {resp.status_code}"
            ) from ex
        if resp.status_code >= 400:
            msg = body.get("message") if isinstance(body, dict) else None
            raise HTTPException(
                status_code=resp.status_code,
                detail=msg or f"ada-graph HTTP {resp.status_code}",
            )
        if isinstance(body, dict) and "code" in body:
            code = body.get("code")
            if code not in (0, "0", None):
                raise HTTPException(
                    status_code=502,
                    detail=str(body.get("message") or f"ada-graph code={code}"),
                )
            return body.get("data")
        return body

    async def list_graphs(
        self,
        *,
        keyword: str | None = None,
        product_name: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if keyword:
            params["keyword"] = keyword
        if product_name:
            params["productName"] = product_name
        resp = await self._client().get(f"{self._base}/api/graphs", params=params or None)
        data = await self._unwrap(resp)
        if data is None:
            return []
        if not isinstance(data, list):
            raise HTTPException(status_code=502, detail="ada-graph 图谱列表格式错误")
        return [x for x in data if isinstance(x, dict)]

    async def resolve_id(self, code: str | None = None) -> int | None:
        """按图谱编码取 id。不存在时返回 None，不中断问数。"""
        from dbc_askdata.config import get_settings

        graph_code = (code or get_settings().graph_code or "default").strip()
        if not graph_code:
            return None
        resp = await self._client().get(f"{self._base}/api/graphs/by-code/{graph_code}")
        if resp.status_code == 404:
            return None
        data = await self._unwrap(resp)
        if isinstance(data, dict) and data.get("id") is not None:
            return int(data["id"])
        return None

    async def get_graph(self, graph_id: int) -> dict[str, Any]:
        resp = await self._client().get(f"{self._base}/api/graphs/{int(graph_id)}")
        data = await self._unwrap(resp)
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="ada-graph 图谱详情格式错误")
        return data

    async def table_join_path(
        self,
        *,
        graph_id: int,
        from_table: str,
        to_table: str,
        max_depth: int = 6,
    ) -> dict[str, Any]:
        payload = {
            "fromTable": from_table,
            "toTable": to_table,
            "maxDepth": max_depth,
        }
        resp = await self._client().post(
            f"{self._base}/api/graphs/{int(graph_id)}/table-join-path",
            json=payload,
        )
        data = await self._unwrap(resp)
        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="ada-graph table-join-path 格式错误")
        return data
