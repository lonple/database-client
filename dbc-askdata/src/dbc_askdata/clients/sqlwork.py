from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from dbc_askdata.config import Settings


class SqlworkClient:
    """仅供 Tool Handler / WorkflowRunner 调用；禁止暴露给 LLM。"""

    def __init__(
        self,
        settings: Settings,
        authorization: str,
        *,
        trace_id: str | None = None,
    ) -> None:
        self._base = settings.sqlwork_base_url.rstrip("/")
        self._timeout = settings.sqlwork_timeout_seconds
        self._authorization = authorization
        self._trace_id = (trace_id or "").strip() or None

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": self._authorization, "Accept": "application/json"}
        if self._trace_id:
            headers["X-Trace-Id"] = self._trace_id
        return headers

    async def _unwrap(self, resp: httpx.Response) -> Any:
        try:
            body = resp.json()
        except Exception as ex:
            raise HTTPException(status_code=502, detail=f"sqlwork 响应非 JSON: {resp.status_code}") from ex
        if resp.status_code >= 400:
            msg = body.get("message") if isinstance(body, dict) else None
            raise HTTPException(status_code=resp.status_code, detail=msg or f"sqlwork HTTP {resp.status_code}")
        if isinstance(body, dict) and "data" in body:
            # 对齐平台 ApiResponse：code!=0 或 success=false 时抛业务错误
            if body.get("success") is False or (
                body.get("code") is not None and int(body.get("code") or 0) != 0
            ):
                raise HTTPException(status_code=400, detail=body.get("message") or "sqlwork 业务失败")
            return body.get("data")
        return body

    @staticmethod
    def ensure_execute_ok(data: Any) -> dict[str, Any]:
        """sqlwork /execute 在语句失败时仍可能 HTTP 200，需检查 statements[].success。"""
        if not isinstance(data, dict):
            return {}
        if data.get("stoppedOnError") is True or data.get("stopped_on_error") is True:
            stmts = data.get("statements") or []
            msg = data.get("message") or "SQL 执行失败"
            for s in stmts:
                if isinstance(s, dict) and s.get("success") is False:
                    msg = s.get("message") or msg
                    break
            raise HTTPException(status_code=400, detail=str(msg))
        stmts = data.get("statements")
        if isinstance(stmts, list) and stmts:
            for s in stmts:
                if isinstance(s, dict) and s.get("success") is False:
                    raise HTTPException(
                        status_code=400,
                        detail=str(s.get("message") or data.get("message") or "SQL 执行失败"),
                    )
        return data

    async def list_connections(self, workspace_id: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base}/workspaces/{workspace_id}/connections",
                headers=self._headers(),
            )
            data = await self._unwrap(resp)
            return data or []

    async def list_databases(self, workspace_id: int, connection_id: int) -> list[str]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base}/meta/databases",
                params={"workspaceId": workspace_id, "connectionId": connection_id},
                headers=self._headers(),
            )
            return (await self._unwrap(resp)) or []

    async def list_schemas(self, workspace_id: int, connection_id: int, database: str | None = None) -> list[str]:
        params: dict[str, Any] = {"workspaceId": workspace_id, "connectionId": connection_id}
        if database:
            params["database"] = database
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}/meta/schemas", params=params, headers=self._headers())
            return (await self._unwrap(resp)) or []

    async def list_tables(
        self,
        workspace_id: int,
        connection_id: int,
        *,
        database: str | None = None,
        schema: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "workspaceId": workspace_id,
            "connectionId": connection_id,
            "page": page,
            "size": size,
        }
        if database:
            params["database"] = database
        if schema:
            params["schema"] = schema
        if keyword:
            params["keyword"] = keyword
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}/meta/tables", params=params, headers=self._headers())
            return (await self._unwrap(resp)) or {"items": [], "total": 0}

    async def list_columns(
        self,
        workspace_id: int,
        connection_id: int,
        *,
        table: str,
        database: str | None = None,
        schema: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "workspaceId": workspace_id,
            "connectionId": connection_id,
            "table": table,
        }
        if database:
            params["database"] = database
        if schema:
            params["schema"] = schema
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{self._base}/meta/columns", params=params, headers=self._headers())
            return (await self._unwrap(resp)) or []

    async def execute(
        self,
        *,
        workspace_id: int,
        connection_id: int,
        sql: str,
        max_rows: int | None = None,
        database: str | None = None,
        schema: str | None = None,
        cancel_token: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "workspaceId": workspace_id,
            "connectionId": connection_id,
            "sql": sql,
        }
        if max_rows is not None:
            body["maxRows"] = max_rows
        if database:
            body["database"] = database
        if schema:
            body["schema"] = schema
        if cancel_token:
            body["cancelToken"] = cancel_token
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base}/execute", json=body, headers=self._headers())
            return self.ensure_execute_ok(await self._unwrap(resp))

    async def cancel(self, cancel_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base}/execute/cancel",
                json={"cancelToken": cancel_token},
                headers=self._headers(),
            )
            return (await self._unwrap(resp)) or {}
