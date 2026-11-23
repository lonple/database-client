# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.clients.ada_graph import AdaGraphClient
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.models import AskTableRelationBinding
from dbc_askdata.db.session import get_session
from dbc_askdata.security.auth import LoginUser, require_permission

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/table-relation-bindings", tags=["table-relations"])


class BindingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    workspace_id: int | None = Field(default=None, alias="workspaceId")
    connection_id: int = Field(..., alias="connectionId")
    connection_name: str | None = Field(default=None, alias="connectionName", max_length=256)
    database: str | None = Field(default=None, max_length=256)
    schema_name: str | None = Field(default=None, alias="schema", max_length=256)
    graph_id: int = Field(..., alias="graphId")
    graph_name: str | None = Field(default=None, alias="graphName", max_length=256)
    remark: str | None = Field(default=None, max_length=512)

    model_config = {"populate_by_name": True}


class BindingPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    workspace_id: int | None = Field(default=None, alias="workspaceId")
    connection_id: int | None = Field(default=None, alias="connectionId")
    connection_name: str | None = Field(default=None, alias="connectionName", max_length=256)
    database: str | None = Field(default=None, max_length=256)
    schema_name: str | None = Field(default=None, alias="schema", max_length=256)
    graph_id: int | None = Field(default=None, alias="graphId")
    graph_name: str | None = Field(default=None, alias="graphName", max_length=256)
    remark: str | None = Field(default=None, max_length=512)

    model_config = {"populate_by_name": True}


def _norm(s: str | None) -> str | None:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _vo(row: AskTableRelationBinding) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "workspaceId": row.workspace_id,
        "connectionId": row.connection_id,
        "connectionName": row.connection_name,
        "database": row.database_name,
        "schema": row.schema_name,
        "graphId": row.graph_id,
        "graphName": row.graph_name,
        "remark": row.remark,
        "ownerUserId": row.owner_user_id,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


async def _owned(
    session: AsyncSession, binding_id: int, user: LoginUser
) -> AskTableRelationBinding:
    row = await session.get(AskTableRelationBinding, binding_id)
    if row is None or row.deleted or row.owner_user_id != int(user.user_id):
        raise HTTPException(status_code=404, detail="库表关系绑定不存在")
    return row


async def find_binding_for_scope(
    session: AsyncSession,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
) -> AskTableRelationBinding | None:
    """按连接/库/模式解析绑定（问数工具用，不按 owner 过滤）。"""
    db = _norm(database)
    sch = _norm(schema)
    q = (
        select(AskTableRelationBinding)
        .where(
            AskTableRelationBinding.deleted.is_(False),
            AskTableRelationBinding.connection_id == int(connection_id),
        )
        .order_by(AskTableRelationBinding.id.desc())
    )
    rows = (await session.execute(q)).scalars().all()
    for row in rows:
        if _norm(row.database_name) == db and _norm(row.schema_name) == sch:
            return row
    return None


@router.get("/graphs")
async def list_ada_graphs(
    keyword: str | None = Query(default=None),
    product_name: str | None = Query(default=None, alias="productName"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    _ = user
    client = AdaGraphClient(settings)
    graphs = await client.list_graphs(keyword=keyword, product_name=product_name)
    items = [
        {
            "id": g.get("id"),
            "name": g.get("name"),
            "summary": g.get("summary"),
            "productName": g.get("productName"),
            "categoryId": g.get("categoryId"),
        }
        for g in graphs
        if g.get("id") is not None
    ]
    return ApiResponse.ok(items)


@router.get("")
async def list_bindings(
    q: str | None = Query(default=None),
    connection_id: int | None = Query(default=None, alias="connectionId"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse:
    stmt = select(AskTableRelationBinding).where(
        AskTableRelationBinding.deleted.is_(False),
        AskTableRelationBinding.owner_user_id == int(user.user_id),
    )
    if connection_id is not None:
        stmt = stmt.where(AskTableRelationBinding.connection_id == int(connection_id))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                AskTableRelationBinding.name.ilike(like),
                AskTableRelationBinding.graph_name.ilike(like),
            )
        )
    stmt = stmt.order_by(AskTableRelationBinding.id.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return ApiResponse.ok([_vo(r) for r in rows])


@router.get("/{binding_id}")
async def get_binding(
    binding_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse:
    row = await _owned(session, binding_id, user)
    return ApiResponse.ok(_vo(row))


@router.post("")
async def create_binding(
    body: BindingCreate,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    graph_id = int(body.graph_id)
    graph_name = _norm(body.graph_name)
    if not graph_name:
        try:
            g = await AdaGraphClient(settings).get_graph(graph_id)
            graph_name = str(g.get("name") or "") or None
        except Exception:
            log.warning("创建绑定时拉取图谱名失败 graph_id=%s", graph_id, exc_info=True)

    existing = await find_binding_for_scope(
        session,
        connection_id=int(body.connection_id),
        database=body.database,
        schema=body.schema_name,
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="该连接/库/模式已绑定图谱，请先编辑或删除原配置",
        )

    row = AskTableRelationBinding(
        name=body.name.strip(),
        workspace_id=body.workspace_id,
        connection_id=int(body.connection_id),
        connection_name=_norm(body.connection_name),
        database_name=_norm(body.database),
        schema_name=_norm(body.schema_name),
        graph_id=graph_id,
        graph_name=graph_name,
        remark=_norm(body.remark),
        owner_user_id=int(user.user_id),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ApiResponse.ok(_vo(row))


@router.patch("/{binding_id}")
async def patch_binding(
    binding_id: int,
    body: BindingPatch,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    row = await _owned(session, binding_id, user)
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "workspace_id" in data:
        row.workspace_id = data["workspace_id"]
    if "connection_id" in data and data["connection_id"] is not None:
        row.connection_id = int(data["connection_id"])
    if "connection_name" in data:
        row.connection_name = _norm(data.get("connection_name"))
    if "database" in data:
        row.database_name = _norm(data.get("database"))
    if "schema_name" in data:
        row.schema_name = _norm(data.get("schema_name"))
    if "remark" in data:
        row.remark = _norm(data.get("remark"))
    if "graph_id" in data and data["graph_id"] is not None:
        row.graph_id = int(data["graph_id"])
        if not data.get("graph_name"):
            try:
                g = await AdaGraphClient(settings).get_graph(row.graph_id)
                row.graph_name = str(g.get("name") or "") or row.graph_name
            except Exception:
                log.warning("更新绑定时拉取图谱名失败 graph_id=%s", row.graph_id, exc_info=True)
    if "graph_name" in data and data["graph_name"] is not None:
        row.graph_name = _norm(data.get("graph_name"))

    clash = await find_binding_for_scope(
        session,
        connection_id=row.connection_id,
        database=row.database_name,
        schema=row.schema_name,
    )
    if clash is not None and clash.id != row.id:
        raise HTTPException(
            status_code=409,
            detail="该连接/库/模式已绑定其它图谱配置",
        )

    await session.commit()
    await session.refresh(row)
    return ApiResponse.ok(_vo(row))


@router.delete("/{binding_id}")
async def delete_binding(
    binding_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse:
    row = await _owned(session, binding_id, user)
    row.deleted = True
    await session.commit()
    return ApiResponse.ok(None)


@router.post("/resolve-join-path")
async def resolve_join_path(
    body: dict[str, Any],
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    """调试/联调用：本地解析绑定后查两表 JOIN 路径。"""
    _ = user
    connection_id = int(body.get("connectionId") or body.get("connection_id") or 0)
    from_table = str(body.get("fromTable") or body.get("from_table") or "").strip()
    to_table = str(body.get("toTable") or body.get("to_table") or "").strip()
    database = body.get("database")
    schema = body.get("schema") or body.get("schema_name")
    if not connection_id or not from_table or not to_table:
        raise HTTPException(status_code=400, detail="需要 connectionId、fromTable、toTable")
    result = await query_table_join_for_scope(
        settings,
        session,
        connection_id=connection_id,
        database=database,
        schema=schema,
        from_table=from_table,
        to_table=to_table,
        max_depth=int(body.get("maxDepth") or 6),
    )
    return ApiResponse.ok(result)


async def query_table_join_for_scope(
    settings: Settings,
    session: AsyncSession,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    from_table: str,
    to_table: str,
    max_depth: int = 6,
) -> dict[str, Any]:
    """工具与 API 共用：本地绑图谱 → ada-graph 最短 JOIN 路径。"""
    binding = await find_binding_for_scope(
        session,
        connection_id=connection_id,
        database=database,
        schema=schema,
    )
    if binding is None:
        return {
            "bound": False,
            "message": "当前连接/库/模式未配置库表关系图谱",
            "connectionId": connection_id,
            "database": _norm(database),
            "schema": _norm(schema),
            "joins": [],
            "joinTexts": [],
        }
    path = await AdaGraphClient(settings).table_join_path(
        graph_id=int(binding.graph_id),
        from_table=from_table.strip(),
        to_table=to_table.strip(),
        max_depth=max_depth,
    )
    return {
        "bound": True,
        "bindingId": binding.id,
        "graphId": binding.graph_id,
        "graphName": binding.graph_name,
        "fromTable": path.get("fromTable") or from_table,
        "toTable": path.get("toTable") or to_table,
        "connected": bool(path.get("connected")),
        "path": path.get("path") or [],
        "pathLength": path.get("pathLength") or 0,
        "joins": path.get("joins") or [],
        "joinTexts": path.get("joinTexts") or [],
        "message": None
        if path.get("connected")
        else f"图谱中未找到 {from_table} 与 {to_table} 的关联路径",
    }
