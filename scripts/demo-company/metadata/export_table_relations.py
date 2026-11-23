"""从 PostgreSQL 导出 company schema 全量外键 → table-relations.md。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"
OUT = Path(__file__).resolve().parent / "table-relations.md"

CORE_TABLES = frozenset(
    {
        "org_department",
        "hr_job_level",
        "hr_employee",
        "att_leave_type",
        "att_leave",
        "att_overtime",
        "att_daily_record",
        "att_timesheet",
        "fin_salary_period",
        "fin_salary_slip",
        "fin_reimburse",
        "fin_reimburse_item",
        "fin_activity_budget",
        "fin_activity_expense",
        "crm_customer",
        "prd_product",
        "prd_product_cost",
        "sal_sales_order",
        "sal_sales_order_item",
        "prj_project",
        "prj_project_member",
        "prj_project_revenue",
    }
)

DOMAIN_PREFIX = [
    ("org_", "组织/公司/职场/成本中心"),
    ("hr_", "人事/绩效/招聘/培训"),
    ("att_", "考勤/排班/打卡"),
    ("fin_", "财务/发票/预算/总账"),
    ("crm_", "客户/商机/跟进"),
    ("sal_", "销售/合同/交付/提成"),
    ("prd_", "产品"),
    ("prj_", "项目交付"),
    ("scm_", "采购/库存"),
    ("itm_", "IT 资产/服务台"),
    ("sec_", "安全"),
    ("ops_", "运维"),
    ("mkt_", "市场"),
    ("adm_", "行政"),
    ("legal_", "法务"),
    ("qa_", "质量"),
    ("kb_", "知识"),
    ("dim_", "通用字典"),
]


async def fetch_fks(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT
          tc.table_name AS child_table,
          kcu.column_name AS child_column,
          ccu.table_name AS parent_table,
          ccu.column_name AS parent_column,
          tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = 'company'
          AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.ordinal_position, kcu.column_name
        """
    )
    return [dict(r) for r in rows]


async def fetch_table_counts(conn: asyncpg.Connection) -> tuple[int, int]:
    tables = [
        r["table_name"]
        for r in await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'company' AND table_type = 'BASE TABLE'
            """
        )
    ]
    core = sum(1 for t in tables if t in CORE_TABLES)
    return core, len(tables) - core


def _domain(name: str) -> str:
    for p, zh in DOMAIN_PREFIX:
        if name.startswith(p):
            return zh
    return "其它"


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        fks = await fetch_fks(conn)
        core_n, ext_n = await fetch_table_counts(conn)
        comments = {
            r["table_name"]: (r["comment"] or "").strip()
            for r in await conn.fetch(
                """
                SELECT c.relname AS table_name, obj_description(c.oid) AS comment
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'company' AND c.relkind = 'r'
                """
            )
        }
    finally:
        await conn.close()

    core_fks = [f for f in fks if f["child_table"] in CORE_TABLES]
    ext_fks = [f for f in fks if f["child_table"] not in CORE_TABLES]

    lines = [
        "# company 库表关系说明",
        "",
        f"> 以库内实际 FOREIGN KEY 为准（自动导出）。",
        f"> 核心表 {core_n} 张 + 扩展表 {ext_n} 张 ≈ **{core_n + ext_n}** 张；外键共 **{len(fks)}** 条。",
        "> 扩展表无灌数；外键可指向核心表或其它扩展表。",
        "",
        "## 核心表",
        "",
    ]
    for n in sorted(CORE_TABLES):
        zh = comments.get(n) or ""
        lines.append(f"- `{n}`" + (f" — {zh}" if zh else ""))

    lines.extend(
        [
            "",
            f"## 核心表外键关系（{len(core_fks)}）",
            "",
            "| 子表 | 列 | 父表 | 父列 | 子表说明 |",
            "|---|---|---|---|---|",
        ]
    )
    for f in core_fks:
        zh = comments.get(f["child_table"]) or ""
        lines.append(
            f"| `{f['child_table']}` | `{f['child_column']}` | `{f['parent_table']}` | "
            f"`{f['parent_column']}` | {zh or '-'} |"
        )

    lines.extend(
        [
            "",
            f"## 扩展表外键关系（{len(ext_fks)}）",
            "",
            "| 子表 | 列 | 父表 | 父列 | 子表说明 |",
            "|---|---|---|---|---|",
        ]
    )
    for f in ext_fks:
        zh = comments.get(f["child_table"]) or ""
        lines.append(
            f"| `{f['child_table']}` | `{f['child_column']}` | `{f['parent_table']}` | "
            f"`{f['parent_column']}` | {zh or '-'} |"
        )

    lines.extend(["", "## 全量外键（按子表）", ""])
    by_child: dict[str, list[dict]] = {}
    for f in fks:
        by_child.setdefault(f["child_table"], []).append(f)
    for child in sorted(by_child):
        zh = comments.get(child) or ""
        tag = "核心" if child in CORE_TABLES else "扩展"
        lines.append(f"### `{child}`（{tag}" + (f" · {zh}" if zh else "") + "）")
        lines.append("")
        for f in by_child[child]:
            lines.append(
                f"- `{f['child_column']}` → `{f['parent_table']}.{f['parent_column']}`"
            )
        lines.append("")

    lines.extend(
        [
            "## 业务域一览",
            "",
            "| 前缀 | 域 |",
            "|---|---|",
        ]
    )
    for p, zh in DOMAIN_PREFIX:
        lines.append(f"| {p} | {zh} |")
    lines.append("")

    # 按域统计外键条数
    lines.extend(["## 外键条数（按子表域）", "", "| 域 | 条数 |", "|---|---|"])
    domain_cnt: dict[str, int] = {}
    for f in fks:
        d = _domain(f["child_table"])
        domain_cnt[d] = domain_cnt.get(d, 0) + 1
    for d, n in sorted(domain_cnt.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {d} | {n} |")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} fk={len(fks)} core_fk={len(core_fks)} ext_fk={len(ext_fks)}")


if __name__ == "__main__":
    asyncio.run(main())
