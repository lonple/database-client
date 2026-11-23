#!/usr/bin/env python3
"""检查测评用例重复度：skeleton 标签、SQL 归一化骨架、题面近似。"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CASES = Path(__file__).resolve().parent / "cases"

# 业务键 / 字面量 → 占位，得到「SQL 意图骨架」
_RE_STR = re.compile(r"'[^']*'")
_RE_NUM = re.compile(r"\b\d+(\.\d+)?\b")
_RE_DATE = re.compile(r"DATE\s+'[^']*'", re.I)
_RE_WS = re.compile(r"\s+")


def norm_sql(sql: str | None) -> str | None:
    if not sql:
        return None
    s = sql.strip()
    s = _RE_DATE.sub("DATE ?", s)
    s = _RE_STR.sub("?", s)
    s = _RE_NUM.sub("?", s)
    s = _RE_WS.sub(" ", s).lower().strip()
    return s


def sk_tag(row: dict) -> str | None:
    for t in row.get("tags") or []:
        if isinstance(t, str) and t.startswith("sk:"):
            return t
    return None


def load_all() -> list[dict]:
    out: list[dict] = []
    for f in sorted(CASES.glob("*.jsonl")):
        if f.name == "smoke.jsonl":
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            row["_file"] = f.name
            out.append(row)
    return out


def jaccard_tokens(a: str, b: str) -> float:
    ta = set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", a))
    tb = set(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def main() -> None:
    rows = load_all()
    print(f"total_cases={len(rows)}")

    # --- 1) sk: 标签 ---
    by_sk: dict[str, list[str]] = defaultdict(list)
    missing_sk = 0
    for r in rows:
        sk = sk_tag(r)
        if not sk:
            missing_sk += 1
            continue
        by_sk[sk].append(r["case_key"])
    sk_counts = Counter({k: len(v) for k, v in by_sk.items()})
    print("\n=== skeleton tag (sk:) ===")
    print(f"unique={len(sk_counts)} missing={missing_sk} max={max(sk_counts.values()) if sk_counts else 0}")
    over = [(k, n) for k, n in sk_counts.most_common() if n > 2]
    print(f"over_cap(>2)={len(over)}")
    for k, n in sk_counts.most_common(15):
        print(f"  {k}: {n}")

    # --- 2) 按 category + 归一化 SQL ---
    print("\n=== normalized SQL skeleton (by category) ===")
    for cat in [
        "SINGLE_FILTER",
        "MULTI_JOIN_FILTER",
        "SINGLE_AGG",
        "MULTI_JOIN_AGG",
        "MULTI_GOVERN_FILTER",
        "MULTI_GOVERN_AGG",
    ]:
        subset = [r for r in rows if r["category"] == cat]
        groups: dict[str, list[dict]] = defaultdict(list)
        no_sql = 0
        for r in subset:
            ns = norm_sql(r.get("expect_sql"))
            if ns is None:
                no_sql += 1
                continue
            groups[ns].append(r)
        sizes = sorted((len(v) for v in groups.values()), reverse=True)
        max_n = sizes[0] if sizes else 0
        gt2 = sum(1 for n in sizes if n > 2)
        gt1 = sum(1 for n in sizes if n > 1)
        print(
            f"{cat}: n={len(subset)} unique_sql={len(groups)} no_sql={no_sql} "
            f"max_dup={max_n} groups_>1={gt1} groups_>2={gt2}"
        )
        # 展示最重复的几组
        top = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:5]
        for ns, items in top:
            if len(items) < 2:
                continue
            keys = [x["case_key"] for x in items]
            gov = Counter(x.get("govern_subtype") for x in items)
            print(f"  x{len(items)} gov={dict(gov)} keys={keys[:6]}{'...' if len(keys)>6 else ''}")
            print(f"    sql≈ {ns[:140]}{'...' if len(ns)>140 else ''}")
            qs = [x["question"][:40] for x in items[:3]]
            for q in qs:
                print(f"    q: {q}")

    # --- 3) BOARD only ---
    print("\n=== BOARD only (normalized SQL) ===")
    for cat in ["MULTI_GOVERN_FILTER", "MULTI_GOVERN_AGG"]:
        subset = [r for r in rows if r["category"] == cat and r.get("govern_subtype") == "BOARD"]
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in subset:
            ns = norm_sql(r.get("expect_sql"))
            if ns:
                groups[ns].append(r)
        sizes = sorted((len(v) for v in groups.values()), reverse=True)
        print(
            f"{cat} BOARD: n={len(subset)} unique={len(groups)} "
            f"max={sizes[0] if sizes else 0} >2={sum(1 for n in sizes if n>2)}"
        )
        for ns, items in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:8]:
            if len(items) < 2:
                continue
            print(f"  x{len(items)} {[x['case_key'] for x in items]}")
            print(f"    {ns[:160]}")

    # --- 4) 题面近似（同 category 内 Jaccard≥0.75，且非同一 sk）---
    print("\n=== question near-dup (Jaccard>=0.75, different sk, same category) ===")
    near_pairs = 0
    samples = []
    for cat in [
        "SINGLE_FILTER",
        "MULTI_JOIN_FILTER",
        "SINGLE_AGG",
        "MULTI_JOIN_AGG",
        "MULTI_GOVERN_FILTER",
        "MULTI_GOVERN_AGG",
    ]:
        subset = [r for r in rows if r["category"] == cat]
        # 去掉数字/工号后的题面，避免参数差掩盖雷同
        def qnorm(q: str) -> str:
            q = re.sub(r"[A-Z]{1,5}\d{3,}", "CODE", q)
            q = re.sub(r"\d{4}", "YEAR", q)
            q = re.sub(r"\d+", "N", q)
            return q

        for i in range(len(subset)):
            for j in range(i + 1, len(subset)):
                a, b = subset[i], subset[j]
                if sk_tag(a) and sk_tag(a) == sk_tag(b):
                    continue  # 同骨架允许最多 2 条，不算「意外雷同」
                sim = jaccard_tokens(qnorm(a["question"]), qnorm(b["question"]))
                if sim >= 0.75:
                    near_pairs += 1
                    if len(samples) < 20:
                        samples.append((sim, cat, a["case_key"], b["case_key"], a["question"], b["question"]))
    print(f"near_pairs={near_pairs}")
    for sim, cat, ka, kb, qa, qb in sorted(samples, key=lambda x: -x[0])[:12]:
        print(f"  {sim:.2f} [{cat}] {ka} vs {kb}")
        print(f"    A: {qa[:60]}")
        print(f"    B: {qb[:60]}")

    # --- 5) 方案甲合规：sk 与 norm_sql 双视角 ---
    print("\n=== verdict ===")
    sk_ok = missing_sk == 0 and (not sk_counts or max(sk_counts.values()) <= 2)
    # 对有 SQL 的用例，同 category 内 norm_sql 出现次数
    sql_over = []
    for cat in [
        "SINGLE_FILTER",
        "MULTI_JOIN_FILTER",
        "SINGLE_AGG",
        "MULTI_JOIN_AGG",
        "MULTI_GOVERN_FILTER",
        "MULTI_GOVERN_AGG",
    ]:
        subset = [r for r in rows if r["category"] == cat]
        groups: dict[str, list[str]] = defaultdict(list)
        for r in subset:
            ns = norm_sql(r.get("expect_sql"))
            if ns:
                groups[ns].append(r["case_key"])
        for ns, keys in groups.items():
            if len(keys) > 2:
                sql_over.append((cat, len(keys), keys[:5], ns[:100]))
    print(f"sk_cap_ok={sk_ok}")
    print(f"norm_sql_groups_>2={len(sql_over)}")
    for cat, n, keys, ns in sql_over[:15]:
        print(f"  FAIL {cat} x{n} {keys} :: {ns}")

    # --- 6) 全表覆盖（有 expect_sql 提及 company.<table>）---
    print("\n=== extended table coverage ===")
    try:
        import asyncio

        import asyncpg
    except ImportError:
        print("skip coverage (asyncpg missing)")
        return

    table_re = re.compile(r"\bcompany\.([a-zA-Z_][a-zA-Z0-9_]*)\b", re.I)
    mentioned: set[str] = set()
    for r in rows:
        sql = r.get("expect_sql")
        if not sql:
            continue
        mentioned |= {m.group(1).lower() for m in table_re.finditer(sql)}

    async def _tables() -> set[str]:
        conn = await asyncpg.connect("postgresql://postgres:root@127.0.0.1:5432/postgres")
        try:
            rs = await conn.fetch(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='company' AND table_type='BASE TABLE'
                """
            )
            return {x["table_name"] for x in rs}
        finally:
            await conn.close()

    all_tables = asyncio.run(_tables())
    missing = sorted(all_tables - mentioned)
    print(f"mentioned={len(mentioned)} total={len(all_tables)} missing={len(missing)}")
    if missing:
        print("missing_tables:", missing[:40])
    sizes = []
    for cat in [
        "SINGLE_FILTER",
        "MULTI_JOIN_FILTER",
        "SINGLE_AGG",
        "MULTI_JOIN_AGG",
        "MULTI_GOVERN_FILTER",
        "MULTI_GOVERN_AGG",
    ]:
        subset = [r for r in rows if r["category"] == cat]
        groups: dict[str, int] = defaultdict(int)
        for r in subset:
            ns = norm_sql(r.get("expect_sql"))
            if ns:
                groups[ns] += 1
        sizes.append(max(groups.values()) if groups else 0)
    print(f"norm_sql_max={max(sizes) if sizes else 0} extended_coverage={len(mentioned)}")
    print(
        f"verdict_ok={sk_ok and len(sql_over) == 0 and not missing and (max(sizes) if sizes else 0) <= 2}"
    )


if __name__ == "__main__":
    main()
