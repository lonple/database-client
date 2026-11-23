"""确保知识库分类 SQL_EX，并写入「关键字空格」示例原文（不分片、直接发布）。

默认走平台库 SQL（无需 JWT）。也可用 HTTP：
  .\\.venv\\Scripts\\python.exe scripts\\seed_sql_ex_knowledge.py --via http --token <jwt>
  .\\.venv\\Scripts\\python.exe scripts\\seed_sql_ex_knowledge.py --dsn postgresql+asyncpg://postgres:root@127.0.0.1:5432/postgres
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from dbc_askdata.clients.ada_memory import AdaMemoryClient  # noqa: E402
from dbc_askdata.clients.downstream_auth import (  # noqa: E402
    reset_downstream_authorization,
    set_downstream_authorization,
)
from dbc_askdata.config import Settings  # noqa: E402
from dbc_askdata.knowledge.sql_ex_knowledge import (  # noqa: E402
    SQL_EX_CATEGORY,
    SQL_EX_CATEGORY_NAME,
)

DOC_TITLE = "SQL关键字空格示例"
DOC_SUMMARY = "关键字与标识符之间必须有空格；禁止标识符与关键字粘连（语法示意，不含业务字段，不用 WITH）。"
DOC_BODY = """# SQL 关键字必须用空格分隔

这是**语法示意**，不涉及具体业务表/字段，也不使用 `WITH … AS`。
凡 `SELECT` / `FROM` / `JOIN` / `ON` / `WHERE` / `GROUP BY` / `ORDER BY` / `ASC` / `DESC` / `LIMIT`
等关键字，与前后标识符、右括号之间必须有空格或换行。

## 错误写法（禁止粘连）

- `colFROM` → 标识符与 FROM 粘在一起
- `tJOIN` → 表别名与 JOIN 粘在一起
- `idORDER` → 标识符与 ORDER 粘在一起
- `ASCLIMIT` → ASC 与 LIMIT 粘在一起
- `)WHERE` / `)GROUP` → 右括号与后续关键字粘在一起

```sql
SELECT a.x, b.yFROM schema.t1 aJOIN schema.t2 b
  ON a.id = b.fkWHERE a.flag = 1GROUP BY a.x, b.yORDER BY b.y DESC, a.x ASCLIMIT 50
```

## 正确写法

```sql
SELECT a.x, b.y
FROM schema.t1 a
JOIN schema.t2 b ON a.id = b.fk
WHERE a.flag = 1
GROUP BY a.x, b.y
ORDER BY b.y DESC, a.x ASC
LIMIT 50
```
"""


async def seed_via_db(dsn: str, *, force: bool) -> int:
    eng = create_async_engine(dsn)
    async with eng.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO knowledge.t_knowledge_category (name, code, path, sort_no)
                SELECT CAST(:name AS varchar), CAST(:code AS varchar), '/SQL_EX', 40
                WHERE NOT EXISTS (
                    SELECT 1 FROM knowledge.t_knowledge_category
                    WHERE code = CAST(:code AS varchar)
                )
                """
            ),
            {"name": SQL_EX_CATEGORY_NAME, "code": SQL_EX_CATEGORY},
        )
        await conn.execute(
            text(
                """
                UPDATE knowledge.t_knowledge_category
                SET path = '/' || id::text
                WHERE code = :code
                  AND (path IS NULL OR path = '/SQL_EX' OR path !~ '^/[0-9]+(/[0-9]+)*$')
                """
            ),
            {"code": SQL_EX_CATEGORY},
        )
        cat_id = (
            await conn.execute(
                text("SELECT id FROM knowledge.t_knowledge_category WHERE code = :code"),
                {"code": SQL_EX_CATEGORY},
            )
        ).scalar_one()
        print(f"category {SQL_EX_CATEGORY} id={cat_id}")

        existing_id = (
            await conn.execute(
                text(
                    """
                    SELECT id FROM knowledge.t_knowledge_document
                    WHERE category_id = :cid AND title = CAST(:title AS varchar) AND status = 'PUBLISHED'
                    ORDER BY id DESC LIMIT 1
                    """
                ),
                {"cid": cat_id, "title": DOC_TITLE},
            )
        ).scalar_one_or_none()
        if existing_id is not None:
            await conn.execute(
                text(
                    """
                    UPDATE knowledge.t_knowledge_document
                    SET body = CAST(:body AS text),
                        summary = CAST(:summary AS varchar),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": existing_id, "body": DOC_BODY, "summary": DOC_SUMMARY},
            )
            print(f"updated documentId={existing_id} title={DOC_TITLE}")
            await eng.dispose()
            return 0

        row = (
            await conn.execute(
                text(
                    """
                    INSERT INTO knowledge.t_knowledge_document (
                        title, product_name, orientation, source_type, body, status,
                        category_id, summary, created_by, vector_sync_status,
                        version_no, update_mode, expire_slice_ids, published_at
                    ) VALUES (
                        CAST(:title AS varchar), CAST(:product AS varchar), 'BOTH', 'SQL_EX',
                        CAST(:body AS text), 'PUBLISHED',
                        :cid, CAST(:summary AS varchar), 'seed_sql_ex_knowledge', 'NONE',
                        1, 'CREATE', '[]', NOW()
                    )
                    RETURNING id
                    """
                ),
                {
                    "title": DOC_TITLE,
                    "product": "dbc产品",
                    "body": DOC_BODY,
                    "cid": cat_id,
                    "summary": DOC_SUMMARY,
                },
            )
        ).scalar_one()
        await conn.execute(
            text(
                "UPDATE knowledge.t_knowledge_document SET lineage_id = id WHERE id = :id AND lineage_id IS NULL"
            ),
            {"id": row},
        )
        print(f"published documentId={row} title={DOC_TITLE}")
    await eng.dispose()
    return 0


async def seed_via_http(settings: Settings, token: str, *, force: bool) -> int:
    from dbc_askdata.knowledge.sql_ex_knowledge import load_sql_ex_knowledge

    tok = set_downstream_authorization(token)
    try:
        client = AdaMemoryClient(settings)
        cat_id = await client.ensure_category(SQL_EX_CATEGORY, name=SQL_EX_CATEGORY_NAME)
        print(f"category {SQL_EX_CATEGORY} id={cat_id}")
        existing = await load_sql_ex_knowledge(settings, ensure_category=False)
        if not force:
            for it in existing:
                if (it.get("title") or "").strip() == DOC_TITLE:
                    print(f"already exists documentId={it.get('documentId')} title={DOC_TITLE}")
                    return 0
        product = (settings.ada_memory_product_name or "dbc产品").strip() or "dbc产品"
        doc = await client.create_document(
            {
                "title": DOC_TITLE,
                "summary": DOC_SUMMARY,
                "productName": product,
                "orientation": "BOTH",
                "body": DOC_BODY,
                "sourceType": "SQL_EX",
                "categoryId": cat_id,
                "createdBy": "seed_sql_ex_knowledge",
                "updateMode": "CREATE",
            }
        )
        doc_id = int(doc["id"])
        published = await client.publish(doc_id)
        print(f"published documentId={published.get('id') or doc_id} title={DOC_TITLE}")
        return 0
    finally:
        reset_downstream_authorization(tok)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed SQL_EX knowledge documents")
    parser.add_argument("--via", choices=("db", "http"), default="db")
    parser.add_argument(
        "--dsn",
        default="postgresql+asyncpg://postgres:root@127.0.0.1:5432/postgres",
    )
    parser.add_argument("--base-url", default="")
    parser.add_argument("--token", default="", help="HTTP 模式所需 Bearer JWT")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.via == "db":
        return await seed_via_db(args.dsn, force=args.force)

    settings = Settings()
    if args.base_url.strip():
        settings = settings.model_copy(
            update={"ada_memory_base_url": args.base_url.strip().rstrip("/")}
        )
    if not (args.token or "").strip():
        print("HTTP 模式需要 --token", file=sys.stderr)
        return 2
    return await seed_via_http(settings, args.token.strip(), force=args.force)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
