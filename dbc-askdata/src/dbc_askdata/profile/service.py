from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB

from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.session import Base
from dbc_askdata.tools.registry import ToolGateway

log = logging.getLogger(__name__)
_SCHEMA = get_settings().database_schema


class AskColumnProfileCache(Base):
    __tablename__ = "ask_column_profile_cache"
    __table_args__ = {"schema": _SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    connection_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    database_name: Mapped[str | None] = mapped_column(String(256))
    schema_name: Mapped[str | None] = mapped_column(String(256))
    table_name: Mapped[str] = mapped_column(String(256), nullable=False)
    column_name: Mapped[str] = mapped_column(String(256), nullable=False)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfileService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_or_compute(
        self,
        session: AsyncSession,
        gateway: ToolGateway,
        *,
        workspace_id: int,
        connection_id: int,
        table: str,
        column: str,
        database: str | None,
        schema: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        q = await session.execute(
            select(AskColumnProfileCache).where(
                AskColumnProfileCache.workspace_id == workspace_id,
                AskColumnProfileCache.connection_id == connection_id,
                AskColumnProfileCache.table_name == table,
                AskColumnProfileCache.column_name == column,
                AskColumnProfileCache.database_name == database,
                AskColumnProfileCache.schema_name == schema,
                AskColumnProfileCache.expires_at > now,
            )
        )
        hit = q.scalar_one_or_none()
        if hit:
            return {"cached": True, "profile": hit.profile_json}

        try:
            raw = await gateway.invoke(
                "get_column_profile",
                {
                    "workspace_id": workspace_id,
                    "connection_id": connection_id,
                    "table": table,
                    "column": column,
                    "database": database,
                    "schema": schema,
                },
            )
        except Exception:
            log.warning("列画像计算失败，降级为空画像", exc_info=True)
            return {"cached": False, "degraded": True, "profile": {"error": "profile_timeout_or_fail"}}

        row = AskColumnProfileCache(
            workspace_id=workspace_id,
            connection_id=connection_id,
            database_name=database,
            schema_name=schema,
            table_name=table,
            column_name=column,
            profile_json=raw if isinstance(raw, dict) else {"raw": raw},
            expires_at=now + timedelta(seconds=self._settings.profile_cache_ttl_seconds),
        )
        session.add(row)
        try:
            await session.commit()
        except Exception:
            log.warning("列画像缓存写入失败", exc_info=True)
            await session.rollback()
        return {"cached": False, "profile": row.profile_json}
