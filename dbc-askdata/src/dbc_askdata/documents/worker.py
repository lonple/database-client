from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import update

from dbc_askdata.config import get_settings
from dbc_askdata.db.models import AskDocument
from dbc_askdata.db.session import SessionLocal
from dbc_askdata.documents import ConvertError
from dbc_askdata.documents.converter import convert_file
from dbc_askdata.documents.store import FileStore

log = logging.getLogger(__name__)


async def reclaim_stale_jobs() -> None:
    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            update(AskDocument)
            .where(
                AskDocument.deleted.is_(False),
                AskDocument.convert_status.in_(("QUEUED", "RUNNING")),
            )
            .values(
                convert_status="FAILED",
                convert_error="服务重启或中断，请重试转换",
                updated_at=now,
            )
        )
        await session.commit()
        n = result.rowcount or 0
        if n:
            log.warning("文档转换悬挂任务已标记失败 count=%s", n)


def schedule_convert(doc_id: int) -> None:
    asyncio.create_task(_run_convert(doc_id), name=f"ask-doc-convert-{doc_id}")


async def _run_convert(doc_id: int) -> None:
    settings = get_settings()
    store = FileStore(settings)
    async with SessionLocal() as session:
        row = await session.get(AskDocument, doc_id)
        if row is None or row.deleted:
            return
        row.convert_status = "RUNNING"
        row.convert_error = None
        await session.commit()
        owner = row.owner_user_id
        rel = row.source_relpath
        pipeline = row.pipeline
        try:
            source = store.abs_from_rel(rel)
        except Exception:
            log.error("文档原件路径非法 id=%s rel=%s", doc_id, rel, exc_info=True)
            row.convert_status = "FAILED"
            row.convert_error = "原件路径无效"
            await session.commit()
            return
        assets = store.assets_dir(owner, doc_id)
        store.wipe_assets(owner, doc_id)
        assets = store.assets_dir(owner, doc_id)
        prefix = f"/dbc-askdata/api/documents/{doc_id}/assets"
        try:
            outcome = await asyncio.wait_for(
                asyncio.to_thread(
                    convert_file,
                    source=source,
                    pipeline=pipeline,
                    assets_dir=assets,
                    asset_url_prefix=prefix,
                    settings=settings,
                ),
                timeout=settings.document_convert_timeout_seconds,
            )
        except ConvertError as ex:
            row.convert_status = "FAILED"
            row.convert_error = ex.message
            await session.commit()
            return
        except TimeoutError:
            row.convert_status = "FAILED"
            row.convert_error = "转换超时"
            await session.commit()
            return
        except Exception as ex:
            log.error("文档转换未捕获异常 id=%s", doc_id, exc_info=True)
            row.convert_status = "FAILED"
            row.convert_error = f"转换失败: {ex}"
            await session.commit()
            return
        row.markdown = outcome.markdown
        row.markdown_from_convert = outcome.markdown
        row.markdown_edited = False
        row.convert_status = "SUCCESS"
        row.convert_error = None
        await session.commit()
