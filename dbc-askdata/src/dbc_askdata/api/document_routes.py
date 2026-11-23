from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata import main as app_main
from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.models import AskDocument
from dbc_askdata.db.session import get_session
from dbc_askdata.documents import ConvertError
from dbc_askdata.documents.store import FileStore
from dbc_askdata.documents.validate import validate_upload
from dbc_askdata.documents.worker import schedule_convert
from dbc_askdata.observability.trace import get_trace_id
from dbc_askdata.security.auth import LoginUser, require_permission

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

_ASSET_NAME = re.compile(r"^[\w.\-]{1,180}$")


class DocumentPatch(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    markdown: str | None = None


def _vo(row: AskDocument) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "sourceFormat": row.source_format,
        "sourceFilename": row.source_filename,
        "pipeline": row.pipeline,
        "convertStatus": row.convert_status,
        "convertError": row.convert_error,
        "markdown": row.markdown,
        "markdownEdited": row.markdown_edited,
        "knowledgeDocumentId": row.knowledge_document_id,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


async def _owned(
    session: AsyncSession, doc_id: int, user: LoginUser
) -> AskDocument:
    row = await session.get(AskDocument, doc_id)
    if row is None or row.deleted or row.owner_user_id != int(user.user_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return row


async def _emit(
    *,
    action: str,
    user: LoginUser,
    doc_id: int,
    trace_id: str,
    result: str = "SUCCESS",
    fail_reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    if not app_main.audit_client:
        return
    await app_main.audit_client.emit_biz(
        action=action,
        resource_type="ask_document",
        resource_id=str(doc_id),
        operator_user_id=int(user.user_id),
        operator_username=user.username,
        result=result,
        fail_reason=fail_reason,
        details=details,
        trace_id=trace_id,
    )


@router.get("")
async def list_documents(
    q: str | None = None,
    source_format: str | None = Query(default=None, alias="sourceFormat"),
    convert_status: str | None = Query(default=None, alias="convertStatus"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(AskDocument).where(
        AskDocument.deleted.is_(False),
        AskDocument.owner_user_id == int(user.user_id),
    )
    if (q or "").strip():
        stmt = stmt.where(AskDocument.name.ilike(f"%{q.strip()}%"))
    if source_format:
        stmt = stmt.where(AskDocument.source_format == source_format.lower())
    if convert_status:
        stmt = stmt.where(AskDocument.convert_status == convert_status.upper())
    stmt = stmt.order_by(AskDocument.updated_at.desc()).limit(200)
    rows = (await session.execute(stmt)).scalars().all()
    return ApiResponse.ok([_vo(r) for r in rows])


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    trace_id: str = Depends(get_trace_id),
):
    filename = file.filename or "unnamed"
    data = await file.read()
    store = FileStore(settings)
    display = (name or "").strip() or Path(filename).stem
    row = AskDocument(
        owner_user_id=int(user.user_id),
        name=display[:256],
        source_format="bin",
        source_filename=filename[:512],
        source_relpath="pending",
        pipeline="DOCUMENT",
        convert_status="QUEUED",
    )
    session.add(row)
    await session.flush()
    dest = store.source_path(int(user.user_id), int(row.id), "bin")
    try:
        pipeline, fmt = validate_upload(
            filename=filename, data=data, dest=dest, settings=settings
        )
    except ConvertError as ex:
        dest.unlink(missing_ok=True)
        await session.rollback()
        raise HTTPException(status_code=400, detail=ex.message) from ex
    final = store.source_path(int(user.user_id), int(row.id), fmt)
    if dest != final:
        dest.replace(final)
    row.source_format = fmt
    row.pipeline = pipeline
    row.source_relpath = store.relpath(final)
    await session.commit()
    await session.refresh(row)
    await _emit(action="document.upload", user=user, doc_id=int(row.id), trace_id=trace_id)
    schedule_convert(int(row.id))
    return ApiResponse.ok(_vo(row))


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    row = await _owned(session, doc_id, user)
    return ApiResponse.ok(_vo(row))


@router.patch("/{doc_id}")
async def patch_document(
    doc_id: int,
    body: DocumentPatch,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    row = await _owned(session, doc_id, user)
    if body.name is not None:
        n = body.name.strip()
        if not n:
            raise HTTPException(status_code=400, detail="名称不能为空")
        row.name = n[:256]
    if body.markdown is not None:
        row.markdown = body.markdown
        row.markdown_edited = True
    await session.commit()
    await session.refresh(row)
    return ApiResponse.ok(_vo(row))


@router.post("/{doc_id}/replace")
async def replace_document(
    doc_id: int,
    file: UploadFile = File(...),
    confirm_overwrite: str = Form(default="false", alias="confirmOverwrite"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    trace_id: str = Depends(get_trace_id),
):
    row = await _owned(session, doc_id, user)
    overwrite = confirm_overwrite.strip().lower() in ("1", "true", "yes", "on")
    if row.markdown_edited and not overwrite:
        raise HTTPException(status_code=409, detail="正文已修改，替换将覆盖 Markdown，请确认")
    filename = file.filename or "unnamed"
    data = await file.read()
    store = FileStore(settings)
    tmp = store.source_path(int(user.user_id), doc_id, "upload")
    try:
        pipeline, fmt = validate_upload(
            filename=filename, data=data, dest=tmp, settings=settings
        )
    except ConvertError as ex:
        raise HTTPException(status_code=400, detail=ex.message) from ex
    final = store.source_path(int(user.user_id), doc_id, fmt)
    if tmp != final:
        tmp.replace(final)
    store.wipe_assets(int(user.user_id), doc_id)
    row.source_format = fmt
    row.pipeline = pipeline
    row.source_filename = filename[:512]
    row.source_relpath = store.relpath(final)
    row.convert_status = "QUEUED"
    row.convert_error = None
    await session.commit()
    await _emit(action="document.replace", user=user, doc_id=doc_id, trace_id=trace_id)
    schedule_convert(doc_id)
    await session.refresh(row)
    return ApiResponse.ok(_vo(row))


@router.post("/{doc_id}/retry")
async def retry_document(
    doc_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    row = await _owned(session, doc_id, user)
    if row.convert_status == "RUNNING":
        raise HTTPException(status_code=409, detail="正在转换")
    row.convert_status = "QUEUED"
    row.convert_error = None
    await session.commit()
    schedule_convert(doc_id)
    await session.refresh(row)
    return ApiResponse.ok(_vo(row))


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
    trace_id: str = Depends(get_trace_id),
):
    row = await _owned(session, doc_id, user)
    row.deleted = True
    await session.commit()
    FileStore(settings).remove_doc(int(user.user_id), doc_id)
    await _emit(action="document.delete", user=user, doc_id=doc_id, trace_id=trace_id)
    return ApiResponse.ok({"id": doc_id, "deleted": True})


@router.get("/{doc_id}/source")
async def download_source(
    doc_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
):
    row = await _owned(session, doc_id, user)
    store = FileStore(settings)
    try:
        path = store.abs_from_rel(row.source_relpath)
    except ValueError as ex:
        raise HTTPException(status_code=404, detail="原件不存在") from ex
    if not path.is_file():
        raise HTTPException(status_code=404, detail="原件不存在")
    return FileResponse(path, filename=row.source_filename)


@router.get("/{doc_id}/assets/{name}")
async def get_asset(
    doc_id: int,
    name: str,
    user: LoginUser = Depends(require_permission("askdata.use")),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
):
    if not _ASSET_NAME.match(name) or ".." in name:
        raise HTTPException(status_code=400, detail="非法文件名")
    row = await _owned(session, doc_id, user)
    path = FileStore(settings).assets_dir(int(user.user_id), doc_id) / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(path)
