#!/usr/bin/env python3
"""按 WORKLIST.md 做扩展造数 + 用例配额验收抽检。"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"
HERE = Path(__file__).resolve().parent
CATALOG = HERE / "metadata" / "extended_catalog.json"
CASES = HERE / "eval" / "cases"

SMALL_HINT = (
    "dim_lookup_",
    "org_company",
    "org_office",
    "org_cost_center",
    "org_position",
    "org_biz_unit",
    "org_location",
    "org_dept_closure",
    "org_seal",
    "att_shift",
    "att_ot_rule",
    "att_device",
    "fin_gl_account",
    "fin_bank_account",
    "fin_vendor",
    "fin_petty_cash",
    "fin_exchange_rate",
    "fin_tax_period",
    "hr_performance_cycle",
    "hr_training_course",
    "hr_work_calendar",
    "prd_product_line",
    "sal_channel",
    "sal_price_list",
    "sal_commission_rule",
    "scm_warehouse",
    "scm_material",
    "itm_system",
    "sec_policy",
    "sec_data_class",
    "adm_meeting_room",
    "adm_supply",
    "adm_vehicle",
    "kb_article_tag",
    "ops_runbook",
    "ops_backup_job",
)


def is_small(name: str) -> bool:
    if name.startswith("dim_lookup_"):
        return True
    return name in SMALL_HINT or any(name == s for s in SMALL_HINT)


async def main() -> None:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    ext = list(cat["tables"].keys())
    conn = await asyncpg.connect(DSN)
    empty, dim, fact_band, other = [], [], [], []
    try:
        for t in ext:
            n = int(await conn.fetchval(f"SELECT count(*) FROM company.{t}"))
            if n == 0:
                empty.append(t)
            elif t.startswith("dim_lookup_"):
                dim.append((t, n))
            elif is_small(t) or n < 8000:
                # 维表/主数据/按人按客户派生：允许 <8k；WORKLIST 要求抽样≥10 张事实表落在约 1 万
                other.append((t, n, "small_or_derived"))
            elif 8000 <= n <= 12000:
                fact_band.append((t, n))
            else:
                other.append((t, n, "fact_out_of_band"))

        cleans = {
            "sal_quote": await conn.fetchval(
                """SELECT count(*) FROM company.sal_quote q
                   WHERE abs(q.total_amount - coalesce((
                     SELECT sum(i.amount) FROM company.sal_quote_item i WHERE i.quote_id=q.id),0)) > 0.01"""
            ),
            "scm_po": await conn.fetchval(
                """SELECT count(*) FROM company.scm_purchase_order p
                   WHERE abs(p.total_amount - coalesce((
                     SELECT sum(i.amount) FROM company.scm_purchase_order_item i WHERE i.po_id=p.id),0)) > 0.01"""
            ),
            "journal": await conn.fetchval(
                """SELECT count(*) FROM (
                     SELECT journal_id FROM company.fin_journal_line
                     GROUP BY journal_id HAVING abs(sum(debit)-sum(credit)) > 0.01
                   ) t"""
            ),
            "scm_req": await conn.fetchval(
                """SELECT count(*) FROM company.scm_purchase_req r
                   WHERE abs(r.total_amount - coalesce((
                     SELECT sum(i.qty * i.unit_price) FROM company.scm_purchase_req_item i
                     WHERE i.req_id=r.id),0)) > 0.01"""
            ),
        }
        core_emp = await conn.fetchval("SELECT count(*) FROM company.hr_employee")
        core_att = await conn.fetchval("SELECT count(*) FROM company.att_daily_record")
    finally:
        await conn.close()

    print("=== W1 extended seed ===")
    print(f"extended_tables={len(ext)} empty={len(empty)}")
    if empty:
        print("EMPTY:", empty)
    print(f"dim_lookup tables={len(dim)} max_rows={max((n for _, n in dim), default=0)}")
    print(f"fact_in_[8000,12000]={len(fact_band)} (need >=10)")
    out = [(t, n, k) for t, n, k in other if k == "fact_out_of_band"]
    print(f"fact_out_of_band(>12k)={len(out)}")
    for t, n, _ in sorted(out, key=lambda x: -x[1])[:12]:
        print(f"  {t}: {n}")
    print("clean_dirty_counts:", {k: int(v) for k, v in cleans.items()})
    print(f"core hr_employee={core_emp} att_daily_record={core_att}")

    print("=== W2 cases ===")
    sk_max_all = 0
    for f in sorted(CASES.glob("*.jsonl")):
        if f.name == "smoke.jsonl":
            continue
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        sk = Counter(t for r in rows for t in (r.get("tags") or []) if t.startswith("sk:"))
        gov = Counter(r.get("govern_subtype") for r in rows if r.get("govern_subtype"))
        mx = max(sk.values()) if sk else 0
        sk_max_all = max(sk_max_all, mx)
        print(f"{f.name}: n={len(rows)} sk_max={mx} gov={dict(gov) or '-'}")
    print(f"skeleton_max_all={sk_max_all}")

    ok = (
        not empty
        and all(int(v) == 0 for v in cleans.values())
        and len(fact_band) >= 10
        and sk_max_all <= 2
        and int(core_emp) == 1000
        and not out
    )
    print("ACCEPT:" + ("PASS" if ok else "REVIEW"))


if __name__ == "__main__":
    asyncio.run(main())
