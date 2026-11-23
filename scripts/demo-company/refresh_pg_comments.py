"""仅修复乱码 COMMENT（含 ??? / 问号占位），不补全空注释（模拟真实库注释不全）。

优先用 extended_catalog.json / 核心 COL_DESC 的中文；找不到则删除乱码注释（置空）。
通过 asyncpg 写入，避免 Windows 管道编码问题。
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import asyncpg

HERE = Path(__file__).resolve().parent
META = HERE / "metadata"
DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"

sys.path.insert(0, str(META))
from gen_db_structure_doc import COL_DESC, TABLE_DESC  # noqa: E402

_QMARK_RE = re.compile(r"\?{2,}|�")


def _esc(s: str) -> str:
    return s.replace("'", "''")


def _is_garbled(text: str | None) -> bool:
    if not text:
        return False
    if _QMARK_RE.search(text):
        return True
    # 全是问号/空白
    if re.fullmatch(r"[?\s]+", text):
        return True
    return False


def _load_extended() -> tuple[dict[str, str], dict[str, str]]:
    path = META / "extended_catalog.json"
    tdesc: dict[str, str] = {}
    cdesc: dict[str, str] = {}
    if not path.is_file():
        return tdesc, cdesc
    data = json.loads(path.read_text(encoding="utf-8"))
    for tname, meta in (data.get("tables") or {}).items():
        zh = str(meta.get("zh") or "").strip()
        if zh:
            tdesc[tname] = zh.rstrip("。") + "。"
        for col, czh in (meta.get("columns") or {}).items():
            if czh:
                cdesc[f"{tname}.{col}"] = str(czh)
    return tdesc, cdesc


async def main() -> None:
    ext_t, ext_c = _load_extended()
    table_desc = {**ext_t, **TABLE_DESC}
    col_desc = {**ext_c, **COL_DESC}

    conn = await asyncpg.connect(DSN)
    fixed_t = fixed_c = cleared = 0
    try:
        rows = await conn.fetch(
            """
            SELECT c.relname AS table_name,
                   obj_description(c.oid) AS table_comment,
                   a.attname AS column_name,
                   col_description(c.oid, a.attnum) AS column_comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
            WHERE n.nspname = 'company' AND c.relkind = 'r'
            ORDER BY c.relname, a.attnum
            """
        )
        seen_tables: set[str] = set()
        for r in rows:
            t = r["table_name"]
            if t not in seen_tables:
                seen_tables.add(t)
                tc = r["table_comment"]
                if _is_garbled(tc):
                    zh = table_desc.get(t)
                    if zh:
                        await conn.execute(f"COMMENT ON TABLE company.{t} IS '{_esc(zh)}'")
                        fixed_t += 1
                    else:
                        await conn.execute(f"COMMENT ON TABLE company.{t} IS NULL")
                        cleared += 1
            cc = r["column_comment"]
            if _is_garbled(cc):
                key = f"{t}.{r['column_name']}"
                zh = col_desc.get(key)
                if zh:
                    zh = re.sub(r"`([^`]+)`", r"\1", zh)
                    await conn.execute(
                        f"COMMENT ON COLUMN company.{t}.{r['column_name']} IS '{_esc(zh)}'"
                    )
                    fixed_c += 1
                else:
                    await conn.execute(
                        f"COMMENT ON COLUMN company.{t}.{r['column_name']} IS NULL"
                    )
                    cleared += 1
        print(f"fixed_tables={fixed_t} fixed_columns={fixed_c} cleared_garbled={cleared}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
