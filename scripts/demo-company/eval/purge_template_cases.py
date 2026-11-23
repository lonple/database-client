#!/usr/bin/env python3
"""删除 askdata 中演示模板相关旧用例（TEMPLATE / company_eval_v2）。"""

from __future__ import annotations

import argparse
import asyncio

import asyncpg

DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN)
    args = ap.parse_args()
    conn = await asyncpg.connect(args.dsn)
    try:
        before = await conn.fetchval("SELECT count(*) FROM askdata.eval_case")
        tpl = await conn.fetchrow(
            "SELECT id, code FROM askdata.eval_template WHERE code = $1",
            "company_eval_v2",
        )
        # 任务快照里的 case 保留历史；只清模板用例表
        deleted = await conn.fetchval(
            """
            WITH d AS (
              DELETE FROM askdata.eval_case
              WHERE scope = 'TEMPLATE'
                 OR case_key LIKE 'TPL_%'
                 OR (template_id IS NOT NULL AND template_id = $1)
              RETURNING 1
            )
            SELECT count(*) FROM d
            """,
            tpl["id"] if tpl else None,
        )
        after = await conn.fetchval("SELECT count(*) FROM askdata.eval_case")
        print(f"template={tpl}")
        print(f"deleted={deleted} before={before} after={after}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
