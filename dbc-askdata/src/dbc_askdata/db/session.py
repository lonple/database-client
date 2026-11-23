from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from dbc_askdata.config import get_settings

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_pool_size = int(_settings.db_pool_size)
_max_overflow = int(_settings.db_max_overflow)
_pool_timeout = float(_settings.db_pool_timeout_seconds)
engine = create_async_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=_pool_timeout,
    pool_recycle=1800,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
log.info(
    "DB pool pool_size=%s max_overflow=%s pool_timeout=%ss (max_conn≈%s)",
    _pool_size,
    _max_overflow,
    _pool_timeout,
    _pool_size + _max_overflow,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
