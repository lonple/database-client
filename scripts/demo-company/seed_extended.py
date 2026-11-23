#!/usr/bin/env python3
"""向 company schema 的扩展表灌入干净演示数据（不动核心 22 表行）。

口径：
- 维表/字典/公司职场/班次/科目等：小规模
- 其余事实表：约 FACT_N=10000 行，时间窗与核心一致 START～END（约 3 年）
- 主从金额：头 = Σ 明细；凭证借贷平衡；借款核销合计 ≤ 借款额
- 外键：不可空列必须命中已存在父行

用法：
  .\\dbc-askdata\\.venv\\Scripts\\python.exe .\\scripts\\demo-company\\seed_extended.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from pathlib import Path

import asyncpg

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "metadata" / "extended_catalog.json"
DSN_DEFAULT = "postgresql://postgres:root@127.0.0.1:5432/postgres"
SEED = 20261002
START = date(2023, 10, 1)
END = date(2026, 9, 28)
FACT_N = 10_000
BATCH = 2000

# 与 gen_extended_schema.CORE_TABLES 对齐：禁止 truncate / 禁止写入
CORE_TABLES = {
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

# 明确小规模维/主数据（其余默认 FACT_N）
SMALL_TARGETS: dict[str, int] = {
    "org_company": 5,
    "org_office": 12,
    "org_cost_center": 40,
    "org_position": 80,
    "org_biz_unit": 12,
    "org_location": 20,
    "org_dept_closure": 0,  # 由部门派生
    "org_dept_change": 200,
    "org_seal": 15,
    "org_announcement": 300,
    "hr_performance_cycle": 12,
    "hr_training_course": 40,
    "hr_work_calendar": 0,  # 按日派生
    "att_shift": 8,
    "att_ot_rule": 5,
    "att_device": 30,
    "fin_vendor": 200,
    "fin_gl_account": 60,
    "fin_bank_account": 10,
    "fin_exchange_rate": 800,
    "fin_tax_period": 108,
    "fin_petty_cash": 20,
    "prd_product_line": 8,
    "sal_channel": 12,
    "sal_price_list": 6,
    "sal_commission_rule": 10,
    "scm_warehouse": 8,
    "scm_material": 200,
    "itm_system": 25,
    "sec_policy": 20,
    "sec_data_class": 8,
    "adm_meeting_room": 20,
    "adm_supply": 50,
    "adm_vehicle": 15,
    "kb_article_tag": 40,
    "ops_runbook": 40,
    "ops_backup_job": 30,
    "mkt_content": 200,
    "legal_compliance_check": 100,
    "qa_release_gate": 200,
}

# 1 人/客户维度类：按核心规模派生，不硬凑 1 万
PER_EMP_SMALL = {
    "hr_contract",
    "hr_probation",
    "hr_onboarding",
    "hr_bank_account",
    "hr_emergency_contact",
    "hr_education",
    "hr_work_history",
    "hr_certificate",
    "hr_family_member",
    "hr_resignation",
    "att_leave_balance",
}
PER_CUSTOMER_SMALL = {"crm_sla", "crm_contact"}
PER_PROJECT_SMALL = {
    "prj_milestone",
    "prj_acceptance",
    "prj_warranty",
    "prj_stakeholder",
}


def d(v: float | int | None) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(round(float(v), 2)))


def add_months(d0: date, n: int) -> date:
    y = d0.year + (d0.month - 1 + n) // 12
    m = (d0.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def month_start(d0: date) -> date:
    return date(d0.year, d0.month, 1)


def iter_months(start: date, end: date):
    cur = month_start(start)
    last = month_start(end)
    while cur <= last:
        yield cur
        cur = add_months(cur, 1)


def rand_date(rng: random.Random, start: date = START, end: date = END) -> date:
    span = (end - start).days
    return start + timedelta(days=rng.randint(0, max(span, 0)))


def rand_ts(rng: random.Random, start: date = START, end: date = END) -> datetime:
    day = rand_date(rng, start, end)
    return datetime.combine(day, time(rng.randint(8, 20), rng.randint(0, 59), rng.randint(0, 59)))


def is_dim(name: str) -> bool:
    return name.startswith("dim_lookup_")


def target_rows(name: str) -> int:
    if is_dim(name):
        return 40
    if name in SMALL_TARGETS:
        return SMALL_TARGETS[name]
    return FACT_N


async def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


async def fetch_core_ids(conn: asyncpg.Connection) -> dict:
    emp = [r["id"] for r in await conn.fetch("SELECT id FROM company.hr_employee ORDER BY id")]
    dept = [r["id"] for r in await conn.fetch("SELECT id FROM company.org_department ORDER BY id")]
    jl = [r["id"] for r in await conn.fetch("SELECT id FROM company.hr_job_level ORDER BY id")]
    cust = [r["id"] for r in await conn.fetch("SELECT id FROM company.crm_customer ORDER BY id")]
    prod = [r["id"] for r in await conn.fetch("SELECT id FROM company.prd_product ORDER BY id")]
    proj = [r["id"] for r in await conn.fetch("SELECT id FROM company.prj_project ORDER BY id")]
    orders = [r["id"] for r in await conn.fetch("SELECT id FROM company.sal_sales_order ORDER BY id")]
    claims = [r["id"] for r in await conn.fetch("SELECT id FROM company.fin_reimburse ORDER BY id")]
    leave_types = [r["id"] for r in await conn.fetch("SELECT id FROM company.att_leave_type ORDER BY id")]
    if not emp or not dept:
        raise RuntimeError("核心表无数据，请先跑 seed_company.py")
    return {
        "hr_employee": emp,
        "org_department": dept,
        "hr_job_level": jl,
        "crm_customer": cust,
        "prd_product": prod,
        "prj_project": proj,
        "sal_sales_order": orders,
        "fin_reimburse": claims,
        "att_leave_type": leave_types,
    }


async def table_columns(conn: asyncpg.Connection, table: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT column_name, data_type, udt_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='company' AND table_name=$1
        ORDER BY ordinal_position
        """,
        table,
    )
    return [dict(r) for r in rows]


async def truncate_extended(conn: asyncpg.Connection, tables: list[str]) -> None:
    # 子表优先：按名字反序足够（扩展表互相依赖简单；再兜底 CASCADE）
    names = [t for t in reversed(tables) if t not in CORE_TABLES]
    # 分批，避免超长语句
    for i in range(0, len(names), 40):
        chunk = names[i : i + 40]
        q = "TRUNCATE TABLE " + ", ".join(f"company.{n}" for n in chunk) + " RESTART IDENTITY CASCADE"
        await conn.execute(q)


def pick(ids: list[int], rng: random.Random) -> int:
    return ids[rng.randrange(len(ids))]


def pick_opt(ids: list[int], rng: random.Random, p: float = 0.85) -> int | None:
    if not ids or rng.random() > p:
        return None
    return pick(ids, rng)


async def insert_returning_ids(
    conn: asyncpg.Connection, table: str, cols: list[str], rows: list[tuple]
) -> list[int]:
    if not rows:
        return []
    ids: list[int] = []
    col_sql = ", ".join(cols)
    ph = ", ".join(f"${i+1}" for i in range(len(cols)))
    sql = f"INSERT INTO company.{table} ({col_sql}) VALUES ({ph}) RETURNING id"
    for i in range(0, len(rows), BATCH):
        batch = rows[i : i + BATCH]
        # executemany 无 returning 聚合；用 pipeline 循环
        async with conn.transaction():
            for row in batch:
                rid = await conn.fetchval(sql, *row)
                ids.append(rid)
    return ids


async def insert_many(conn: asyncpg.Connection, table: str, cols: list[str], rows: list[tuple]) -> int:
    if not rows:
        return 0
    col_sql = ", ".join(cols)
    ph = ", ".join(f"${i+1}" for i in range(len(cols)))
    sql = f"INSERT INTO company.{table} ({col_sql}) VALUES ({ph})"
    for i in range(0, len(rows), BATCH):
        await conn.executemany(sql, rows[i : i + BATCH])
    return len(rows)


class SeedCtx:
    def __init__(self, rng: random.Random, core: dict):
        self.rng = rng
        self.ids: dict[str, list[int]] = {k: list(v) for k, v in core.items()}
        self.counts: dict[str, int] = {}

    def set_ids(self, table: str, ids: list[int]) -> None:
        self.ids[table] = ids
        self.counts[table] = len(ids)

    def note(self, table: str, n: int) -> None:
        self.counts[table] = n


async def seed_org(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    companies = []
    for i in range(1, 6):
        companies.append(
            (
                f"CO{i:02d}",
                f"演示法人公司{i}",
                f"演示科技（中国）有限公司{i}",
                f"91330000MA{i:08d}",
                "active",
                None,
            )
        )
    cids = await insert_returning_ids(
        conn,
        "org_company",
        ["company_code", "company_name", "legal_name", "tax_no", "status", "remark"],
        companies,
    )
    ctx.set_ids("org_company", cids)

    offices = []
    cities = ["杭州", "上海", "北京", "深圳", "成都", "南京", "武汉", "西安", "广州", "苏州", "宁波", "重庆"]
    for i, city in enumerate(cities, start=1):
        offices.append(
            (f"OF{i:02d}", f"{city}职场", city, f"{city}示范路{i}号", pick(cids, rng), "active", None)
        )
    oids = await insert_returning_ids(
        conn,
        "org_office",
        ["office_code", "office_name", "city", "address", "company_id", "status", "remark"],
        offices,
    )
    ctx.set_ids("org_office", oids)

    depts = ctx.ids["org_department"]
    emps = ctx.ids["hr_employee"]
    jls = ctx.ids["hr_job_level"]

    ccs = []
    for i in range(1, 41):
        ccs.append(
            (
                f"CC{i:03d}",
                f"成本中心{i}",
                pick(depts, rng),
                pick(emps, rng),
                "active",
                None,
            )
        )
    cc_ids = await insert_returning_ids(
        conn,
        "org_cost_center",
        ["cc_code", "cc_name", "dept_id", "owner_emp_id", "status", "remark"],
        ccs,
    )
    ctx.set_ids("org_cost_center", cc_ids)

    pos = []
    for i in range(1, 81):
        pos.append(
            (
                f"POS{i:03d}",
                f"岗位{i}",
                pick(depts, rng),
                pick(jls, rng),
                rng.randint(1, 20),
                "active",
                None,
            )
        )
    pos_ids = await insert_returning_ids(
        conn,
        "org_position",
        ["pos_code", "pos_name", "dept_id", "job_level_id", "headcount", "status", "remark"],
        pos,
    )
    ctx.set_ids("org_position", pos_ids)

    bus = []
    for i in range(1, 13):
        bus.append((f"BU{i:02d}", f"业务单元{i}", pick(emps, rng), "active", None))
    bu_ids = await insert_returning_ids(
        conn, "org_biz_unit", ["bu_code", "bu_name", "leader_emp_id", "status", "remark"], bus
    )
    ctx.set_ids("org_biz_unit", bu_ids)

    locs = []
    for i, (code, name, region) in enumerate(
        [
            ("LOC-EAST", "华东区", "华东"),
            ("LOC-NORTH", "华北区", "华北"),
            ("LOC-SOUTH", "华南区", "华南"),
            ("LOC-SW", "西南区", "西南"),
            ("LOC-CENT", "华中区", "华中"),
            ("LOC-NW", "西北区", "西北"),
        ],
        start=1,
    ):
        locs.append((code, name, region, "中国", "active", None))
    for i in range(7, 21):
        locs.append((f"LOC{i:02d}", f"区位{i}", rng.choice(["华东", "华北", "华南"]), "中国", "active", None))
    loc_ids = await insert_returning_ids(
        conn,
        "org_location",
        ["loc_code", "loc_name", "region", "country", "status", "remark"],
        locs,
    )
    ctx.set_ids("org_location", loc_ids)

    # 部门闭包：自反 + 少量跨层（无 parent 列时仅自反）
    closure = [(did, did, 0) for did in depts]
    # 随机祖先-后代 depth=1（演示用，不保证真实树）
    for _ in range(min(40, len(depts) * 2)):
        a, b = pick(depts, rng), pick(depts, rng)
        if a != b:
            closure.append((a, b, 1))
    # 去重
    seen = set()
    uniq = []
    for a, b, depth in closure:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        uniq.append((a, b, depth))
    n = await insert_many(conn, "org_dept_closure", ["ancestor_id", "descendant_id", "depth"], uniq)
    ctx.note("org_dept_closure", n)

    changes = []
    for i in range(200):
        changes.append(
            (
                pick(depts, rng),
                rng.choice(["rename", "move", "split", "merge"]),
                pick_opt(depts, rng, 0.6),
                pick_opt(depts, rng, 0.6),
                rand_date(rng),
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "org_dept_change",
        [
            "dept_id",
            "change_type",
            "old_parent_id",
            "new_parent_id",
            "effective_date",
            "operator_emp_id",
            "status",
            "remark",
        ],
        changes,
    )
    ctx.note("org_dept_change", n)

    seals = []
    for i in range(1, 16):
        seals.append(
            (f"SEAL{i:02d}", f"印章{i}", pick(cids, rng), pick(emps, rng), "active", None)
        )
    seal_ids = await insert_returning_ids(
        conn,
        "org_seal",
        ["seal_code", "seal_name", "company_id", "keeper_emp_id", "status", "remark"],
        seals,
    )
    ctx.set_ids("org_seal", seal_ids)

    anns = []
    for i in range(300):
        anns.append(
            (
                f"公告标题{i+1}",
                f"公告正文内容示例 {i+1}",
                pick(emps, rng),
                rand_ts(rng),
                rng.choice(["all", "dept", "mgmt"]),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "org_announcement",
        ["title", "content", "publisher_emp_id", "publish_at", "scope", "status", "remark"],
        anns,
    )
    ctx.note("org_announcement", n)


async def seed_hr_people(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    """按员工派生的一人一行/少量行表。"""
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    depts = ctx.ids["org_department"]
    jls = ctx.ids["hr_job_level"]
    cos = ctx.ids.get("org_company", [])

    # 合同：在职员工各 1
    rows = []
    for i, eid in enumerate(emps):
        rows.append(
            (
                eid,
                f"HT{2023 + i % 3}{i:05d}",
                rng.choice(["labor", "outsource", "intern"]),
                rand_date(rng, START, date(2025, 12, 31)),
                rand_date(rng, date(2025, 1, 1), END) if rng.random() < 0.7 else None,
                pick_opt(cos, rng, 0.9),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_contract",
        [
            "emp_id",
            "contract_no",
            "contract_type",
            "start_date",
            "end_date",
            "sign_company_id",
            "status",
            "remark",
        ],
        rows,
    )
    ctx.note("hr_contract", n)

    # 试用/入职/银行/紧急联系人/教育/履历/证书/家属：抽样员工
    sample = emps if len(emps) <= 800 else rng.sample(emps, 800)

    def pack_status():
        return "active", None

    rows = []
    for eid in sample[:600]:
        rows.append(
            (
                eid,
                rand_date(rng),
                rand_date(rng) if rng.random() < 0.8 else None,
                rng.choice(["pass", "extend", "fail", "pending"]),
                pick_opt(emps, rng, 0.7),
                *pack_status(),
            )
        )
    n = await insert_many(
        conn,
        "hr_probation",
        ["emp_id", "plan_end_date", "actual_end_date", "result", "mentor_emp_id", "status", "remark"],
        rows,
    )
    ctx.note("hr_probation", n)

    rows = []
    for eid in sample:
        rows.append(
            (
                eid,
                rng.choice(["done", "pending", "partial"]),
                rng.random() < 0.85,
                f"B{eid:06d}",
                *pack_status(),
            )
        )
    n = await insert_many(
        conn,
        "hr_onboarding",
        ["emp_id", "checklist_status", "it_ready", "badge_no", "status", "remark"],
        rows,
    )
    ctx.note("hr_onboarding", n)

    rows = []
    for eid in sample:
        rows.append(
            (eid, rng.choice(["工行", "建行", "招行", "支付宝"]), f"6222{eid:012d}"[-19:], True, *pack_status())
        )
    n = await insert_many(
        conn,
        "hr_bank_account",
        ["emp_id", "bank_name", "account_no", "is_primary", "status", "remark"],
        rows,
    )
    ctx.note("hr_bank_account", n)

    rows = []
    for eid in sample:
        rows.append((eid, f"联系人{eid % 97}", rng.choice(["配偶", "父母", "子女", "朋友"]), f"138{eid:08d}"[-11:], *pack_status()))
    n = await insert_many(
        conn,
        "hr_emergency_contact",
        ["emp_id", "contact_name", "relation", "phone", "status", "remark"],
        rows,
    )
    ctx.note("hr_emergency_contact", n)

    rows = []
    for eid in sample:
        rows.append(
            (
                eid,
                rng.choice(["浙江大学", "复旦大学", "上海交大", "杭电", "其他高校"]),
                rng.choice(["本科", "硕士", "大专", "博士"]),
                rng.choice(["计算机", "软件工程", "会计", "市场营销", "电子信息"]),
                date(2008 + eid % 10, 6, 30),
                *pack_status(),
            )
        )
    n = await insert_many(
        conn,
        "hr_education",
        ["emp_id", "school", "degree", "major", "graduate_date", "status", "remark"],
        rows,
    )
    ctx.note("hr_education", n)

    rows = []
    for eid in sample[:500]:
        rows.append(
            (
                eid,
                f"前东家{(eid % 50) + 1}",
                rng.choice(["工程师", "经理", "专员", "顾问"]),
                date(2015 + eid % 5, 3, 1),
                date(2018 + eid % 5, 8, 31),
                *pack_status(),
            )
        )
    n = await insert_many(
        conn,
        "hr_work_history",
        ["emp_id", "employer", "title", "start_date", "end_date", "status", "remark"],
        rows,
    )
    ctx.note("hr_work_history", n)

    rows = []
    for eid in sample[:400]:
        rows.append(
            (
                eid,
                rng.choice(["PMP", "软考中级", "CPA", "AWS SAA", "英语六级"]),
                f"CERT{eid}",
                rand_date(rng, date(2026, 1, 1), date(2029, 12, 31)),
                *pack_status(),
            )
        )
    n = await insert_many(
        conn,
        "hr_certificate",
        ["emp_id", "cert_name", "cert_no", "expire_date", "status", "remark"],
        rows,
    )
    ctx.note("hr_certificate", n)

    rows = []
    for eid in sample[:500]:
        rows.append(
            (eid, f"家属{eid % 80}", rng.choice(["配偶", "子女", "父母"]), date(1990 + eid % 20, 5, 1), *pack_status())
        )
    n = await insert_many(
        conn,
        "hr_family_member",
        ["emp_id", "member_name", "relation", "birthday", "status", "remark"],
        rows,
    )
    ctx.note("hr_family_member", n)

    # 调动/晋升/奖惩/离职办理
    rows = []
    for i in range(3000):
        rows.append(
            (
                pick(emps, rng),
                pick(depts, rng),
                pick(depts, rng),
                rand_date(rng),
                rng.choice(["transfer", "secondment", "return"]),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_transfer",
        ["emp_id", "from_dept_id", "to_dept_id", "effective_date", "transfer_type", "status", "remark"],
        rows,
    )
    ctx.note("hr_transfer", n)

    rows = []
    for i in range(2000):
        a, b = pick(jls, rng), pick(jls, rng)
        rows.append((pick(emps, rng), a, b, rand_date(rng), "active", None))
    n = await insert_many(
        conn,
        "hr_promotion",
        ["emp_id", "from_level_id", "to_level_id", "effective_date", "status", "remark"],
        rows,
    )
    ctx.note("hr_promotion", n)

    rows = []
    for i in range(2500):
        rows.append(
            (
                pick(emps, rng),
                rng.choice(["award", "penalty"]),
                d(rng.uniform(100, 5000)),
                rand_date(rng),
                f"事由{i}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_award",
        ["emp_id", "award_type", "amount", "occur_date", "reason", "status", "remark"],
        rows,
    )
    ctx.note("hr_award", n)

    # 离职办理：部分员工
    left_like = rng.sample(emps, min(200, len(emps)))
    rows = []
    for eid in left_like:
        rows.append(
            (
                eid,
                rand_date(rng),
                rand_date(rng),
                rng.choice(["personal", "performance", "org", "other"]),
                "面谈纪要摘要",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_resignation",
        ["emp_id", "apply_date", "last_work_date", "reason_type", "exit_interview", "status", "remark"],
        rows,
    )
    ctx.note("hr_resignation", n)

    # 绩效周期 + 目标/评估
    cycles = []
    for i, ym in enumerate(list(iter_months(date(2024, 1, 1), date(2026, 9, 1)))[:12]):
        cycles.append(
            (
                f"PERF{ym.year}{ym.month:02d}",
                f"{ym.year}年{ym.month}月绩效",
                ym,
                add_months(ym, 1) - timedelta(days=1),
                "active",
                None,
            )
        )
    cycle_ids = await insert_returning_ids(
        conn,
        "hr_performance_cycle",
        ["cycle_code", "cycle_name", "start_date", "end_date", "status", "remark"],
        cycles,
    )
    ctx.set_ids("hr_performance_cycle", cycle_ids)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(cycle_ids, rng),
                pick(emps, rng),
                f"目标描述 {rng.randint(1, 9999)}",
                d(rng.uniform(5, 40)),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_performance_goal",
        ["cycle_id", "emp_id", "goal_text", "weight_pct", "status", "remark"],
        rows,
    )
    ctx.note("hr_performance_goal", n)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(cycle_ids, rng),
                pick(emps, rng),
                d(rng.uniform(60, 100)),
                rng.choice(["A", "B", "C", "D"]),
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_performance_review",
        ["cycle_id", "emp_id", "score", "grade", "reviewer_emp_id", "status", "remark"],
        rows,
    )
    ctx.note("hr_performance_review", n)

    # 培训
    courses = []
    for i in range(1, 41):
        courses.append(
            (f"COURSE{i:03d}", f"培训课程{i}", d(rng.uniform(2, 40)), f"供应商{i % 7}", "active", None)
        )
    course_ids = await insert_returning_ids(
        conn,
        "hr_training_course",
        ["course_code", "course_name", "hours", "vendor", "status", "remark"],
        courses,
    )
    ctx.set_ids("hr_training_course", course_ids)

    sessions = []
    for i in range(800):
        st = rand_ts(rng)
        sessions.append(
            (
                pick(course_ids, rng),
                st,
                st + timedelta(hours=rng.randint(2, 8)),
                rng.choice(["杭州", "线上", "上海"]),
                f"讲师{i % 20}",
                "active",
                None,
            )
        )
    sess_ids = await insert_returning_ids(
        conn,
        "hr_training_session",
        ["course_id", "start_at", "end_at", "location", "trainer", "status", "remark"],
        sessions,
    )
    ctx.set_ids("hr_training_session", sess_ids)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(sess_ids, rng),
                pick(emps, rng),
                rng.choice(["attended", "absent", "late"]),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_training_enroll",
        ["session_id", "emp_id", "attend_status", "status", "remark"],
        rows,
    )
    ctx.note("hr_training_enroll", n)

    # 招聘
    reqs = []
    for i in range(1, 501):
        reqs.append(
            (
                f"REQ{i:04d}",
                f"招聘需求{i}",
                pick(depts, rng),
                rng.randint(1, 5),
                pick(jls, rng),
                pick(emps, rng),
                "active",
                None,
            )
        )
    req_ids = await insert_returning_ids(
        conn,
        "hr_recruit_req",
        [
            "req_code",
            "req_name",
            "dept_id",
            "headcount",
            "job_level_id",
            "owner_emp_id",
            "status",
            "remark",
        ],
        reqs,
    )
    ctx.set_ids("hr_recruit_req", req_ids)

    cands = []
    for i in range(1, 3001):
        cands.append(
            (
                f"CAND{i:05d}",
                f"候选人{i}",
                f"139{i:08d}"[-11:],
                f"cand{i}@example.com",
                rng.choice(["猎头", "内推", "官网", "社招"]),
                "active",
                None,
            )
        )
    cand_ids = await insert_returning_ids(
        conn,
        "hr_candidate",
        ["cand_code", "cand_name", "phone", "email", "source", "status", "remark"],
        cands,
    )
    ctx.set_ids("hr_candidate", cand_ids)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(cand_ids, rng),
                pick_opt(req_ids, rng, 0.9),
                pick(emps, rng),
                rand_ts(rng),
                rng.choice(["pass", "fail", "pending"]),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_interview",
        ["candidate_id", "req_id", "interviewer_emp_id", "interview_at", "result", "status", "remark"],
        rows,
    )
    ctx.note("hr_interview", n)

    rows = []
    for i in range(2000):
        rows.append(
            (
                pick(cand_ids, rng),
                pick_opt(req_ids, rng, 0.9),
                d(rng.uniform(15, 80) * 10000),
                rng.choice(["accepted", "rejected", "pending"]),
                rand_date(rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "hr_offer",
        ["candidate_id", "req_id", "offer_amount", "accept_status", "join_date", "status", "remark"],
        rows,
    )
    ctx.note("hr_offer", n)

    # 工作日历 3 年
    cal = []
    cur = START
    while cur <= END:
        day_type = "work" if cur.weekday() < 5 else "weekend"
        holiday = None
        if cur.month == 10 and cur.day == 1:
            day_type, holiday = "holiday", "国庆"
        cal.append((cur, day_type, holiday, "active", None))
        cur += timedelta(days=1)
    n = await insert_many(
        conn,
        "hr_work_calendar",
        ["cal_date", "day_type", "holiday_name", "status", "remark"],
        cal,
    )
    ctx.note("hr_work_calendar", n)

    rows = []
    months = list(iter_months(START, END))
    for did in depts:
        for ym in months:
            plan = rng.randint(5, 80)
            rows.append((did, f"{ym.year}-{ym.month:02d}", plan, max(0, plan + rng.randint(-5, 5)), "active", None))
    n = await insert_many(
        conn,
        "hr_headcount_plan",
        ["dept_id", "year_month", "plan_hc", "actual_hc", "status", "remark"],
        rows,
    )
    ctx.note("hr_headcount_plan", n)


async def seed_att(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    offices = ctx.ids.get("org_office", [])
    projs = ctx.ids["prj_project"]
    leave_types = ctx.ids["att_leave_type"]

    shifts = []
    for i, (code, name, st, et) in enumerate(
        [
            ("S1", "标准白班", time(9, 0), time(18, 0)),
            ("S2", "早班", time(8, 0), time(17, 0)),
            ("S3", "晚班", time(13, 0), time(22, 0)),
            ("S4", "弹性", time(10, 0), time(19, 0)),
            ("S5", "值班", time(0, 0), time(8, 0)),
            ("S6", "周末班", time(9, 0), time(17, 0)),
            ("S7", "培训班", time(9, 30), time(16, 30)),
            ("S8", "远程协同", time(9, 0), time(18, 0)),
        ],
        start=1,
    ):
        shifts.append((code, name, st, et, 60, "active", None))
    shift_ids = await insert_returning_ids(
        conn,
        "att_shift",
        ["shift_code", "shift_name", "start_time", "end_time", "break_minutes", "status", "remark"],
        shifts,
    )
    ctx.set_ids("att_shift", shift_ids)

    rules = []
    for i in range(1, 6):
        rules.append((f"OTR{i}", f"加班规则{i}", d(1.5), d(2.0), d(3.0), "active", None))
    rule_ids = await insert_returning_ids(
        conn,
        "att_ot_rule",
        ["rule_code", "rule_name", "weekday_rate", "weekend_rate", "holiday_rate", "status", "remark"],
        rules,
    )
    ctx.set_ids("att_ot_rule", rule_ids)

    devices = []
    for i in range(1, 31):
        devices.append(
            (f"DEV{i:03d}", f"考勤机{i}", pick_opt(offices, rng, 0.9), f"10.0.{i // 10}.{i}", "active", None)
        )
    dev_ids = await insert_returning_ids(
        conn,
        "att_device",
        ["device_code", "device_name", "office_id", "ip_addr", "status", "remark"],
        devices,
    )
    ctx.set_ids("att_device", dev_ids)

    # 排班 / 打卡 / 出差 / 居家 / 补卡 / 月汇总 / 假期余额
    rows = []
    for _ in range(FACT_N):
        rows.append((pick(emps, rng), pick(shift_ids, rng), rand_date(rng), "active", None))
    n = await insert_many(
        conn, "att_shift_assign", ["emp_id", "shift_id", "work_date", "status", "remark"], rows
    )
    ctx.note("att_shift_assign", n)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(emps, rng),
                rand_ts(rng),
                rng.choice(["in", "out"]),
                f"D{rng.randint(1, 30):03d}",
                pick_opt(offices, rng, 0.8),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "att_punch",
        ["emp_id", "punch_at", "punch_type", "device_no", "office_id", "status", "remark"],
        rows,
    )
    ctx.note("att_punch", n)

    rows = []
    for _ in range(FACT_N):
        s = rand_date(rng)
        rows.append(
            (
                pick(emps, rng),
                s,
                s + timedelta(days=rng.randint(1, 5)),
                rng.choice(["北京", "上海", "客户现场", "深圳"]),
                pick_opt(projs, rng, 0.6),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "att_travel",
        ["emp_id", "start_date", "end_date", "destination", "project_id", "status", "remark"],
        rows,
    )
    ctx.note("att_travel", n)

    rows = []
    for _ in range(FACT_N):
        rows.append((pick(emps, rng), rand_date(rng), f"事由{rng.randint(1,9999)}", "active", None))
    n = await insert_many(
        conn, "att_remote_work", ["emp_id", "work_date", "reason", "status", "remark"], rows
    )
    ctx.note("att_remote_work", n)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(emps, rng),
                rand_date(rng),
                rng.choice(["in", "out"]),
                f"补卡原因{rng.randint(1,999)}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "att_makeup_card",
        ["emp_id", "work_date", "punch_type", "reason", "status", "remark"],
        rows,
    )
    ctx.note("att_makeup_card", n)

    rows = []
    # 控制在约 1 万：3 年 × 全员 × 部分假种
    years = [2024, 2025, 2026]
    lt_use = leave_types[: max(1, min(3, len(leave_types)))]
    for eid in emps:
        for y in years:
            for lt in lt_use:
                rows.append((eid, lt, y, d(rng.uniform(0, 15)), "active", None))
    n = await insert_many(
        conn,
        "att_leave_balance",
        ["emp_id", "leave_type_id", "year", "balance_days", "status", "remark"],
        rows,
    )
    ctx.note("att_leave_balance", n)

    rows = []
    months = list(iter_months(START, END))
    # 控制在约 1 万：抽样员工 × 月份
    sample_emps = rng.sample(emps, min(280, len(emps)))
    for eid in sample_emps:
        for ym in months:
            rows.append(
                (
                    eid,
                    f"{ym.year}-{ym.month:02d}",
                    d(rng.uniform(15, 23)),
                    d(rng.uniform(0, 3)),
                    d(rng.uniform(0, 40)),
                    "active",
                    None,
                )
            )
            if len(rows) >= FACT_N:
                break
        if len(rows) >= FACT_N:
            break
    rows = rows[:FACT_N]
    n = await insert_many(
        conn,
        "att_monthly_summary",
        ["emp_id", "year_month", "work_days", "leave_days", "ot_hours", "status", "remark"],
        rows,
    )
    ctx.note("att_monthly_summary", n)


async def seed_fin(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    depts = ctx.ids["org_department"]
    custs = ctx.ids["crm_customer"]
    projs = ctx.ids["prj_project"]
    cos = ctx.ids["org_company"]
    claims = ctx.ids["fin_reimburse"]

    vendors = []
    for i in range(1, 201):
        vendors.append(
            (
                f"V{i:04d}",
                f"供应商{i}",
                f"9133{i:014d}"[:18],
                f"联系人{i}",
                f"137{i:08d}"[-11:],
                "active",
                None,
            )
        )
    vendor_ids = await insert_returning_ids(
        conn,
        "fin_vendor",
        ["vendor_code", "vendor_name", "tax_no", "contact", "phone", "status", "remark"],
        vendors,
    )
    ctx.set_ids("fin_vendor", vendor_ids)

    rows = []
    for i in range(FACT_N):
        amt = d(rng.uniform(100, 50000))
        tax = d(float(amt) * 0.06)
        rows.append(
            (
                f"INV{i+1:06d}",
                rng.choice(["input", "output"]),
                pick_opt(vendor_ids, rng, 0.5),
                pick_opt(custs, rng, 0.5),
                amt,
                tax,
                rand_date(rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "fin_invoice",
        [
            "invoice_no",
            "invoice_type",
            "vendor_id",
            "customer_id",
            "amount",
            "tax_amount",
            "invoice_date",
            "status",
            "remark",
        ],
        rows,
    )
    ctx.note("fin_invoice", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (
                f"PAY{i+1:06d}",
                pick(vendor_ids, rng),
                d(rng.uniform(500, 200000)),
                rand_date(rng),
                rng.choice(["bank", "check", "cash"]),
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "fin_payment",
        [
            "payment_no",
            "vendor_id",
            "amount",
            "pay_date",
            "method",
            "applicant_emp_id",
            "status",
            "remark",
        ],
        rows,
    )
    ctx.note("fin_payment", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (
                f"RCP{i+1:06d}",
                pick(custs, rng),
                d(rng.uniform(500, 300000)),
                rand_date(rng),
                pick_opt(projs, rng, 0.7),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "fin_receipt",
        ["receipt_no", "customer_id", "amount", "receipt_date", "project_id", "status", "remark"],
        rows,
    )
    ctx.note("fin_receipt", n)

    # 年度预算 + 明细（头 used_amount = Σ line，干净）
    budgets = []
    for y in (2024, 2025, 2026):
        for did in depts:
            budgets.append((y, did, d(0), d(0), "active", None))  # 先占位，后面回写
    # 用 returning 拿 id 后写 line 再 update
    budget_meta = []
    for y in (2024, 2025, 2026):
        for did in depts:
            budget_meta.append((y, did))
    budget_ids = await insert_returning_ids(
        conn,
        "fin_budget_year",
        ["year", "dept_id", "budget_amount", "used_amount", "status", "remark"],
        [(y, did, d(0), d(0), "active", None) for y, did in budget_meta],
    )
    ctx.set_ids("fin_budget_year", budget_ids)

    line_rows = []
    budget_sums: dict[int, Decimal] = {bid: Decimal("0") for bid in budget_ids}
    for bid in budget_ids:
        for j in range(rng.randint(3, 8)):
            amt = d(rng.uniform(5000, 80000))
            budget_sums[bid] += amt
            # subject_code 在扩展 DDL 上被误建成全局唯一，须全局不重复
            line_rows.append((bid, f"S{bid}_{j}", f"科目{j}", amt, "active", None))
    n = await insert_many(
        conn,
        "fin_budget_line",
        ["budget_id", "subject_code", "subject_name", "amount", "status", "remark"],
        line_rows,
    )
    ctx.note("fin_budget_line", n)
    for bid, total in budget_sums.items():
        used = d(float(total) * rng.uniform(0.3, 0.95))
        await conn.execute(
            "UPDATE company.fin_budget_year SET budget_amount=$1, used_amount=$2 WHERE id=$3",
            total,
            used,
            bid,
        )
    ctx.note("fin_budget_year", len(budget_ids))

    # 固定资产 + 折旧
    assets = []
    for i in range(1, 501):
        assets.append(
            (
                f"FA{i:04d}",
                f"固定资产{i}",
                rng.choice(["电脑", "家具", "服务器", "车辆"]),
                rand_date(rng, START, date(2025, 6, 1)),
                d(rng.uniform(2000, 80000)),
                pick(emps, rng),
                pick(depts, rng),
                "active",
                None,
            )
        )
    asset_ids = await insert_returning_ids(
        conn,
        "fin_fixed_asset",
        [
            "asset_code",
            "asset_name",
            "category",
            "purchase_date",
            "original_value",
            "custodian_emp_id",
            "dept_id",
            "status",
            "remark",
        ],
        assets,
    )
    ctx.set_ids("fin_fixed_asset", asset_ids)

    rows = []
    months = [f"{m.year}-{m.month:02d}" for m in iter_months(START, END)]
    for aid in asset_ids:
        for ym in rng.sample(months, k=min(24, len(months))):
            rows.append((aid, ym, d(rng.uniform(50, 800)), "active", None))
            if len(rows) >= FACT_N:
                break
        if len(rows) >= FACT_N:
            break
    rows = rows[:FACT_N]
    n = await insert_many(
        conn, "fin_asset_depr", ["asset_id", "year_month", "depr_amount", "status", "remark"], rows
    )
    ctx.note("fin_asset_depr", n)

    # 借款 + 核销（核销合计 ≤ 借款）
    loans = []
    for i in range(1, 2001):
        loans.append(
            (
                f"LN{i:05d}",
                pick(emps, rng),
                d(rng.uniform(1000, 30000)),
                rand_date(rng),
                rand_date(rng),
                "active",
                None,
            )
        )
    loan_ids = await insert_returning_ids(
        conn,
        "fin_loan",
        ["loan_no", "emp_id", "amount", "loan_date", "due_date", "status", "remark"],
        loans,
    )
    ctx.set_ids("fin_loan", loan_ids)

    # 读回金额
    loan_amts = {
        r["id"]: r["amount"]
        for r in await conn.fetch("SELECT id, amount FROM company.fin_loan")
    }
    repay_rows = []
    for lid in loan_ids:
        remain = float(loan_amts[lid])
        for _ in range(rng.randint(1, 3)):
            if remain <= 0:
                break
            part = min(remain, remain * rng.uniform(0.2, 0.6))
            remain -= part
            repay_rows.append(
                (lid, d(part), rand_date(rng), pick_opt(claims, rng, 0.3), "active", None)
            )
            if len(repay_rows) >= FACT_N:
                break
        if len(repay_rows) >= FACT_N:
            break
    repay_rows = repay_rows[:FACT_N]
    n = await insert_many(
        conn,
        "fin_loan_repay",
        ["loan_id", "repay_amount", "repay_date", "reimburse_id", "status", "remark"],
        repay_rows,
    )
    ctx.note("fin_loan_repay", n)

    # 税期
    rows = []
    for ym in iter_months(START, END):
        for tax in ("VAT", "CIT", "IIT"):
            pay = d(rng.uniform(1000, 90000))
            rows.append(
                (f"{ym.year}-{ym.month:02d}", tax, pay, d(float(pay) * rng.uniform(0.5, 1.0)), "active", None)
            )
    n = await insert_many(
        conn,
        "fin_tax_period",
        ["year_month", "tax_type", "payable_amount", "paid_amount", "status", "remark"],
        rows,
    )
    ctx.note("fin_tax_period", n)

    accts = []
    for i in range(1, 11):
        accts.append(
            (
                f"BA{i:02d}",
                f"公司账户{i}",
                rng.choice(["工行", "中行", "招行"]),
                f"3301{i:012d}",
                pick(cos, rng),
                "active",
                None,
            )
        )
    acct_ids = await insert_returning_ids(
        conn,
        "fin_bank_account",
        ["acct_code", "acct_name", "bank_name", "account_no", "company_id", "status", "remark"],
        accts,
    )
    ctx.set_ids("fin_bank_account", acct_ids)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (
                pick(acct_ids, rng),
                rand_date(rng),
                rng.choice(["in", "out"]),
                d(rng.uniform(10, 500000)),
                f"对方{i % 200}",
                f"REF{i:08d}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "fin_bank_txn",
        ["acct_id", "txn_date", "direction", "amount", "counterpart", "ref_no", "status", "remark"],
        rows,
    )
    ctx.note("fin_bank_txn", n)

    rows = []
    for i in range(FACT_N):
        ym = rng.choice(list(iter_months(START, END)))
        rows.append(
            (
                f"{ym.year}-{ym.month:02d}",
                pick(depts, rng),
                pick(depts, rng),
                d(rng.uniform(100, 20000)),
                f"CA{i:06d}",  # DDL 对 subject_code 建了全局唯一
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "fin_cost_allocation",
        ["year_month", "from_dept_id", "to_dept_id", "amount", "subject_code", "status", "remark"],
        rows,
    )
    ctx.note("fin_cost_allocation", n)

    gl = []
    for i in range(1, 61):
        gl.append(
            (
                f"1001{i:02d}",
                f"会计科目{i}",
                rng.choice(["asset", "liability", "equity", "income", "expense"]),
                None if i < 10 else f"1001{(i // 10):02d}",
                "active",
                None,
            )
        )
    gl_ids = await insert_returning_ids(
        conn,
        "fin_gl_account",
        ["acct_code", "acct_name", "acct_type", "parent_code", "status", "remark"],
        gl,
    )
    ctx.set_ids("fin_gl_account", gl_ids)

    # 凭证头 + 分录（借贷平衡）
    journals = []
    for i in range(1, 4001):
        vd = rand_date(rng)
        journals.append(
            (
                f"JV{vd.year}{i:05d}",
                vd,
                f"{vd.year}-{vd.month:02d}",
                pick(emps, rng),
                "active",
                None,
            )
        )
    journal_ids = await insert_returning_ids(
        conn,
        "fin_journal",
        ["voucher_no", "voucher_date", "period", "created_by", "status", "remark"],
        journals,
    )
    ctx.set_ids("fin_journal", journal_ids)

    line_rows = []
    for jid in journal_ids:
        amt = d(rng.uniform(100, 50000))
        a1, a2 = pick(gl_ids, rng), pick(gl_ids, rng)
        line_rows.append((jid, a1, amt, d(0), f"借方摘要{jid}", "active", None))
        line_rows.append((jid, a2, d(0), amt, f"贷方摘要{jid}", "active", None))
        if len(line_rows) >= FACT_N * 2:
            # 控制明细规模约 1 万～2 万
            break
    # 截断到约 10000 行（成对）
    line_rows = line_rows[: (FACT_N // 2) * 2]
    n = await insert_many(
        conn,
        "fin_journal_line",
        ["journal_id", "acct_id", "debit", "credit", "summary", "status", "remark"],
        line_rows,
    )
    ctx.note("fin_journal_line", n)
    # 未写入分录的凭证头仍保留（演示允许空凭证？更好删掉）——保持头多、线约 1 万

    rows = []
    cur = START
    while cur <= END and len(rows) < 800:
        for ccy in ("USD", "EUR", "HKD", "JPY"):
            rows.append((ccy, cur, d(rng.uniform(0.05, 8.0)), "active", None))
        cur += timedelta(days=7)
    n = await insert_many(
        conn, "fin_exchange_rate", ["currency", "rate_date", "rate", "status", "remark"], rows
    )
    ctx.note("fin_exchange_rate", n)

    petty = []
    for i in range(20):
        petty.append((pick(depts, rng), pick(emps, rng), d(rng.uniform(1000, 20000)), "active", None))
    petty_ids = await insert_returning_ids(
        conn, "fin_petty_cash", ["dept_id", "keeper_emp_id", "balance", "status", "remark"], petty
    )
    ctx.set_ids("fin_petty_cash", petty_ids)

    rows = []
    for _ in range(FACT_N):
        rows.append(
            (
                pick(petty_ids, rng),
                rand_date(rng),
                rng.choice(["in", "out"]),
                d(rng.uniform(50, 3000)),
                f"事由{rng.randint(1,9999)}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "fin_petty_cash_txn",
        ["petty_id", "txn_date", "direction", "amount", "reason", "status", "remark"],
        rows,
    )
    ctx.note("fin_petty_cash_txn", n)


async def seed_crm_sal(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    custs = ctx.ids["crm_customer"]
    prods = ctx.ids["prd_product"]
    orders = ctx.ids["sal_sales_order"]
    depts = ctx.ids["org_department"]
    projs = ctx.ids["prj_project"]

    # 联系人 / SLA
    rows = []
    for cid in custs:
        for j in range(rng.randint(1, 3)):
            rows.append(
                (
                    cid,
                    f"联系人{cid}-{j}",
                    rng.choice(["经理", "总监", "专员"]),
                    f"136{cid:08d}"[-11:],
                    f"c{cid}_{j}@corp.example",
                    j == 0,
                    "active",
                    None,
                )
            )
    n = await insert_many(
        conn,
        "crm_contact",
        ["customer_id", "contact_name", "title", "phone", "email", "is_primary", "status", "remark"],
        rows,
    )
    ctx.note("crm_contact", n)

    rows = []
    for cid in custs:
        rows.append(
            (cid, rng.choice(["gold", "silver", "standard"]), rng.randint(1, 24), rng.randint(24, 168), "active", None)
        )
    n = await insert_many(
        conn,
        "crm_sla",
        ["customer_id", "sla_level", "response_hours", "resolve_hours", "status", "remark"],
        rows,
    )
    ctx.note("crm_sla", n)

    leads = []
    for i in range(1, 4001):
        leads.append(
            (
                f"LEAD{i:05d}",
                f"线索{i}",
                rng.choice(["官网", "展会", "转介", "广告"]),
                pick(emps, rng),
                pick_opt(custs, rng, 0.4),
                "active",
                None,
            )
        )
    lead_ids = await insert_returning_ids(
        conn,
        "crm_lead",
        ["lead_code", "lead_name", "source", "owner_emp_id", "customer_id", "status", "remark"],
        leads,
    )
    ctx.set_ids("crm_lead", lead_ids)

    opps = []
    for i in range(1, 3001):
        opps.append(
            (
                f"OPP{i:05d}",
                f"商机{i}",
                pick(custs, rng),
                pick(emps, rng),
                d(rng.uniform(10000, 2000000)),
                rng.choice(["qualify", "propose", "negotiate", "won", "lost"]),
                rand_date(rng),
                "active",
                None,
            )
        )
    opp_ids = await insert_returning_ids(
        conn,
        "crm_opportunity",
        [
            "opp_code",
            "opp_name",
            "customer_id",
            "owner_emp_id",
            "amount",
            "stage",
            "close_date",
            "status",
            "remark",
        ],
        opps,
    )
    ctx.set_ids("crm_opportunity", opp_ids)

    for table, n_target, builder in [
        (
            "crm_activity",
            FACT_N,
            lambda i: (
                pick(custs, rng),
                pick_opt(opp_ids, rng, 0.6),
                pick(emps, rng),
                rng.choice(["call", "email", "meeting", "demo"]),
                rand_ts(rng),
                f"跟进内容{i}",
                "active",
                None,
            ),
        ),
        (
            "crm_visit",
            FACT_N,
            lambda i: (
                pick(custs, rng),
                pick(emps, rng),
                rand_date(rng),
                f"目的{i}",
                f"结果{i}",
                "active",
                None,
            ),
        ),
        (
            "crm_complaint",
            2000,
            lambda i: (
                pick(custs, rng),
                pick_opt(projs, rng, 0.5),
                f"投诉{i}",
                rng.choice(["low", "mid", "high"]),
                pick(emps, rng),
                "active",
                None,
            ),
        ),
    ]:
        cols_map = {
            "crm_activity": [
                "customer_id",
                "opp_id",
                "emp_id",
                "activity_type",
                "activity_at",
                "content",
                "status",
                "remark",
            ],
            "crm_visit": ["customer_id", "emp_id", "visit_date", "purpose", "result", "status", "remark"],
            "crm_complaint": [
                "customer_id",
                "project_id",
                "title",
                "severity_level",
                "handler_emp_id",
                "status",
                "remark",
            ],
        }
        rows = [builder(i) for i in range(n_target)]
        n = await insert_many(conn, table, cols_map[table], rows)
        ctx.note(table, n)

    # 报价头+明细干净
    quotes = []
    for i in range(1, 2501):
        quotes.append(
            (
                f"QT{i:05d}",
                f"报价{i}",
                pick(custs, rng),
                pick(emps, rng),
                d(0),
                rand_date(rng),
                "active",
                None,
            )
        )
    quote_ids = await insert_returning_ids(
        conn,
        "sal_quote",
        [
            "quote_code",
            "quote_name",
            "customer_id",
            "owner_emp_id",
            "total_amount",
            "valid_until",
            "status",
            "remark",
        ],
        quotes,
    )
    ctx.set_ids("sal_quote", quote_ids)

    item_rows = []
    sums: dict[int, Decimal] = {qid: Decimal("0") for qid in quote_ids}
    for qid in quote_ids:
        for _ in range(rng.randint(1, 4)):
            qty = Decimal(str(rng.randint(1, 20)))
            price = d(rng.uniform(100, 50000))
            assert price is not None
            amt = (qty * price).quantize(Decimal("0.01"))
            sums[qid] += amt
            item_rows.append((qid, pick(prods, rng), qty, price, amt, "active", None))
    n = await insert_many(
        conn,
        "sal_quote_item",
        ["quote_id", "product_id", "qty", "unit_price", "amount", "status", "remark"],
        item_rows,
    )
    ctx.note("sal_quote_item", n)
    for qid, total in sums.items():
        await conn.execute("UPDATE company.sal_quote SET total_amount=$1 WHERE id=$2", total, qid)

    # 合同 + 里程碑（里程碑合计 = 合同金额）
    contracts = []
    for i in range(1, 1501):
        contracts.append(
            (
                f"SC{i:05d}",
                f"销售合同{i}",
                pick(custs, rng),
                pick_opt(orders, rng, 0.7),
                rand_date(rng),
                d(rng.uniform(20000, 800000)),
                pick(emps, rng),
                "active",
                None,
            )
        )
    contract_ids = await insert_returning_ids(
        conn,
        "sal_contract",
        [
            "contract_code",
            "contract_name",
            "customer_id",
            "order_id",
            "sign_date",
            "amount",
            "owner_emp_id",
            "status",
            "remark",
        ],
        contracts,
    )
    ctx.set_ids("sal_contract", contract_ids)
    contract_amts = {
        r["id"]: r["amount"]
        for r in await conn.fetch("SELECT id, amount FROM company.sal_contract")
    }
    ms_rows = []
    for cid in contract_ids:
        total = float(contract_amts[cid])
        parts = 3
        acc = 0.0
        for j in range(parts):
            if j == parts - 1:
                amt = d(total - acc)
            else:
                part = total / parts
                amt = d(part)
                acc += float(amt)
            received = d(float(amt) * rng.uniform(0, 1))
            ms_rows.append(
                (cid, f"里程碑{j+1}", rand_date(rng), amt, received, "active", None)
            )
    n = await insert_many(
        conn,
        "sal_contract_milestone",
        ["contract_id", "milestone_name", "due_date", "amount", "received_amount", "status", "remark"],
        ms_rows,
    )
    ctx.note("sal_contract_milestone", n)

    # 交付头+明细
    deliveries = []
    for i in range(1, 3001):
        deliveries.append(
            (
                f"DL{i:05d}",
                f"交付{i}",
                pick_opt(orders, rng, 0.9),
                rand_date(rng),
                f"收货人{i % 100}",
                "active",
                None,
            )
        )
    delivery_ids = await insert_returning_ids(
        conn,
        "sal_delivery",
        ["delivery_code", "delivery_name", "order_id", "delivery_date", "receiver", "status", "remark"],
        deliveries,
    )
    ctx.set_ids("sal_delivery", delivery_ids)
    rows = []
    for did in delivery_ids:
        for _ in range(rng.randint(1, 3)):
            rows.append((did, pick(prods, rng), d(rng.uniform(1, 50)), "active", None))
    n = await insert_many(
        conn, "sal_delivery_item", ["delivery_id", "product_id", "qty", "status", "remark"], rows
    )
    ctx.note("sal_delivery_item", n)

    rows = []
    for i in range(1, 1501):
        rows.append(
            (
                f"RT{i:05d}",
                f"退货{i}",
                pick_opt(orders, rng, 0.9),
                rand_date(rng),
                f"原因{i % 50}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "sal_return",
        ["return_code", "return_name", "order_id", "return_date", "reason", "status", "remark"],
        rows,
    )
    ctx.note("sal_return", n)

    rules = []
    for i in range(1, 11):
        rules.append((f"CR{i:02d}", f"提成规则{i}", d(rng.uniform(1, 15)), pick_opt(prods, rng, 0.8), "active", None))
    rule_ids = await insert_returning_ids(
        conn,
        "sal_commission_rule",
        ["rule_code", "rule_name", "rate_pct", "product_id", "status", "remark"],
        rules,
    )
    ctx.set_ids("sal_commission_rule", rule_ids)

    rows = []
    for i in range(FACT_N):
        ym = rng.choice(list(iter_months(START, END)))
        rows.append(
            (
                pick(emps, rng),
                pick_opt(orders, rng, 0.9),
                f"{ym.year}-{ym.month:02d}",
                d(rng.uniform(100, 20000)),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "sal_commission",
        ["emp_id", "order_id", "year_month", "amount", "status", "remark"],
        rows,
    )
    ctx.note("sal_commission", n)

    plists = []
    for i in range(1, 7):
        plists.append(
            (
                f"PL{i:02d}",
                f"价格表{i}",
                "CNY",
                START,
                END,
                "active",
                None,
            )
        )
    plist_ids = await insert_returning_ids(
        conn,
        "sal_price_list",
        ["plist_code", "plist_name", "currency", "effective_from", "effective_to", "status", "remark"],
        plists,
    )
    ctx.set_ids("sal_price_list", plist_ids)
    rows = []
    for pid in plist_ids:
        for prod in prods:
            rows.append((pid, prod, d(rng.uniform(100, 100000)), "active", None))
    n = await insert_many(
        conn, "sal_price_list_item", ["plist_id", "product_id", "unit_price", "status", "remark"], rows
    )
    ctx.note("sal_price_list_item", n)

    rows = []
    for i in range(FACT_N):
        ym = rng.choice(list(iter_months(START, END)))
        target = d(rng.uniform(50000, 500000))
        rows.append(
            (
                pick_opt(emps, rng, 0.8),
                pick_opt(depts, rng, 0.8),
                f"{ym.year}-{ym.month:02d}",
                target,
                d(float(target) * rng.uniform(0.4, 1.2)),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "sal_target",
        ["emp_id", "dept_id", "year_month", "target_amount", "actual_amount", "status", "remark"],
        rows,
    )
    ctx.note("sal_target", n)

    chans = []
    for i in range(1, 13):
        chans.append((f"CH{i:02d}", f"渠道{i}", rng.choice(["直销", "伙伴", "电商"]), "active", None))
    chan_ids = await insert_returning_ids(
        conn, "sal_channel", ["channel_code", "channel_name", "channel_type", "status", "remark"], chans
    )
    ctx.set_ids("sal_channel", chan_ids)


async def seed_prd_prj(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    prods = ctx.ids["prd_product"]
    projs = ctx.ids["prj_project"]
    custs = ctx.ids["crm_customer"]

    lines = []
    for i in range(1, 9):
        lines.append((f"PLINE{i}", f"产品线{i}", pick(emps, rng), "active", None))
    line_ids = await insert_returning_ids(
        conn, "prd_product_line", ["line_code", "line_name", "owner_emp_id", "status", "remark"], lines
    )
    ctx.set_ids("prd_product_line", line_ids)

    rows = []
    for pid in prods:
        for v in range(1, 6):
            rows.append((pid, f"v{v}.0", rand_date(rng), f"变更说明{v}", "active", None))
    n = await insert_many(
        conn,
        "prd_product_version",
        ["product_id", "version_no", "release_date", "changelog", "status", "remark"],
        rows,
    )
    ctx.note("prd_product_version", n)

    rows = []
    feat_i = 0
    for pid in prods:
        for j in range(20):
            feat_i += 1
            rows.append((pid, f"FEAT{feat_i:05d}", f"功能{j}", "active", None))
    n = await insert_many(
        conn, "prd_feature", ["product_id", "feature_code", "feature_name", "status", "remark"], rows
    )
    ctx.note("prd_feature", n)

    rows = []
    for i in range(2000):
        rows.append(
            (
                pick(prods, rng),
                pick(custs, rng),
                f"KEY-{i:06d}",
                rng.randint(5, 500),
                rand_date(rng, date(2025, 1, 1), date(2028, 12, 31)),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "prd_license",
        ["product_id", "customer_id", "license_key", "seat_count", "expire_date", "status", "remark"],
        rows,
    )
    ctx.note("prd_license", n)

    rows = []
    for pid in prods:
        for j in range(15):
            rows.append(
                (pid, f"路线图{j}", f"202{4+j%3}Q{(j%4)+1}", rng.choice(["P0", "P1", "P2"]), "active", None)
            )
    n = await insert_many(
        conn,
        "prd_roadmap",
        ["product_id", "item_name", "target_quarter", "priority", "status", "remark"],
        rows,
    )
    ctx.note("prd_roadmap", n)

    # 项目扩展
    rows = []
    for pid in projs:
        for j in range(rng.randint(2, 5)):
            rows.append(
                (pid, f"里程碑{j+1}", rand_date(rng), rand_date(rng) if rng.random() < 0.6 else None, "active", None)
            )
    n = await insert_many(
        conn,
        "prj_milestone",
        ["project_id", "milestone_name", "plan_date", "actual_date", "status", "remark"],
        rows,
    )
    ctx.note("prj_milestone", n)

    for table, n_target, cols, builder in [
        (
            "prj_task",
            FACT_N,
            ["project_id", "task_name", "assignee_emp_id", "plan_start", "plan_end", "progress_pct", "status", "remark"],
            lambda i: (
                pick(projs, rng),
                f"任务{i}",
                pick(emps, rng),
                rand_date(rng),
                rand_date(rng),
                d(rng.uniform(0, 100)),
                "active",
                None,
            ),
        ),
        (
            "prj_risk",
            3000,
            ["project_id", "risk_title", "level", "owner_emp_id", "mitigation", "status", "remark"],
            lambda i: (
                pick(projs, rng),
                f"风险{i}",
                rng.choice(["low", "mid", "high"]),
                pick(emps, rng),
                f"缓解{i}",
                "active",
                None,
            ),
        ),
        (
            "prj_issue",
            FACT_N,
            ["project_id", "title", "severity", "reporter_emp_id", "assignee_emp_id", "status", "remark"],
            lambda i: (
                pick(projs, rng),
                f"问题{i}",
                rng.choice(["low", "mid", "high"]),
                pick(emps, rng),
                pick(emps, rng),
                "active",
                None,
            ),
        ),
        (
            "prj_change_request",
            2000,
            ["project_id", "title", "impact", "requester_emp_id", "status", "remark"],
            lambda i: (pick(projs, rng), f"变更{i}", f"影响{i}", pick(emps, rng), "active", None),
        ),
        (
            "prj_document",
            5000,
            ["project_id", "doc_name", "doc_type", "url", "uploader_emp_id", "status", "remark"],
            lambda i: (
                pick(projs, rng),
                f"文档{i}",
                rng.choice(["design", "minutes", "contract"]),
                f"https://docs.example/{i}",
                pick(emps, rng),
                "active",
                None,
            ),
        ),
        (
            "prj_weekly_report",
            FACT_N,
            ["project_id", "week_start", "author_emp_id", "content", "status", "remark"],
            lambda i: (pick(projs, rng), rand_date(rng), pick(emps, rng), f"周报{i}", "active", None),
        ),
    ]:
        rows = [builder(i) for i in range(n_target)]
        n = await insert_many(conn, table, cols, rows)
        ctx.note(table, n)

    rows = []
    for pid in projs:
        rows.append(
            (pid, pick_opt(emps, rng, 0.5), f"外部干系人{pid}" if rng.random() < 0.5 else None, rng.choice(["sponsor", "user", "pm"]), "active", None)
        )
        rows.append((pid, pick(emps, rng), None, "owner", "active", None))
    n = await insert_many(
        conn, "prj_stakeholder", ["project_id", "emp_id", "external_name", "role", "status", "remark"], rows
    )
    ctx.note("prj_stakeholder", n)

    rows = []
    for pid in projs:
        rows.append((pid, rand_date(rng), rng.choice(["pass", "conditional", "fail"]), f"签字人{pid}", "active", None))
    n = await insert_many(
        conn, "prj_acceptance", ["project_id", "accept_date", "result", "customer_signer", "status", "remark"], rows
    )
    ctx.note("prj_acceptance", n)

    rows = []
    for pid in projs:
        s = rand_date(rng)
        rows.append((pid, s, s + timedelta(days=365), "质保条款摘要", "active", None))
    n = await insert_many(
        conn, "prj_warranty", ["project_id", "start_date", "end_date", "terms", "status", "remark"], rows
    )
    ctx.note("prj_warranty", n)


async def seed_scm(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    depts = ctx.ids["org_department"]
    vendors = ctx.ids["fin_vendor"]
    offices = ctx.ids["org_office"]

    reqs = []
    for i in range(1, 3001):
        reqs.append(
            (
                f"PR{i:05d}",
                f"采购申请{i}",
                pick(emps, rng),
                pick(depts, rng),
                d(0),
                "active",
                None,
            )
        )
    req_ids = await insert_returning_ids(
        conn,
        "scm_purchase_req",
        ["req_code", "req_name", "applicant_emp_id", "dept_id", "total_amount", "status", "remark"],
        reqs,
    )
    ctx.set_ids("scm_purchase_req", req_ids)

    item_rows = []
    sums: dict[int, Decimal] = {rid: Decimal("0") for rid in req_ids}
    for rid in req_ids:
        for j in range(rng.randint(1, 4)):
            qty = Decimal(str(rng.randint(1, 100)))
            price = d(rng.uniform(10, 5000))
            assert price is not None
            amt = (qty * price).quantize(Decimal("0.01"))
            sums[rid] += amt
            item_rows.append((rid, f"物资{j}", qty, price, "active", None))
    n = await insert_many(
        conn,
        "scm_purchase_req_item",
        ["req_id", "item_name", "qty", "unit_price", "status", "remark"],
        item_rows,
    )
    ctx.note("scm_purchase_req_item", n)
    for rid, total in sums.items():
        await conn.execute("UPDATE company.scm_purchase_req SET total_amount=$1 WHERE id=$2", total, rid)

    pos = []
    for i in range(1, 2501):
        pos.append(
            (
                f"PO{i:05d}",
                f"采购订单{i}",
                pick(vendors, rng),
                pick_opt(req_ids, rng, 0.8),
                d(0),
                pick(emps, rng),
                "active",
                None,
            )
        )
    po_ids = await insert_returning_ids(
        conn,
        "scm_purchase_order",
        ["po_code", "po_name", "vendor_id", "req_id", "total_amount", "buyer_emp_id", "status", "remark"],
        pos,
    )
    ctx.set_ids("scm_purchase_order", po_ids)

    item_rows = []
    sums = {pid: Decimal("0") for pid in po_ids}
    for pid in po_ids:
        for j in range(rng.randint(1, 5)):
            qty = Decimal(str(rng.randint(1, 200)))
            price = d(rng.uniform(10, 8000))
            assert price is not None
            amt = (qty * price).quantize(Decimal("0.01"))
            sums[pid] += amt
            item_rows.append((pid, f"采购物资{j}", qty, price, amt, "active", None))
    n = await insert_many(
        conn,
        "scm_purchase_order_item",
        ["po_id", "item_name", "qty", "unit_price", "amount", "status", "remark"],
        item_rows,
    )
    ctx.note("scm_purchase_order_item", n)
    for pid, total in sums.items():
        await conn.execute("UPDATE company.scm_purchase_order SET total_amount=$1 WHERE id=$2", total, pid)

    whs = []
    for i in range(1, 9):
        whs.append((f"WH{i:02d}", f"仓库{i}", pick_opt(offices, rng, 0.9), "active", None))
    wh_ids = await insert_returning_ids(
        conn, "scm_warehouse", ["wh_code", "wh_name", "office_id", "status", "remark"], whs
    )
    ctx.set_ids("scm_warehouse", wh_ids)

    rows = []
    for i in range(1, 4001):
        rows.append(
            (
                f"GRN{i:05d}",
                f"入库{i}",
                pick_opt(po_ids, rng, 0.9),
                rand_date(rng),
                pick(wh_ids, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "scm_receipt",
        ["grn_code", "grn_name", "po_id", "receipt_date", "warehouse_id", "status", "remark"],
        rows,
    )
    ctx.note("scm_receipt", n)

    mats = []
    for i in range(1, 201):
        mats.append((f"MAT{i:04d}", f"物料{i}", rng.choice(["EA", "KG", "BOX"]), rng.choice(["IT", "办公", "工程"]), "active", None))
    mat_ids = await insert_returning_ids(
        conn, "scm_material", ["mat_code", "mat_name", "uom", "category", "status", "remark"], mats
    )
    ctx.set_ids("scm_material", mat_ids)

    rows = []
    for idx, wid in enumerate(wh_ids):
        for i in range(1, 201):
            # DDL 对 sku_code 全局唯一（含跨仓）
            rows.append((wid, f"INV-W{idx}-S{i:03d}", f"库存品{i}", d(rng.uniform(0, 5000)), "active", None))
    n = await insert_many(
        conn,
        "scm_inventory",
        ["warehouse_id", "sku_code", "sku_name", "qty_on_hand", "status", "remark"],
        rows,
    )
    ctx.note("scm_inventory", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (
                pick(wh_ids, rng),
                f"TXN-SKU-{i:06d}",  # inventory_txn.sku_code 也被建成全局唯一
                rng.choice(["in", "out", "adjust"]),
                d(rng.uniform(1, 100)),
                rand_date(rng),
                f"REF{i:06d}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "scm_inventory_txn",
        ["warehouse_id", "sku_code", "txn_type", "qty", "txn_date", "ref_no", "status", "remark"],
        rows,
    )
    ctx.note("scm_inventory_txn", n)

    rows = []
    for i in range(3000):
        ym = rng.choice(list(iter_months(START, END)))
        rows.append(
            (
                pick(vendors, rng),
                f"{ym.year}-{ym.month:02d}",
                d(rng.uniform(60, 100)),
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "scm_vendor_eval",
        ["vendor_id", "year_month", "score", "evaluator_emp_id", "status", "remark"],
        rows,
    )
    ctx.note("scm_vendor_eval", n)


async def seed_it_misc(conn: asyncpg.Connection, ctx: SeedCtx) -> None:
    rng = ctx.rng
    emps = ctx.ids["hr_employee"]
    offices = ctx.ids["org_office"]
    projs = ctx.ids["prj_project"]
    prods = ctx.ids["prd_product"]
    custs = ctx.ids["crm_customer"]
    vendors = ctx.ids["fin_vendor"]
    leads = ctx.ids.get("crm_lead", [])

    assets = []
    for i in range(1, 2001):
        assets.append(
            (
                f"IT{i:05d}",
                f"IT资产{i}",
                rng.choice(["laptop", "monitor", "phone", "server"]),
                f"SN{i:08d}",
                pick_opt(emps, rng, 0.8),
                pick_opt(offices, rng, 0.8),
                "active",
                None,
            )
        )
    asset_ids = await insert_returning_ids(
        conn,
        "itm_asset",
        ["asset_code", "asset_name", "asset_type", "sn", "assignee_emp_id", "office_id", "status", "remark"],
        assets,
    )
    ctx.set_ids("itm_asset", asset_ids)

    rows = []
    for i in range(5000):
        rows.append(
            (
                pick(asset_ids, rng),
                pick(emps, rng),
                rand_date(rng),
                rand_date(rng) if rng.random() < 0.4 else None,
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "itm_asset_assign",
        ["asset_id", "emp_id", "assign_date", "return_date", "status", "remark"],
        rows,
    )
    ctx.note("itm_asset_assign", n)

    tickets = []
    for i in range(1, FACT_N + 1):
        tickets.append(
            (
                f"TK{i:06d}",
                f"工单{i}",
                pick(emps, rng),
                pick(emps, rng),
                rng.choice(["hardware", "software", "network", "account"]),
                rng.choice(["low", "mid", "high"]),
                "active",
                None,
            )
        )
    ticket_ids = await insert_returning_ids(
        conn,
        "itm_ticket",
        [
            "ticket_code",
            "ticket_name",
            "requester_emp_id",
            "assignee_emp_id",
            "category",
            "priority",
            "status",
            "remark",
        ],
        tickets,
    )
    ctx.set_ids("itm_ticket", ticket_ids)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (pick(ticket_ids, rng), pick(emps, rng), f"评论{i}", rand_ts(rng), "active", None)
        )
    n = await insert_many(
        conn,
        "itm_ticket_comment",
        ["ticket_id", "author_emp_id", "content", "commented_at", "status", "remark"],
        rows,
    )
    ctx.note("itm_ticket_comment", n)

    systems = []
    for i in range(1, 26):
        systems.append(
            (
                f"SYS{i:02d}",
                f"业务系统{i}",
                pick(emps, rng),
                rng.choice(["prod", "staging", "dev"]),
                f"https://sys{i}.example.com",
                "active",
                None,
            )
        )
    sys_ids = await insert_returning_ids(
        conn,
        "itm_system",
        ["sys_code", "sys_name", "owner_emp_id", "env", "url", "status", "remark"],
        systems,
    )
    ctx.set_ids("itm_system", sys_ids)

    for table, n_target, cols, builder in [
        (
            "itm_deploy",
            3000,
            ["system_id", "version_no", "deploy_at", "operator_emp_id", "result", "status", "remark"],
            lambda i: (
                pick(sys_ids, rng),
                f"dep-{i:05d}",  # DDL 对 version_no 全局唯一
                rand_ts(rng),
                pick(emps, rng),
                rng.choice(["success", "rollback", "failed"]),
                "active",
                None,
            ),
        ),
        (
            "itm_incident",
            2000,
            ["inc_code", "inc_name", "system_id", "severity", "started_at", "resolved_at", "commander_emp_id", "status", "remark"],
            lambda i: (
                f"INC{i:05d}",
                f"故障{i}",
                pick_opt(sys_ids, rng, 0.9),
                rng.choice(["sev1", "sev2", "sev3"]),
                rand_ts(rng),
                rand_ts(rng),
                pick(emps, rng),
                "active",
                None,
            ),
        ),
        (
            "itm_change",
            3000,
            ["chg_code", "chg_name", "system_id", "planned_at", "risk_level", "applicant_emp_id", "status", "remark"],
            lambda i: (
                f"CHG{i:05d}",
                f"变更{i}",
                pick_opt(sys_ids, rng, 0.9),
                rand_ts(rng),
                rng.choice(["low", "mid", "high"]),
                pick(emps, rng),
                "active",
                None,
            ),
        ),
        (
            "itm_account",
            FACT_N,
            ["system_id", "emp_id", "login_name", "role_name", "status", "remark"],
            lambda i: (pick(sys_ids, rng), pick(emps, rng), f"u{i}", rng.choice(["user", "admin", "ops"]), "active", None),
        ),
        (
            "itm_access_request",
            5000,
            ["system_id", "emp_id", "role_name", "reason", "status", "remark"],
            lambda i: (pick(sys_ids, rng), pick(emps, rng), rng.choice(["user", "admin"]), f"事由{i}", "active", None),
        ),
    ]:
        # itm_incident / itm_change 用 code_name：列名在 schema 里是 inc_code/inc_name 等
        rows = [builder(i) for i in range(1, n_target + 1)]
        n = await insert_many(conn, table, cols, rows)
        ctx.note(table, n)

    pols = []
    for i in range(1, 21):
        pols.append((f"POL{i:02d}", f"安全策略{i}", rng.choice(["access", "password", "data"]), f"策略正文{i}", "active", None))
    pol_ids = await insert_returning_ids(
        conn, "sec_policy", ["pol_code", "pol_name", "policy_type", "content", "status", "remark"], pols
    )
    ctx.set_ids("sec_policy", pol_ids)

    rows = []
    for i in range(1, 1501):
        rows.append(
            (
                f"VULN{i:05d}",
                f"漏洞{i}",
                pick_opt(sys_ids, rng, 0.9),
                rng.choice(["low", "mid", "high", "critical"]),
                rand_date(rng),
                rand_date(rng) if rng.random() < 0.5 else None,
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "sec_vulnerability",
        ["vuln_code", "vuln_name", "system_id", "severity", "discovered_at", "fixed_at", "status", "remark"],
        rows,
    )
    ctx.note("sec_vulnerability", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (
                pick_opt(sys_ids, rng, 0.9),
                pick(emps, rng),
                rng.choice(["login", "export", "admin", "download"]),
                rand_ts(rng),
                f"10.1.{i % 255}.{(i * 3) % 255}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "sec_audit_log",
        ["system_id", "emp_id", "action", "acted_at", "ip_addr", "status", "remark"],
        rows,
    )
    ctx.note("sec_audit_log", n)

    classes = []
    for i in range(1, 9):
        classes.append((f"DC{i}", f"数据分类{i}", i, "active", None))
    class_ids = await insert_returning_ids(
        conn, "sec_data_class", ["class_code", "class_name", "level_no", "status", "remark"], classes
    )
    ctx.set_ids("sec_data_class", class_ids)

    # 市场/行政/法务/质量/知识/运维
    camps = []
    for i in range(1, 401):
        s = rand_date(rng)
        camps.append(
            (
                f"CAMP{i:04d}",
                f"市场活动{i}",
                s,
                s + timedelta(days=rng.randint(1, 14)),
                d(rng.uniform(5000, 200000)),
                pick(emps, rng),
                "active",
                None,
            )
        )
    camp_ids = await insert_returning_ids(
        conn,
        "mkt_campaign",
        ["camp_code", "camp_name", "start_date", "end_date", "budget", "owner_emp_id", "status", "remark"],
        camps,
    )
    ctx.set_ids("mkt_campaign", camp_ids)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (pick(camp_ids, rng), pick_opt(leads, rng, 0.7) if leads else None, rng.choice(["web", "offline", "partner"]), "active", None)
        )
    n = await insert_many(
        conn, "mkt_campaign_lead", ["camp_id", "lead_id", "channel", "status", "remark"], rows
    )
    ctx.note("mkt_campaign_lead", n)

    rows = []
    for i in range(1, 201):
        rows.append(
            (
                f"CT{i:04d}",
                f"素材{i}",
                rng.choice(["article", "video", "ppt"]),
                f"https://cdn.example/{i}",
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "mkt_content",
        ["content_code", "content_name", "content_type", "url", "author_emp_id", "status", "remark"],
        rows,
    )
    ctx.note("mkt_content", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (pick(camp_ids, rng), f"报名人{i}", f"单位{i % 300}", f"135{i:08d}"[-11:], "active", None)
        )
    n = await insert_many(
        conn, "mkt_event_reg", ["camp_id", "reg_name", "company_name", "phone", "status", "remark"], rows
    )
    ctx.note("mkt_event_reg", n)

    rooms = []
    for i in range(1, 21):
        rooms.append((f"ROOM{i:02d}", f"会议室{i}", pick_opt(offices, rng, 0.9), rng.randint(4, 30), "active", None))
    room_ids = await insert_returning_ids(
        conn, "adm_meeting_room", ["room_code", "room_name", "office_id", "capacity", "status", "remark"], rooms
    )
    ctx.set_ids("adm_meeting_room", room_ids)

    rows = []
    for i in range(FACT_N):
        st = rand_ts(rng)
        rows.append((pick(room_ids, rng), pick(emps, rng), st, st + timedelta(hours=1), f"会议{i}", "active", None))
    n = await insert_many(
        conn,
        "adm_meeting_booking",
        ["room_id", "organizer_emp_id", "start_at", "end_at", "title", "status", "remark"],
        rows,
    )
    ctx.note("adm_meeting_booking", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (f"访客{i}", pick(emps, rng), rand_date(rng), f"事由{i}", pick_opt(offices, rng, 0.8), "active", None)
        )
    n = await insert_many(
        conn,
        "adm_visitor",
        ["visitor_name", "host_emp_id", "visit_date", "purpose", "office_id", "status", "remark"],
        rows,
    )
    ctx.note("adm_visitor", n)

    supplies = []
    for i in range(1, 51):
        supplies.append((f"SUP{i:03d}", f"办公用品{i}", "EA", d(rng.uniform(1, 200)), "active", None))
    supply_ids = await insert_returning_ids(
        conn, "adm_supply", ["supply_code", "supply_name", "uom", "unit_cost", "status", "remark"], supplies
    )
    ctx.set_ids("adm_supply", supply_ids)

    rows = []
    for i in range(FACT_N):
        rows.append((pick(supply_ids, rng), pick(emps, rng), d(rng.uniform(1, 20)), rand_date(rng), "active", None))
    n = await insert_many(
        conn,
        "adm_supply_request",
        ["supply_id", "emp_id", "qty", "request_date", "status", "remark"],
        rows,
    )
    ctx.note("adm_supply_request", n)

    vehicles = []
    for i in range(1, 16):
        vehicles.append((f"VH{i:02d}", f"公务车{i}", f"浙A{i:04d}学", rng.randint(4, 7), "active", None))
    vehicle_ids = await insert_returning_ids(
        conn, "adm_vehicle", ["vehicle_code", "vehicle_name", "plate_no", "seat_count", "status", "remark"], vehicles
    )
    ctx.set_ids("adm_vehicle", vehicle_ids)

    rows = []
    for i in range(5000):
        st = rand_ts(rng)
        rows.append(
            (pick(vehicle_ids, rng), pick(emps, rng), st, st + timedelta(hours=rng.randint(1, 6)), f"目的地{i % 50}", "active", None)
        )
    n = await insert_many(
        conn,
        "adm_vehicle_trip",
        ["vehicle_id", "driver_emp_id", "start_at", "end_at", "destination", "status", "remark"],
        rows,
    )
    ctx.note("adm_vehicle_trip", n)

    lcontracts = []
    for i in range(1, 2001):
        lcontracts.append(
            (
                f"LC{i:05d}",
                f"法务合同{i}",
                f"相对方{i % 200}",
                rand_date(rng),
                d(rng.uniform(10000, 1000000)),
                pick(emps, rng),
                pick_opt(custs, rng, 0.5),
                pick_opt(vendors, rng, 0.5),
                "active",
                None,
            )
        )
    lc_ids = await insert_returning_ids(
        conn,
        "legal_contract",
        [
            "lcontract_code",
            "lcontract_name",
            "counterparty",
            "sign_date",
            "amount",
            "owner_emp_id",
            "customer_id",
            "vendor_id",
            "status",
            "remark",
        ],
        lcontracts,
    )
    ctx.set_ids("legal_contract", lc_ids)

    rows = []
    for cid in lc_ids:
        for j in range(rng.randint(1, 4)):
            rows.append((cid, f"条款{j}", f"条款正文{j}", "active", None))
    n = await insert_many(
        conn, "legal_contract_clause", ["contract_id", "clause_title", "clause_text", "status", "remark"], rows
    )
    ctx.note("legal_contract_clause", n)

    rows = []
    for i in range(1, 501):
        rows.append(
            (
                f"CASE{i:04d}",
                f"案件{i}",
                pick_opt(lc_ids, rng, 0.8),
                f"对方{i}",
                rand_date(rng),
                f"律师{i % 20}",
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "legal_dispute",
        ["case_code", "case_name", "contract_id", "counterpart", "opened_at", "lawyer", "status", "remark"],
        rows,
    )
    ctx.note("legal_dispute", n)

    rows = []
    for i in range(1, 101):
        rows.append(
            (f"CHK{i:03d}", f"合规检查{i}", rand_date(rng), rng.choice(["pass", "fail", "na"]), pick(emps, rng), "active", None)
        )
    n = await insert_many(
        conn,
        "legal_compliance_check",
        ["chk_code", "chk_name", "check_date", "result", "owner_emp_id", "status", "remark"],
        rows,
    )
    ctx.note("legal_compliance_check", n)

    plans = []
    for i in range(1, 501):
        plans.append(
            (
                f"TP{i:04d}",
                f"测试计划{i}",
                pick_opt(projs, rng, 0.8),
                pick_opt(prods, rng, 0.8),
                pick(emps, rng),
                "active",
                None,
            )
        )
    plan_ids = await insert_returning_ids(
        conn,
        "qa_test_plan",
        ["plan_code", "plan_name", "project_id", "product_id", "owner_emp_id", "status", "remark"],
        plans,
    )
    ctx.set_ids("qa_test_plan", plan_ids)

    rows = []
    tc_i = 0
    for pid in plan_ids:
        for j in range(rng.randint(5, 20)):
            tc_i += 1
            rows.append((pid, f"TC{tc_i:06d}", f"用例{j}", rng.choice(["P0", "P1", "P2"]), "active", None))
            if len(rows) >= FACT_N:
                break
        if len(rows) >= FACT_N:
            break
    rows = rows[:FACT_N]
    n = await insert_many(
        conn, "qa_test_case", ["plan_id", "case_code", "case_name", "priority", "status", "remark"], rows
    )
    ctx.note("qa_test_case", n)

    rows = []
    for i in range(1, FACT_N + 1):
        rows.append(
            (
                f"BUG{i:06d}",
                f"缺陷{i}",
                pick_opt(projs, rng, 0.8),
                pick_opt(prods, rng, 0.8),
                rng.choice(["low", "mid", "high", "critical"]),
                pick(emps, rng),
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "qa_defect",
        [
            "bug_code",
            "bug_name",
            "project_id",
            "product_id",
            "severity",
            "reporter_emp_id",
            "assignee_emp_id",
            "status",
            "remark",
        ],
        rows,
    )
    ctx.note("qa_defect", n)

    rows = []
    for i in range(200):
        rows.append(
            (
                pick_opt(sys_ids, rng, 0.9),
                f"RG-{i:04d}",  # DDL 对 version_no 建了全局唯一
                f"门禁{i % 10}",
                rng.random() < 0.8,
                pick(emps, rng),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "qa_release_gate",
        ["system_id", "version_no", "gate_name", "passed", "checked_by", "status", "remark"],
        rows,
    )
    ctx.note("qa_release_gate", n)

    articles = []
    for i in range(1, 2001):
        articles.append(
            (
                f"ART{i:05d}",
                f"知识文章{i}",
                rng.choice(["研发", "运维", "销售", "行政"]),
                pick(emps, rng),
                f"正文内容{i}",
                "active",
                None,
            )
        )
    article_ids = await insert_returning_ids(
        conn,
        "kb_article",
        ["article_code", "article_name", "category", "author_emp_id", "body", "status", "remark"],
        articles,
    )
    ctx.set_ids("kb_article", article_ids)

    tags = []
    for i in range(1, 41):
        tags.append((f"TAG{i:02d}", f"标签{i}", f"#{rng.randint(0,0xFFFFFF):06x}", i, "active", None))
    # kb_article_tag 列：tag_code, tag_name, color, sort_no — 无 std 的 code_name 前缀 article
    # 看 schema: code_name 没用，是手写 tag_code
    tag_ids = await insert_returning_ids(
        conn, "kb_article_tag", ["tag_code", "tag_name", "color", "sort_no", "status", "remark"], tags
    )
    ctx.set_ids("kb_article_tag", tag_ids)

    rows = []
    for i in range(8000):
        rows.append((pick(article_ids, rng), pick(tag_ids, rng), pick(emps, rng), rand_ts(rng), "active", None))
    n = await insert_many(
        conn,
        "kb_article_tag_rel",
        ["article_id", "tag_id", "tagged_by", "tagged_at", "status", "remark"],
        rows,
    )
    ctx.note("kb_article_tag_rel", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (pick(emps, rng), rand_date(rng), rng.choice(["白班", "夜班"]), pick_opt(sys_ids, rng, 0.7), "active", None)
        )
    n = await insert_many(
        conn, "ops_duty_roster", ["emp_id", "duty_date", "shift_name", "system_id", "status", "remark"], rows
    )
    ctx.note("ops_duty_roster", n)

    rows = []
    for i in range(1, 41):
        rows.append(
            (f"RB{i:03d}", f"运维手册{i}", pick_opt(sys_ids, rng, 0.9), f"手册正文{i}", pick(emps, rng), "active", None)
        )
    n = await insert_many(
        conn,
        "ops_runbook",
        ["rb_code", "rb_name", "system_id", "content", "owner_emp_id", "status", "remark"],
        rows,
    )
    ctx.note("ops_runbook", n)

    rows = []
    for i in range(1, 31):
        rows.append(
            (
                f"BAK{i:03d}",
                f"备份任务{i}",
                pick_opt(sys_ids, rng, 0.9),
                "0 2 * * *",
                rand_ts(rng),
                rng.choice(["ok", "fail"]),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "ops_backup_job",
        ["bak_code", "bak_name", "system_id", "cron_expr", "last_run_at", "last_result", "status", "remark"],
        rows,
    )
    ctx.note("ops_backup_job", n)

    rows = []
    for i in range(FACT_N):
        rows.append(
            (
                pick_opt(sys_ids, rng, 0.9),
                f"告警{i % 100}",
                rng.choice(["info", "warn", "critical"]),
                rand_ts(rng),
                pick_opt(emps, rng, 0.6),
                "active",
                None,
            )
        )
    n = await insert_many(
        conn,
        "ops_monitor_alert",
        ["system_id", "alert_name", "severity", "fired_at", "acked_by", "status", "remark"],
        rows,
    )
    ctx.note("ops_monitor_alert", n)


async def seed_dim_lookups(conn: asyncpg.Connection, ctx: SeedCtx, tables: list[str]) -> None:
    rng = ctx.rng
    for name in tables:
        if not is_dim(name):
            continue
        rows = []
        for i in range(1, 41):
            rows.append(
                (
                    f"D{i:03d}",
                    f"字典项{i}",
                    f"group_{(i % 5) + 1}",
                    i,
                    "active",
                    None,
                )
            )
        n = await insert_many(
            conn, name, ["dict_code", "dict_name", "dict_group", "sort_no", "status", "remark"], rows
        )
        ctx.note(name, n)


async def verify_clean(conn: asyncpg.Connection) -> list[str]:
    problems: list[str] = []
    checks = [
        (
            "sal_quote",
            """
            SELECT count(*) FROM company.sal_quote q
            WHERE abs(q.total_amount - coalesce((
              SELECT sum(i.amount) FROM company.sal_quote_item i WHERE i.quote_id=q.id
            ),0)) > 0.01
            """,
        ),
        (
            "scm_purchase_order",
            """
            SELECT count(*) FROM company.scm_purchase_order p
            WHERE abs(p.total_amount - coalesce((
              SELECT sum(i.amount) FROM company.scm_purchase_order_item i WHERE i.po_id=p.id
            ),0)) > 0.01
            """,
        ),
        (
            "fin_journal_balance",
            """
            SELECT count(*) FROM (
              SELECT journal_id, sum(debit) d, sum(credit) c
              FROM company.fin_journal_line GROUP BY journal_id
              HAVING abs(sum(debit)-sum(credit)) > 0.01
            ) t
            """,
        ),
    ]
    for label, sql in checks:
        n = await conn.fetchval(sql)
        if n and int(n) > 0:
            problems.append(f"{label} dirty={n}")
    return problems


async def assert_core_untouched(conn: asyncpg.Connection, before: dict[str, int]) -> None:
    for t, n0 in before.items():
        n1 = await conn.fetchval(f"SELECT count(*) FROM company.{t}")
        if int(n1) != int(n0):
            raise RuntimeError(f"核心表被改动: {t} {n0} -> {n1}")


async def run_seed(dsn: str) -> None:
    catalog = await load_catalog()
    ext_tables = list(catalog["tables"].keys())
    rng = random.Random(SEED)

    conn = await asyncpg.connect(dsn)
    try:
        before = {
            t: int(await conn.fetchval(f"SELECT count(*) FROM company.{t}"))
            for t in sorted(CORE_TABLES)
        }
        core = await fetch_core_ids(conn)
        print(f"core loaded: emp={len(core['hr_employee'])} cust={len(core['crm_customer'])}")

        print("truncate extended tables...")
        await truncate_extended(conn, ext_tables)

        ctx = SeedCtx(rng, core)
        print("seed org...")
        await seed_org(conn, ctx)
        print("seed hr...")
        await seed_hr_people(conn, ctx)
        print("seed att...")
        await seed_att(conn, ctx)
        print("seed fin...")
        await seed_fin(conn, ctx)
        print("seed crm/sal...")
        await seed_crm_sal(conn, ctx)
        print("seed prd/prj...")
        await seed_prd_prj(conn, ctx)
        print("seed scm...")
        await seed_scm(conn, ctx)
        print("seed it/misc...")
        await seed_it_misc(conn, ctx)
        print("seed dim_lookup_*...")
        await seed_dim_lookups(conn, ctx, ext_tables)

        await assert_core_untouched(conn, before)
        problems = await verify_clean(conn)
        if problems:
            raise RuntimeError("干净校验失败: " + "; ".join(problems))

        factish = []
        smallish = []
        for t in sorted(ext_tables):
            n = int(await conn.fetchval(f"SELECT count(*) FROM company.{t}"))
            ctx.counts[t] = n
            if is_dim(t) or t in SMALL_TARGETS or t in PER_EMP_SMALL or t in PER_CUSTOMER_SMALL or t in PER_PROJECT_SMALL:
                smallish.append((t, n))
            else:
                factish.append((t, n))

        print("--- extended seed summary ---")
        print(f"tables={len(ext_tables)} factish={len(factish)} smallish={len(smallish)}")
        low = [(t, n) for t, n in factish if n == 0]
        empty_all = [(t, n) for t, n in ctx.counts.items() if n == 0]
        if empty_all:
            raise RuntimeError(f"仍有空表: {empty_all[:30]}")
        sample = sorted(factish, key=lambda x: -x[1])[:15]
        for t, n in sample:
            print(f"  {t}: {n}")
        print("clean checks: OK")
        print("core tables unchanged: OK")
    finally:
        await conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN_DEFAULT)
    args = ap.parse_args()
    asyncio.run(run_seed(args.dsn))


if __name__ == "__main__":
    main()
