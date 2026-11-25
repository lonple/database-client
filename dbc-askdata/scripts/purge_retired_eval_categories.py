"""Remove retired evaluation cases and history using one transaction."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from dbc_askdata.config import get_settings
from dbc_askdata.eval.cleanup import purge_removed_categories


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default=get_settings().database_url)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    engine = create_async_engine(args.dsn)
    try:
        async with AsyncSession(engine) as session:
            result = await purge_removed_categories(session)
            if args.dry_run:
                await session.rollback()
            else:
                await session.commit()
            print({**result, "dryRun": args.dry_run})
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
