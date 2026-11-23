# -*- coding: utf-8 -*-
"""问数知识绑定 API：连接/库/模式 → ada-memory 文档；正文维护在 ada-memory 控制台。"""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.clients.ada_memory import AdaMemoryClient
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.models import AskKnowledgeBinding
from dbc_askdata.db.session import get_session
from dbc_askdata.security.auth import LoginUser, require_permission

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-bindings", tags=["knowledge"])

KnowledgeCategory = Literal["GENERAL", "METADATA", "QUESTION"]


class BindingCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    workspace_id: int | None = Field(default=None, alias="workspaceId")
    connection_id: int = Field(..., alias="connectionId")
    connection_name: str | None = Field(default=None, alias="connectionName", max_length=256)
    database: str | None = Field(default=None, max_length=256)
    schema_name: str | None = Field(default=None, alias="schema", max_length=256)
    document_id: int = Field(..., alias="documentId")
    document_name: str | None = Field(default=None, alias="documentName", max_length=256)
    knowledge_category: KnowledgeCategory = Field(..., alias="knowledgeCategory")
    remark: str | None = Field(default=None, max_length=512)

    model_config = {"populate_by_name": True}


class BindingPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    workspace_id: int | None = Field(default=None, alias="workspaceId")
    connection_id: int | None = Field(default=None, alias="connectionId")
    connection_name: str | None = Field(default=None, alias="connectionName", max_length=256)
    database: str | None = Field(default=None, max_length=256)
    schema_name: str | None = Field(default=None, alias="schema", max_length=256)
    document_id: int | None = Field(default=None, alias="documentId")
    document_name: str | None = Field(default=None, alias="documentName", max_length=256)
    knowledge_category: KnowledgeCategory | None = Field(default=None, alias="knowledgeCategory")
    remark: str | None = Field(default=None, max_length=512)

    model_config = {"populate_by_name": True}


def _norm(s: str | None) -> str | None:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _vo(row: AskKnowledgeBinding) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "workspaceId": row.workspace_id,
        "connectionId": row.connection_id,
        "connectionName": row.connection_name,
        "database": row.database_name,
        "schema": row.schema_name,
        "documentId": row.document_id,
        "documentName": row.document_name,
        "knowledgeCategory": row.knowledge_category,
        "remark": row.remark,
        "ownerUserId": row.owner_user_id,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


async def _owned(
    session: AsyncSession, binding_id: int, user: LoginUser
) -> AskKnowledgeBinding:
    row = await session.get(AskKnowledgeBinding, binding_id)
    if row is None or row.deleted or row.owner_user_id != int(user.user_id):
        raise HTTPException(status_code=404, detail="知识绑定不存在")
    return row


async def find_binding_for_scope_doc(
    session: AsyncSession,
    *,
    connection_id: int,
    database: str | None,
    schema: str | None,
    document_id: int,
) -> AskKnowledgeBinding | None:
    db = _norm(database)
    sch = _norm(schema)
    q = (
        select(AskKnowledgeBinding)
        .where(
            AskKnowledgeBinding.deleted.is_(False),
            AskKnowledgeBinding.connection_id == int(connection_id),
            AskKnowledgeBinding.document_id == int(document_id),
        )
        .order_by(AskKnowledgeBinding.id.desc())
    )
    rows = (await session.execute(q)).scalars().all()
    for row in rows:
        if _norm(row.database_name) == db and _norm(row.schema_name) == sch:
            return row
    return None


@router.get("/documents")
async def list_ada_documents(
    status: str | None = Query(default=None),
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    """从 ada-memory 拉取知识文档列表，供绑定选择。"""
    _ = user
    client = AdaMemoryClient(settings)
    docs = await client.list_documents(status=status)
    items = [
        {
            "id": d.get("id"),
            "title": d.get("title"),
            "summary": d.get("summary"),
            "productName": d.get("productName"),
            "status": d.get("status"),
            "sourceType": d.get("sourceType"),
        }
        for d in docs
        if isinstance(d, dict) and d.get("id") is not None
    ]
    return ApiResponse.ok(items)


@router.get("")
async def list_bindings(
    q: str | None = Query(default=None),
    connection_id: int | None = Query(default=None, alias="connectionId"),
    knowledge_category: str | None = Query(default=None, alias="knowledgeCategory"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse:
    stmt = select(AskKnowledgeBinding).where(
        AskKnowledgeBinding.deleted.is_(False),
        AskKnowledgeBinding.owner_user_id == int(user.user_id),
    )
    if connection_id is not None:
        stmt = stmt.where(AskKnowledgeBinding.connection_id == int(connection_id))
    if knowledge_category:
        stmt = stmt.where(
            AskKnowledgeBinding.knowledge_category == knowledge_category.strip().upper()
        )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                AskKnowledgeBinding.name.ilike(like),
                AskKnowledgeBinding.document_name.ilike(like),
            )
        )
    stmt = stmt.order_by(AskKnowledgeBinding.id.desc())
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
    document_id = int(body.document_id)
    document_name = _norm(body.document_name)
    if not document_name:
        try:
            doc = await AdaMemoryClient(settings).get_document(document_id)
            document_name = str(doc.get("title") or "") or None
        except Exception:
            log.warning("创建绑定时拉取文档标题失败 document_id=%s", document_id, exc_info=True)

    existing = await find_binding_for_scope_doc(
        session,
        connection_id=int(body.connection_id),
        database=body.database,
        schema=body.schema_name,
        document_id=document_id,
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="该连接/库/模式已绑定此知识文档，请先编辑或删除原配置",
        )

    row = AskKnowledgeBinding(
        name=body.name.strip(),
        workspace_id=body.workspace_id,
        connection_id=int(body.connection_id),
        connection_name=_norm(body.connection_name),
        database_name=_norm(body.database),
        schema_name=_norm(body.schema_name),
        document_id=document_id,
        document_name=document_name,
        knowledge_category=str(body.knowledge_category).upper(),
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
    if "knowledge_category" in data and data["knowledge_category"] is not None:
        row.knowledge_category = str(data["knowledge_category"]).upper()
    if "document_id" in data and data["document_id"] is not None:
        row.document_id = int(data["document_id"])
        if not data.get("document_name"):
            try:
                doc = await AdaMemoryClient(settings).get_document(row.document_id)
                row.document_name = str(doc.get("title") or "") or row.document_name
            except Exception:
                log.warning(
                    "更新绑定时拉取文档标题失败 document_id=%s",
                    row.document_id,
                    exc_info=True,
                )
    if "document_name" in data and data["document_name"] is not None:
        row.document_name = _norm(data.get("document_name"))

    clash = await find_binding_for_scope_doc(
        session,
        connection_id=row.connection_id,
        database=row.database_name,
        schema=row.schema_name,
        document_id=row.document_id,
    )
    if clash is not None and clash.id != row.id:
        raise HTTPException(
            status_code=409,
            detail="该连接/库/模式已绑定其它同名知识文档配置",
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
