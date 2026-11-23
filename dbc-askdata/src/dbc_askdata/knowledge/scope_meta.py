from __future__ import annotations

import json
from typing import Any


def build_scope_marker(
    *,
    workspace_id: int,
    connection_id: int,
    database: str,
    schema: str | None,
    connection_name: str | None = None,
    db_type: str | None = None,
) -> str:
    """写入正文头部，供后续问数按连接/库/模式精准过滤。"""
    payload: dict[str, Any] = {
        "workspaceId": workspace_id,
        "connectionId": connection_id,
        "database": database,
        "schema": schema,
        "connectionName": connection_name or "",
        "dbType": db_type or "",
    }
    return f"<!--dbc-askdata-scope:{json.dumps(payload, ensure_ascii=False)}-->"


def attach_meta_scope(
    doc_body: str,
    *,
    workspace_id: int,
    connection_id: int,
    database: str,
    schema: str | None,
    connection_name: str | None = None,
    db_type: str | None = None,
) -> str:
    body = (doc_body or "").strip()
    marker = build_scope_marker(
        workspace_id=workspace_id,
        connection_id=connection_id,
        database=database,
        schema=schema,
        connection_name=connection_name,
        db_type=db_type,
    )
    if "<!--dbc-askdata-scope:" in body:
        return body
    scope_bits = [f"连接 {connection_name or connection_id}", f"库 `{database}`"]
    if schema:
        scope_bits.append(f"模式 `{schema}`")
    human = "> 作用域过滤（问数检索精准过滤）：" + " · ".join(scope_bits)
    return f"{marker}\n{human}\n\n{body}"


def parse_meta_scope(doc_body: str | None) -> dict[str, Any] | None:
    text = doc_body or ""
    start = text.find("<!--dbc-askdata-scope:")
    if start < 0:
        return None
    start += len("<!--dbc-askdata-scope:")
    end = text.find("-->", start)
    if end < 0:
        return None
    raw = text[start:end].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
