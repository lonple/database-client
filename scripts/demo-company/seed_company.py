#!/usr/bin/env python3
"""向本地 PG schema company 灌入约 3 年仿生产 IT 公司数据。

连接默认：postgresql://postgres:root@127.0.0.1:5432/postgres
故意掺入空值、缺卡、金额不一致、状态异常等脏数据，供智能问数演练。
"""

from __future__ import annotations

import argparse
import asyncio
import random
import string
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import asyncpg

DSN_DEFAULT = "postgresql://postgres:root@127.0.0.1:5432/postgres"
SEED = 20260928
START = date(2023, 10, 1)
END = date(2026, 9, 28)

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻")
GIVEN = [
    "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋",
    "勇", "艳", "杰", "涛", "明", "超", "秀英", "霞", "平", "刚",
    "桂英", "建华", "文", "辉", "力", "倩", "鑫", "斌", "婷", "浩",
]
CITIES = ["杭州", "上海", "北京", "深圳", "成都", "南京", "武汉", "西安", None, ""]
INDUSTRIES = ["金融", "制造", "互联网", "能源", "政务", "零售", "物流", "医疗", None]
REGIONS = ["华东", "华北", "华南", "西南", "华中", "西北", None]
CUSTOMER_PREFIX = [
    "华信", "远航", "中科", "鼎盛", "云启", "博远", "正通", "安泰",
    "国联", "晨光", "星河", "智联", "瑞丰", "宏图", "天成", "金桥",
]


def d(v: float | int | None) -> Decimal | None:
    if v is None:
        return None
    return Decimal(str(round(float(v), 2)))


def month_start(d0: date) -> date:
    return date(d0.year, d0.month, 1)


def add_months(d0: date, n: int) -> date:
    y = d0.year + (d0.month - 1 + n) // 12
    m = (d0.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def iter_months(start: date, end: date):
    cur = month_start(start)
    last = month_start(end)
    while cur <= last:
        yield cur
        cur = add_months(cur, 1)


def is_workday(d0: date) -> bool:
    return d0.weekday() < 5


def rand_name(rng: random.Random) -> str:
    return rng.choice(SURNAMES) + rng.choice(GIVEN) + (rng.choice(GIVEN) if rng.random() < 0.35 else "")


@dataclass
class Emp:
    id: int = 0
    emp_no: str = ""
    name: str = ""
    gender: str | None = "M"
    dept_id: int | None = 1
    job_level_id: int | None = 1
    title: str | None = ""
    hire_date: date = START
    leave_date: date | None = None
    status: str = "active"
    email: str | None = ""
    phone: str | None = ""
    base_city: str | None = "杭州"
    base_salary: float = 12000.0


@dataclass
class State:
    rng: random.Random
    depts: list[dict[str, Any]] = field(default_factory=list)
    levels: list[dict[str, Any]] = field(default_factory=list)
    leave_types: list[dict[str, Any]] = field(default_factory=list)
    emps: list[Emp] = field(default_factory=list)
    customers: list[dict[str, Any]] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    periods: list[dict[str, Any]] = field(default_factory=list)


async def exec_many(conn: asyncpg.Connection, sql: str, rows: list[tuple], page: int = 2000) -> None:
    if not rows:
        return
    for i in range(0, len(rows), page):
        await conn.executemany(sql, rows[i : i + page])


async def seed(dsn: str, rebuild: bool) -> None:
    rng = random.Random(SEED)
    st = State(rng=rng)

    conn = await asyncpg.connect(dsn)
    try:
        if rebuild:
            print("==> applying schema (DROP + CREATE company)")
            # schema sql is applied separately via docker; here only truncate-like rebuild expect schema exists
            exists = await conn.fetchval(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name='company'"
            )
            if not exists:
                raise SystemExit("schema company 不存在，请先执行 01_schema.sql")
            # clear in FK-safe order via cascade drop recreate is done outside; here TRUNCATE
            await conn.execute(
                """
                TRUNCATE TABLE
                  company.prj_project_revenue,
                  company.prj_project_member,
                  company.att_timesheet,
                  company.att_overtime,
                  company.fin_reimburse_item,
                  company.fin_reimburse,
                  company.fin_activity_expense,
                  company.fin_activity_budget,
                  company.fin_salary_slip,
                  company.fin_salary_period,
                  company.att_daily_record,
                  company.att_leave,
                  company.sal_sales_order_item,
                  company.sal_sales_order,
                  company.prd_product_cost,
                  company.prj_project,
                  company.prd_product,
                  company.crm_customer,
                  company.hr_employee,
                  company.att_leave_type,
                  company.hr_job_level,
                  company.org_department
                RESTART IDENTITY CASCADE
                """
            )

        await seed_master(conn, st)
        await seed_employees(conn, st)
        await seed_customers_products(conn, st)
        await seed_projects(conn, st)
        await seed_attendance(conn, st)
        await seed_finance(conn, st)
        await seed_sales(conn, st)
        await seed_project_revenue_and_costs(conn, st)
        await backfill_dept_managers(conn, st)
        await print_stats(conn)
    finally:
        await conn.close()


async def seed_master(conn: asyncpg.Connection, st: State) -> None:
    depts = [
        ("HQ", "总部", None),
        ("MGMT", "管理层", "HQ"),
        ("RD", "研发中心", "HQ"),
        ("RD_PLAT", "平台研发部", "RD"),
        ("RD_APP", "应用研发部", "RD"),
        ("PROD", "产品部", "HQ"),
        ("SALES", "销售部", "HQ"),
        ("DELIVERY", "交付实施部", "HQ"),
        ("FIN", "财务部", "HQ"),
        ("HR", "人事行政部", "HQ"),
        ("CS", "客户成功部", "HQ"),
    ]
    code_to_id: dict[str, int] = {}
    for code, name, parent in depts:
        pid = code_to_id.get(parent) if parent else None
        rid = await conn.fetchval(
            """
            INSERT INTO company.org_department(dept_code, dept_name, parent_id, status)
            VALUES($1,$2,$3,1) RETURNING id
            """,
            code,
            name,
            pid,
        )
        code_to_id[code] = rid
        st.depts.append({"id": rid, "code": code, "name": name, "parent_id": pid})

    levels = [
        ("P1", "初级工程师", 1),
        ("P2", "工程师", 2),
        ("P3", "高级工程师", 3),
        ("P4", "资深工程师", 4),
        ("P5", "专家", 5),
        ("M1", "主管", 6),
        ("M2", "经理", 7),
        ("M3", "总监", 8),
    ]
    for code, name, rank in levels:
        rid = await conn.fetchval(
            "INSERT INTO company.hr_job_level(level_code, level_name, rank_no) VALUES($1,$2,$3) RETURNING id",
            code,
            name,
            rank,
        )
        st.levels.append({"id": rid, "code": code, "rank": rank})

    leave_types = [
        ("annual", "年假", True, True),
        ("sick", "病假", True, True),
        ("personal", "事假", False, True),
        ("marriage", "婚假", True, True),
        ("maternity", "产假", True, True),
        ("compensatory", "调休", True, True),
    ]
    for code, name, paid, deduct in leave_types:
        rid = await conn.fetchval(
            """
            INSERT INTO company.att_leave_type(type_code, type_name, is_paid, deduct_attendance)
            VALUES($1,$2,$3,$4) RETURNING id
            """,
            code,
            name,
            paid,
            deduct,
        )
        st.leave_types.append({"id": rid, "code": code})

    products = [
        ("DBC-SQL", "DBC SQL工作台", "数据平台", "subscription", 68000, "套/年"),
        ("DBC-ASK", "DBC 智能问数", "数据智能", "subscription", 98000, "套/年"),
        ("DBC-AUDIT", "DBC 审计中心", "合规审计", "subscription", 52000, "套/年"),
        ("DBC-MGMT", "DBC 资产管理", "数据平台", "license", 45000, "套"),
        ("DBC-IMPL", "实施服务包", "专业服务", "project", 120000, "人月"),
        ("DBC-OPS", "运维托管", "专业服务", "subscription", 36000, "年"),
        ("DBC-TRAIN", "培训认证", "专业服务", "project", 15000, "场"),
        ("DBC-OEM", "OEM 授权", "数据平台", "license", 200000, "套"),
    ]
    for code, name, line, model, price, unit in products:
        # 偶发空标价
        list_price = None if st.rng.random() < 0.08 else price
        rid = await conn.fetchval(
            """
            INSERT INTO company.prd_product(product_code, product_name, product_line, pricing_model, list_price, unit, status)
            VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING id
            """,
            code,
            name,
            line,
            model,
            d(list_price),
            unit,
            "on_sale" if st.rng.random() > 0.05 else "off",
        )
        st.products.append({"id": rid, "code": code, "list_price": price, "line": line})
    print(f"  master: depts={len(st.depts)} levels={len(st.levels)} products={len(st.products)}")


async def seed_employees(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    leaf_depts = [x for x in st.depts if x["code"] not in ("HQ", "RD")]
    titles = {
        "RD_PLAT": ["后端开发", "前端开发", "架构师", "DBA", "测试工程师"],
        "RD_APP": ["Java开发", "Python开发", "前端开发", "测试开发"],
        "PROD": ["产品经理", "产品运营", "需求分析"],
        "SALES": ["销售经理", "客户经理", "售前顾问"],
        "DELIVERY": ["实施顾问", "交付经理", "驻场工程师"],
        "FIN": ["会计", "出纳", "财务经理"],
        "HR": ["HRBP", "招聘专员", "行政专员"],
        "CS": ["客户成功经理", "支持工程师"],
        "MGMT": ["总经理", "副总经理", "COO"],
    }
    salary_by_rank = {1: 9000, 2: 14000, 3: 20000, 4: 28000, 5: 38000, 6: 32000, 7: 45000, 8: 65000}

    # 期初约 95 人，后续入职约 70，离职约 25 → 累计约 165，期末在职约 140
    initial_n = 95
    later_n = 70
    rows: list[tuple] = []
    seq = 1

    def make_emp(hire: date) -> Emp:
        nonlocal seq
        dept = rng.choice(leaf_depts)
        level = rng.choices(st.levels, weights=[18, 22, 20, 14, 8, 8, 6, 4])[0]
        title_pool = titles.get(dept["code"], ["专员"])
        title = rng.choice(title_pool)
        name = rand_name(rng)
        emp_no = f"E{hire.year % 100:02d}{seq:04d}"
        seq += 1
        gender = rng.choice(["M", "F", "M", "F", None])  # 偶发空
        email = None if rng.random() < 0.07 else f"{emp_no.lower()}@starlink-it.example"
        phone = None if rng.random() < 0.12 else f"1{rng.choice('345789')}{rng.randint(100000000, 999999999)}"
        city = rng.choice(CITIES)
        base = salary_by_rank[level["rank"]] * rng.uniform(0.9, 1.15)
        return Emp(
            emp_no=emp_no,
            name=name,
            gender=gender,
            dept_id=dept["id"],
            job_level_id=level["id"],
            title=title if rng.random() > 0.03 else None,
            hire_date=hire,
            email=email,
            phone=phone,
            base_city=city if city != "" else None,
            base_salary=base,
        )

    for _ in range(initial_n):
        # 入职日散落在 START 之前 0~900 天
        hire = START - timedelta(days=rng.randint(0, 900))
        st.emps.append(make_emp(hire))

    for _ in range(later_n):
        hire = START + timedelta(days=rng.randint(0, (END - START).days - 30))
        st.emps.append(make_emp(hire))

    # 离职：约 28 人，且须在 hire 之后
    resign_candidates = [e for e in st.emps if (END - e.hire_date).days > 120]
    for e in rng.sample(resign_candidates, k=min(28, len(resign_candidates))):
        span = (END - max(e.hire_date, START)).days
        if span < 30:
            continue
        leave = max(e.hire_date, START) + timedelta(days=rng.randint(30, span))
        e.leave_date = leave
        e.status = "resigned"
        # 少量脏数据：离职但 status 仍 active
        if rng.random() < 0.08:
            e.status = "active"

    for e in st.emps:
        rows.append(
            (
                e.emp_no,
                e.name,
                e.gender,
                e.dept_id,
                e.job_level_id,
                e.title,
                e.hire_date,
                e.leave_date,
                e.status,
                e.email,
                e.phone,
                e.base_city,
            )
        )

    await exec_many(
        conn,
        """
        INSERT INTO company.hr_employee(
          emp_no, name, gender, dept_id, job_level_id, title, hire_date, leave_date,
          employment_status, email, phone, base_city
        ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        """,
        rows,
    )
    id_map = {r["emp_no"]: r["id"] for r in await conn.fetch("SELECT id, emp_no FROM company.hr_employee")}
    for e in st.emps:
        e.id = id_map[e.emp_no]
    active = sum(1 for e in st.emps if e.leave_date is None or e.leave_date > END)
    print(f"  employees: total={len(st.emps)} approx_active_end={active} resigned_flagged={sum(1 for e in st.emps if e.leave_date)}")


def active_on(emps: list[Emp], d0: date) -> list[Emp]:
    out = []
    for e in emps:
        if e.hire_date > d0:
            continue
        if e.leave_date and e.leave_date <= d0:
            continue
        out.append(e)
    return out


async def seed_customers_products(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    sales = [e for e in st.emps if e.dept_id in {d["id"] for d in st.depts if d["code"] == "SALES"}]
    if not sales:
        sales = st.emps[:10]
    rows = []
    for i in range(28):
        code = f"C{i+1:04d}"
        name = f"{rng.choice(CUSTOMER_PREFIX)}{rng.choice(['科技','信息','股份','集团','有限'])}有限公司"
        owner = rng.choice(sales)
        rows.append(
            (
                code,
                name,
                rng.choice(INDUSTRIES),
                rng.choice(REGIONS),
                rng.choice(["A", "A", "B", "B", "C", None]),
                owner.id if rng.random() > 0.1 else None,
                "active" if rng.random() > 0.1 else "churned",
            )
        )
    await exec_many(
        conn,
        """
        INSERT INTO company.crm_customer(customer_code, customer_name, industry, region, customer_level, owner_emp_id, status)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        """,
        rows,
    )
    for r in await conn.fetch("SELECT id, customer_code FROM company.crm_customer"):
        st.customers.append({"id": r["id"], "code": r["customer_code"]})
    print(f"  customers={len(st.customers)}")


async def seed_projects(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    delivery_dept = next(d for d in st.depts if d["code"] == "DELIVERY")
    rd_depts = [d for d in st.depts if d["code"] in ("RD_PLAT", "RD_APP", "DELIVERY")]
    pms = [e for e in st.emps if e.title and ("经理" in e.title or "顾问" in e.title or "架构" in (e.title or ""))]
    if len(pms) < 8:
        pms = st.emps
    types = ["implementation", "custom_dev", "ops", "poc"]
    rows = []
    for i in range(24):
        cust = rng.choice(st.customers)
        start = START + timedelta(days=rng.randint(0, 700))
        duration = rng.randint(90, 480)
        plan_end = start + timedelta(days=duration)
        end = None
        status = "active"
        if plan_end < END - timedelta(days=30):
            if rng.random() < 0.7:
                status = "closed"
                end = plan_end + timedelta(days=rng.randint(-20, 40))
            elif rng.random() < 0.5:
                status = "warranty"
                end = plan_end
        elif start > END - timedelta(days=60):
            status = "planning"
        code = f"PRJ{start.year}{i+1:03d}"
        name = f"{cust['code']}-{rng.choice(['上线实施','定制开发','运维托管','POC验证','迁移升级'])}"
        pm = rng.choice(pms)
        dept = rng.choice(rd_depts)
        amount = rng.choice([180000, 350000, 520000, 780000, 1200000, 2000000, None])
        rows.append(
            (
                code,
                name,
                cust["id"],
                rng.choice(types),
                dept["id"] if rng.random() > 0.05 else None,
                pm.id if rng.random() > 0.08 else None,
                start,
                end,
                plan_end,
                d(amount),
                status,
            )
        )
    await exec_many(
        conn,
        """
        INSERT INTO company.prj_project(
          project_code, project_name, customer_id, project_type, dept_id, pm_emp_id,
          start_date, end_date, plan_end_date, contract_amount, status
        ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """,
        rows,
    )
    for r in await conn.fetch(
        "SELECT id, project_code, start_date, end_date, status, customer_id, contract_amount FROM company.prj_project"
    ):
        st.projects.append(dict(r))

    # 项目成员
    member_rows = []
    tech = [e for e in st.emps if e.dept_id in {d["id"] for d in st.depts if d["code"] in ("RD_PLAT", "RD_APP", "DELIVERY", "CS")}]
    for p in st.projects:
        n = rng.randint(3, 10)
        chosen = rng.sample(tech, k=min(n, len(tech)))
        for e in chosen:
            role = rng.choice(["pm", "dev", "qa", "implement", "support", None])
            join = p["start_date"] or START
            leave = None
            if e.leave_date and (p["end_date"] is None or e.leave_date < p["end_date"]):
                leave = e.leave_date
            member_rows.append(
                (
                    p["id"],
                    e.id,
                    role,
                    join,
                    leave,
                    d(rng.choice([30, 50, 80, 100, None])),
                )
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.prj_project_member(project_id, emp_id, role, join_date, leave_date, allocation_pct)
        VALUES($1,$2,$3,$4,$5,$6)
        ON CONFLICT DO NOTHING
        """,
        member_rows,
    )
    print(f"  projects={len(st.projects)} members~={len(member_rows)}")


async def seed_attendance(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    daily_rows: list[tuple] = []
    leave_rows: list[tuple] = []
    ot_rows: list[tuple] = []
    ts_rows: list[tuple] = []

    members = await conn.fetch("SELECT project_id, emp_id, join_date, leave_date FROM company.prj_project_member")
    emp_projects: dict[int, list[dict]] = {}
    for m in members:
        emp_projects.setdefault(m["emp_id"], []).append(dict(m))

    # 请假：每人每年 0~6 次
    for e in st.emps:
        years = max(1, (min(e.leave_date or END, END) - e.hire_date).days // 365)
        for _ in range(rng.randint(0, 2 + years * 2)):
            base = e.hire_date + timedelta(days=rng.randint(30, max(31, (min(e.leave_date or END, END) - e.hire_date).days)))
            if base > END:
                continue
            days = rng.choice([0.5, 1, 1, 2, 3, 5])
            start = datetime.combine(base, datetime.min.time()) + timedelta(hours=9)
            end = start + timedelta(days=float(days))
            lt = rng.choice(st.leave_types)["id"]
            if rng.random() < 0.04:
                lt = None  # 脏：缺类型
            status = rng.choices(["approved", "approved", "rejected", "cancelled", "draft"], weights=[70, 15, 5, 5, 5])[0]
            approver = rng.choice(st.emps).id if status == "approved" and rng.random() > 0.1 else None
            leave_rows.append(
                (
                    e.id,
                    lt,
                    start,
                    end,
                    d(days if rng.random() > 0.05 else None),
                    rng.choice(["家里有事", "身体不适", "年假出行", "婚假", None, ""]),
                    status,
                    approver,
                    start + timedelta(days=rng.randint(0, 3)) if approver else None,
                )
            )

    await exec_many(
        conn,
        """
        INSERT INTO company.att_leave(emp_id, leave_type_id, start_at, end_at, leave_days, reason, status, approved_by, approved_at)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        leave_rows,
    )

    # 日考勤：抽样生成（不全量 150*工作日*3，控制在可管理规模，但仍够问数）
    # 策略：每月对在职员工生成 70%~95% 工作日记录，故意漏记
    cur = START
    while cur <= END:
        if is_workday(cur):
            actives = active_on(st.emps, cur)
            sample_n = int(len(actives) * rng.uniform(0.72, 0.95))
            for e in rng.sample(actives, k=max(1, sample_n)):
                # 缺勤/请假/异常
                roll = rng.random()
                if roll < 0.03:
                    status = "absent"
                    cin = cout = wh = late = early = None
                    src = "device"
                elif roll < 0.08:
                    status = "leave"
                    cin = cout = wh = late = early = None
                    src = "manual"
                else:
                    late = 0
                    early = 0
                    cin_h = 8 + rng.choice([0, 0, 0, 0, 1])
                    cin_m = rng.choice([45, 50, 55, 0, 5, 10, 20, 35])
                    if cin_m >= 60:
                        cin_h += 1
                        cin_m -= 60
                    cin = datetime(cur.year, cur.month, cur.day, cin_h, cin_m % 60, rng.randint(0, 59))
                    if cin.hour > 9 or (cin.hour == 9 and cin.minute > 5):
                        late = (cin.hour - 9) * 60 + cin.minute
                        status = "late"
                    else:
                        status = "normal"
                    cout_h = rng.choice([17, 18, 18, 19, 20, 21])
                    cout_m = rng.randint(0, 59)
                    cout = datetime(cur.year, cur.month, cur.day, cout_h, cout_m, rng.randint(0, 59))
                    if rng.random() < 0.06:
                        cout = None  # 缺卡
                        status = "early" if status == "normal" else status
                        early = rng.randint(10, 90)
                        wh = None
                    else:
                        wh = round((cout - cin).total_seconds() / 3600, 2)
                        if wh > 14 and rng.random() < 0.5:
                            wh = 12.0  # 偶发超长工时脏值保留一部分
                    src = rng.choice(["device", "device", "device", "manual", None])
                daily_rows.append((e.id, cur, cin if roll >= 0.03 else None, cout if roll >= 0.08 else None, d(wh) if roll >= 0.08 else None, late if roll >= 0.08 else None, early if roll >= 0.08 else None, status, src))

                # 加班：约 8% 工作日
                if roll >= 0.08 and rng.random() < 0.08:
                    pj = None
                    eps = emp_projects.get(e.id) or []
                    if eps and rng.random() > 0.25:
                        pj = rng.choice(eps)["project_id"]
                    hours = rng.choice([1, 1.5, 2, 2, 3, 4, 8, None])
                    ot_rows.append(
                        (
                            e.id,
                            pj,
                            cur,
                            datetime(cur.year, cur.month, cur.day, 18, 30),
                            datetime(cur.year, cur.month, cur.day, 18, 30) + timedelta(hours=float(hours or 2)),
                            d(hours),
                            rng.choice(["workday", "workday", "weekend", "holiday", None]),
                            rng.choice(["pay", "leave", None]),
                            rng.choice(["approved", "approved", "draft", "rejected"]),
                        )
                    )

                # 工时：约 35% 有项目的人写 timesheet
                eps = emp_projects.get(e.id) or []
                if eps and rng.random() < 0.35 and roll >= 0.08:
                    m = rng.choice(eps)
                    hours = rng.choice([2, 4, 6, 8, 8, 8, 10, 12, 0.5])
                    if rng.random() < 0.03:
                        hours = 16  # 异常超长
                    ts_rows.append(
                        (
                            e.id,
                            m["project_id"] if rng.random() > 0.04 else None,
                            cur,
                            d(hours),
                            rng.choice(["develop", "test", "implement", "support", "manage", None]),
                            rng.choice([None, "", "联调", "发版", "驻场"]),
                            rng.choice(["approved", "approved", "submitted", "draft"]),
                        )
                    )
        cur += timedelta(days=1)
        if len(daily_rows) >= 5000:
            await exec_many(
                conn,
                """
                INSERT INTO company.att_daily_record(
                  emp_id, work_date, check_in_at, check_out_at, work_hours, late_minutes, early_leave_minutes, attendance_status, source
                ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT DO NOTHING
                """,
                daily_rows,
            )
            daily_rows.clear()
            print(f"  ... attendance flushed at {cur}")

    await exec_many(
        conn,
        """
        INSERT INTO company.att_daily_record(
          emp_id, work_date, check_in_at, check_out_at, work_hours, late_minutes, early_leave_minutes, attendance_status, source
        ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
        ON CONFLICT DO NOTHING
        """,
        daily_rows,
    )
    await exec_many(
        conn,
        """
        INSERT INTO company.att_overtime(emp_id, project_id, overtime_date, start_at, end_at, hours, ot_type, compensate_type, status)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        ot_rows,
    )
    await exec_many(
        conn,
        """
        INSERT INTO company.att_timesheet(emp_id, project_id, work_date, hours, work_type, remark, status)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        """,
        ts_rows,
    )
    print(f"  leaves={len(leave_rows)} overtime={len(ot_rows)} timesheet={len(ts_rows)}")


async def seed_finance(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    period_rows = []
    for ym in iter_months(START, END):
        code = ym.strftime("%Y-%m")
        pay = date(ym.year, ym.month, min(15, 28))
        if ym.month == 12:
            pay = date(ym.year, 12, 20)
        status = "closed" if ym < month_start(END) else "open"
        period_rows.append((code, ym, pay if rng.random() > 0.05 else None, status))
    await exec_many(
        conn,
        "INSERT INTO company.fin_salary_period(period_code, year_month, pay_date, status) VALUES($1,$2,$3,$4)",
        period_rows,
    )
    periods = await conn.fetch("SELECT id, year_month, period_code FROM company.fin_salary_period ORDER BY year_month")
    st.periods = [dict(p) for p in periods]

    slip_rows = []
    for p in st.periods:
        ym: date = p["year_month"]
        month_end = add_months(ym, 1) - timedelta(days=1)
        for e in active_on(st.emps, month_end):
            if e.hire_date > month_end:
                continue
            base = e.base_salary * (1 + (ym.year - 2023) * 0.03)
            allowance = rng.choice([0, 500, 800, 1000, 1500, None])
            ot_pay = rng.choice([0, 0, 200, 500, 1200, None])
            bonus = 0.0
            if ym.month in (6, 12) and rng.random() < 0.7:
                bonus = base * rng.uniform(0.3, 1.2)
            if rng.random() < 0.06:
                bonus = None
            ss = round(base * 0.105, 2)
            hf = round(base * 0.12, 2)
            tax = max(0, round((base + (allowance or 0) + (ot_pay or 0) + (bonus or 0) - ss - hf - 5000) * 0.1, 2))
            other = rng.choice([0, 0, 0, 100, 200, None])
            gross = base + (allowance or 0) + (ot_pay or 0) + (bonus or 0)
            net = gross - ss - hf - tax - (other or 0)
            # 3% 脏：net 对不上或为空
            if rng.random() < 0.03:
                net = None
            elif rng.random() < 0.03:
                net = net + rng.choice([-500, 300, 0.01])
            slip_rows.append(
                (
                    p["id"],
                    e.id,
                    e.dept_id if rng.random() > 0.04 else None,
                    d(base),
                    d(allowance),
                    d(ot_pay),
                    d(bonus),
                    d(ss),
                    d(hf),
                    d(tax if rng.random() > 0.02 else None),
                    d(other),
                    d(net),
                    "CNY",
                )
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.fin_salary_slip(
          period_id, emp_id, dept_id, base_salary, allowance, overtime_pay, bonus,
          social_security_personal, housing_fund_personal, tax, other_deduction, net_pay, currency
        ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        ON CONFLICT DO NOTHING
        """,
        slip_rows,
    )

    # 报销
    cats = ["travel", "meal", "traffic", "office", "entertainment", "training", None]
    claim_rows = []
    item_rows = []
    claim_id_seq = 0
    tmp_claims: list[dict] = []
    for e in st.emps:
        n = rng.randint(2, 18)
        for _ in range(n):
            if e.hire_date >= END:
                continue
            span = (min(e.leave_date or END, END) - e.hire_date).days
            if span < 5:
                continue
            cd = e.hire_date + timedelta(days=rng.randint(1, span))
            claim_id_seq += 1
            claim_no = f"RB{cd.strftime('%Y%m')}{claim_id_seq:05d}"
            status = rng.choices(["approved", "paid", "submitted", "rejected", "draft"], weights=[40, 35, 10, 8, 7])[0]
            paid_at = datetime.combine(cd + timedelta(days=rng.randint(3, 25)), datetime.min.time()) if status == "paid" else None
            pj = rng.choice(st.projects)["id"] if st.projects and rng.random() < 0.35 else None
            items_n = rng.randint(1, 4)
            amounts = [round(rng.uniform(35, 2800), 2) for _ in range(items_n)]
            total = sum(amounts)
            if rng.random() < 0.05:
                total = None  # 头表金额空
            elif rng.random() < 0.06:
                total = round(total * rng.uniform(0.8, 1.2), 2)  # 与明细不一致
            tmp_claims.append(
                {
                    "row": (
                        claim_no,
                        e.id,
                        e.dept_id,
                        pj,
                        cd,
                        rng.choice(["差旅报销", "招待费", "办公采购", "培训费", "交通费", None]),
                        d(total),
                        status,
                        paid_at,
                    ),
                    "amounts": amounts,
                    "cd": cd,
                }
            )

    await exec_many(
        conn,
        """
        INSERT INTO company.fin_reimburse(claim_no, emp_id, dept_id, project_id, claim_date, title, total_amount, status, paid_at)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        [c["row"] for c in tmp_claims],
    )
    claim_map = {r["claim_no"]: r["id"] for r in await conn.fetch("SELECT id, claim_no FROM company.fin_reimburse")}
    for c in tmp_claims:
        cid = claim_map[c["row"][0]]
        # 2% 无明细
        if rng.random() < 0.02:
            continue
        for amt in c["amounts"]:
            item_rows.append(
                (
                    cid,
                    rng.choice(cats),
                    d(amt if rng.random() > 0.03 else None),
                    c["cd"] - timedelta(days=rng.randint(0, 10)),
                    None if rng.random() < 0.2 else f"INV{rng.randint(100000, 999999)}",
                    rng.choice([None, "", "含税", "客户现场"]),
                )
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.fin_reimburse_item(claim_id, category, amount, occur_date, invoice_no, remark)
        VALUES($1,$2,$3,$4,$5,$6)
        """,
        item_rows,
    )

    # 活动经费：每年每部门若干
    budget_rows = []
    expense_rows = []
    years = sorted({ym.year for ym in iter_months(START, END)})
    act_names = ["团建", "年会分摊", "技术分享会", "招聘开放日", "客户答谢", "部门聚餐"]
    bid = 0
    tmp_budgets = []
    for y in years:
        for dept in st.depts:
            if dept["code"] in ("HQ", "RD"):
                continue
            if rng.random() < 0.25:
                continue
            bid += 1
            code = f"ACT{y}{dept['code']}{bid%100:02d}"
            budget = rng.choice([8000, 15000, 30000, 50000, 80000, None])
            owner = rng.choice(active_on(st.emps, date(y, 6, 1)) or st.emps)
            tmp_budgets.append(
                {
                    "row": (
                        code,
                        f"{y}年{dept['name']}{rng.choice(act_names)}",
                        dept["id"],
                        owner.id if rng.random() > 0.1 else None,
                        y,
                        d(budget),
                        rng.choice(["ongoing", "closed", "planned"]),
                    ),
                    "budget": budget,
                    "year": y,
                }
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.fin_activity_budget(activity_code, activity_name, dept_id, owner_emp_id, year, budget_amount, status)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        """,
        [b["row"] for b in tmp_budgets],
    )
    bmap = {r["activity_code"]: r["id"] for r in await conn.fetch("SELECT id, activity_code FROM company.fin_activity_budget")}
    for b in tmp_budgets:
        bid = bmap[b["row"][0]]
        for _ in range(rng.randint(1, 6)):
            ed = date(b["year"], rng.randint(1, 12), rng.randint(1, 28))
            if ed < START or ed > END:
                continue
            amt = round(rng.uniform(200, 12000), 2)
            expense_rows.append(
                (
                    bid,
                    ed,
                    rng.choice(["catering", "venue", "gift", "transport", "other", None]),
                    d(amt if rng.random() > 0.04 else None),
                    rng.choice(["商家A", "酒店B", "盒马", None, "个人垫付"]),
                    rng.choice([None, "发票后补", "超预算特批"]),
                    rng.choice(["paid", "approved", "draft"]),
                )
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.fin_activity_expense(budget_id, expense_date, category, amount, payee, remark, status)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        """,
        expense_rows,
    )
    print(f"  salary_slips~={len(slip_rows)} reimburses={len(tmp_claims)} activity_budgets={len(tmp_budgets)}")


async def seed_sales(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    sales_emps = [e for e in st.emps if e.dept_id in {d["id"] for d in st.depts if d["code"] == "SALES"}]
    if not sales_emps:
        sales_emps = st.emps
    sales_dept = next(d for d in st.depts if d["code"] == "SALES")
    order_tmp = []
    for i in range(95):
        od = START + timedelta(days=rng.randint(0, (END - START).days))
        cust = rng.choice(st.customers)
        owner = rng.choice(sales_emps)
        status = rng.choices(
            ["signed", "delivering", "closed", "cancelled", "draft"],
            weights=[35, 25, 25, 8, 7],
        )[0]
        sign = od + timedelta(days=rng.randint(0, 20)) if status != "draft" else None
        if rng.random() < 0.05:
            od = None  # 脏：无下单日
        order_no = f"SO{od.strftime('%Y%m') if od else 'XXXXXX'}{i+1:04d}"
        n_items = rng.randint(1, 3)
        items = []
        total = 0.0
        for _ in range(n_items):
            prod = rng.choice(st.products)
            qty = rng.choice([1, 1, 1, 2, 5, 10])
            price = prod["list_price"] * rng.uniform(0.75, 1.05)
            disc = rng.choice([0, 0, 0.05, 0.1, 0.15, None])
            amt = qty * price * (1 - (disc or 0))
            cost = amt * rng.uniform(0.25, 0.55)
            if rng.random() < 0.05:
                cost = None
            items.append((prod["id"] if rng.random() > 0.03 else None, d(qty), d(price), d(disc), d(amt), d(cost)))
            total += amt
        if rng.random() < 0.06:
            total_v = None
        elif rng.random() < 0.05:
            total_v = total * rng.uniform(0.9, 1.1)
        else:
            total_v = total
        order_tmp.append(
            {
                "row": (
                    order_no,
                    cust["id"] if rng.random() > 0.04 else None,
                    owner.id,
                    sales_dept["id"],
                    od,
                    sign,
                    "CNY",
                    d(total_v),
                    status,
                ),
                "items": items,
            }
        )
    await exec_many(
        conn,
        """
        INSERT INTO company.sal_sales_order(order_no, customer_id, owner_emp_id, dept_id, order_date, sign_date, currency, total_amount, status)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        [o["row"] for o in order_tmp],
    )
    omap = {r["order_no"]: r["id"] for r in await conn.fetch("SELECT id, order_no FROM company.sal_sales_order")}
    item_rows = []
    for o in order_tmp:
        oid = omap[o["row"][0]]
        if rng.random() < 0.03:
            continue  # 无明细订单
        for it in o["items"]:
            item_rows.append((oid, *it))
    await exec_many(
        conn,
        """
        INSERT INTO company.sal_sales_order_item(order_id, product_id, qty, unit_price, discount_rate, amount, cost_amount)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        """,
        item_rows,
    )
    print(f"  sales_orders={len(order_tmp)} items={len(item_rows)}")


async def seed_project_revenue_and_costs(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    rev_rows = []
    for p in st.projects:
        contract = float(p["contract_amount"] or rng.choice([200000, 500000, 800000]))
        milestones = rng.randint(2, 5)
        start = p["start_date"] or START
        for i in range(milestones):
            rd = start + timedelta(days=30 * (i + 1) + rng.randint(0, 20))
            if rd > END:
                continue
            amt = contract / milestones * rng.uniform(0.7, 1.2)
            received = amt if rng.random() < 0.7 else amt * rng.uniform(0, 0.9)
            if rng.random() < 0.08:
                received = None
            if rng.random() < 0.04:
                amt = None
            rev_rows.append(
                (
                    p["id"],
                    rd,
                    rng.choice(["milestone", "acceptance", "monthly", "final", None]),
                    d(amt),
                    d(received),
                    None if rng.random() < 0.25 else f"FP{rd.strftime('%Y%m')}{rng.randint(1000,9999)}",
                    rng.choice([None, "验收后开票", "分批回款"]),
                )
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.prj_project_revenue(project_id, revenue_date, revenue_type, amount, received_amount, invoice_no, remark)
        VALUES($1,$2,$3,$4,$5,$6,$7)
        """,
        rev_rows,
    )

    cost_rows = []
    for prod in st.products:
        for ym in iter_months(START, END):
            if rng.random() < 0.12:
                continue  # 缺月成本
            unit = prod["list_price"] * rng.uniform(0.28, 0.48)
            cost_rows.append(
                (
                    prod["id"],
                    ym,
                    d(unit if rng.random() > 0.04 else None),
                    rng.choice(["license_cost", "cloud", "support", "other"]),
                    rng.choice([None, "含云资源", "渠道成本调整"]),
                )
            )
    await exec_many(
        conn,
        """
        INSERT INTO company.prd_product_cost(product_id, year_month, unit_cost, cost_type, remark)
        VALUES($1,$2,$3,$4,$5)
        ON CONFLICT DO NOTHING
        """,
        cost_rows,
    )
    print(f"  project_revenues={len(rev_rows)} product_costs={len(cost_rows)}")


async def backfill_dept_managers(conn: asyncpg.Connection, st: State) -> None:
    rng = st.rng
    for dept in st.depts:
        cands = [e for e in st.emps if e.dept_id == dept["id"] and e.leave_date is None]
        if not cands:
            cands = [e for e in st.emps if e.dept_id == dept["id"]]
        if not cands:
            continue
        mgr = rng.choice(cands)
        if rng.random() < 0.1:
            continue  # 故意不设负责人
        await conn.execute(
            "UPDATE company.org_department SET manager_emp_id=$1, updated_at=CURRENT_TIMESTAMP WHERE id=$2",
            mgr.id,
            dept["id"],
        )


async def print_stats(conn: asyncpg.Connection) -> None:
    tables = [
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
    ]
    print("==> row counts")
    for t in tables:
        n = await conn.fetchval(f"SELECT count(*) FROM company.{t}")
        print(f"  company.{t}: {n}")
    emp = await conn.fetchrow(
        """
        SELECT count(*) AS total,
               count(*) FILTER (WHERE leave_date IS NULL) AS no_leave_date,
               count(*) FILTER (WHERE employment_status='active') AS status_active,
               count(*) FILTER (WHERE employment_status='resigned') AS status_resigned
        FROM company.hr_employee
        """
    )
    print(
        f"==> employees total={emp['total']} no_leave_date={emp['no_leave_date']} "
        f"status_active={emp['status_active']} status_resigned={emp['status_resigned']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=DSN_DEFAULT)
    parser.add_argument("--no-truncate", action="store_true", help="不先 TRUNCATE（默认会清空 company 业务表）")
    args = parser.parse_args()
    asyncio.run(seed(args.dsn, rebuild=not args.no_truncate))


if __name__ == "__main__":
    main()
