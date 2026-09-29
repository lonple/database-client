from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

log = logging.getLogger(__name__)


def _strip_leading_comments(sql: str) -> str:
    """去掉语句前的 -- 行注释，避免整段被误判跳过。"""
    lines: list[str] = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


async def _run_sql_file(engine: AsyncEngine, schema: str, migration_file: Path) -> None:
    sql = migration_file.read_text(encoding="utf-8")
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        for stmt in sql.split(";"):
            piece = _strip_leading_comments(stmt)
            if not piece:
                continue
            if piece.upper().startswith("CREATE SCHEMA"):
                continue
            try:
                await conn.execute(text(piece))
            except Exception:
                log.warning("迁移语句执行失败 file=%s: %s", migration_file.name, piece[:120], exc_info=True)
                raise
    log.info("askdata schema 迁移完成: %s", migration_file.name)


async def ensure_schema(engine: AsyncEngine, schema: str, migrations_dir: Path) -> None:
    """启动时按文件名顺序执行 migrations/V*.sql（幂等）。"""
    files = sorted(migrations_dir.glob("V*.sql"))
    if not files:
        raise RuntimeError(f"未找到迁移文件: {migrations_dir}")
    for f in files:
        await _run_sql_file(engine, schema, f)
