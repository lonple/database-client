#!/usr/bin/env python3
"""从 company 库元数据生成口语化测评用例 JSONL，校验并可选导入 askdata.eval_case。

硬性约束：
- 归一化 SQL 骨架（字面量占位）同 category 内 ≤2
- company schema 全表覆盖（有 expect_sql 的用例提及 company.<table>）
- 配额见 quota.md；BOARD 期望 SQL 用最简两表写法，不为凑治理分堆复杂度

用法：
  .\\dbc-askdata\\.venv\\Scripts\\python.exe .\\scripts\\demo-company\\eval\\gen_cases.py
  .\\dbc-askdata\\.venv\\Scripts\\python.exe .\\scripts\\demo-company\\eval\\gen_cases.py --validate-only
  .\\dbc-askdata\\.venv\\Scripts\\python.exe .\\scripts\\demo-company\\eval\\gen_cases.py --import-db
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import asyncpg

DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"
OUT = Path(__file__).resolve().parent / "cases"
META_CATALOG = Path(__file__).resolve().parents[1] / "metadata" / "extended_catalog.json"
SEED = 20261015
TEMPLATE_CODE = "company_eval_v2"
REMOVED_CATEGORIES = frozenset({"MULTI_GOVERN_FILTER", "MULTI_GOVERN_AGG"})

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


def case(
    key: str,
    category: str,
    question: str,
    sql: str | None,
    compare_mode: str,
    compare_spec: dict,
    *,
    govern_subtype: str | None = None,
    hitl_replies: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    return {
        "case_key": key,
        "scope": "TEMPLATE",
        "category": category,
        "govern_subtype": govern_subtype,
        "question": question,
        "expect_sql": sql,
        "compare_mode": compare_mode,
        "compare_spec": compare_spec,
        "hitl_replies": hitl_replies,
        "tags": tags or [],
    }


def pick(rng: random.Random, *options: str) -> str:
    return rng.choice(options)


def utter(i: int, primary: str, *alts: str) -> str:
    if not alts or i % 4 != 1:
        return primary
    return alts[(i // 4) % len(alts)]


ASK_OPENERS = [
    "请帮我",
    "请帮我查下",
    "请帮我看一下",
    "请帮我查一下",
    "麻烦帮我查下",
    "麻烦帮我看下",
    "能不能帮我查一下",
    "帮我确认下",
    "辛苦帮我看下",
    "劳驾帮我查一下",
    "帮忙核对一下",
    "请帮忙查一下",
    "烦请帮我看下",
    "拜托帮我查下",
]


def with_ask(i: int, body: str) -> str:
    body = body.strip()
    if body.startswith(
        (
            "请帮",
            "麻烦",
            "能不能",
            "辛苦",
            "劳驾",
            "拜托",
            "烦请",
            "帮忙核",
            "请帮忙",
        )
    ):
        return body
    if i % 4 != 0:
        return body
    opener = ASK_OPENERS[(i // 4) % len(ASK_OPENERS)]
    for s in (
        "帮我看下",
        "帮我查一下",
        "帮我查下",
        "帮我捞",
        "帮我看一下",
        "帮我确认下",
        "帮我",
        "确认下",
        "看下",
        "查一下",
        "查下",
    ):
        if body.startswith(s):
            body = body[len(s) :].lstrip("，, ：: ")
            break
    joiner = ("：", "，", "——")[i % 3]
    return f"{opener}{joiner}{body}"


def quote_label(i: int, label: str) -> str:
    style = i % 3
    if style == 0:
        return f" {label} "
    if style == 1:
        return f"“{label}”"
    return f'"{label}"'


DIVERSIFY_TAILS = [
    "给我一份清单",
    "按编号排一下",
    "全量列出来就行",
    "结果按顺序排好",
    "帮忙整理一下",
    "导出编号列表即可",
    "做成一览表",
    "方便对账用",
    "看板口径",
    "只要最终名单",
    "按业务日常口径",
    "不要漏行",
]


def diversify_question(q: str, salt: str) -> str:
    base = q.rstrip("。．. ")
    idx = sum(ord(ch) for ch in salt) % len(DIVERSIFY_TAILS)
    for step in range(len(DIVERSIFY_TAILS)):
        tail = DIVERSIFY_TAILS[(idx + step) % len(DIVERSIFY_TAILS)]
        if tail in base:
            continue
        return f"{base}，{tail}。"
    return f"{base}，再核一遍清单。"


def two(seq: list, a: int, b: int):
    if not seq:
        raise ValueError("empty seq")
    if len(seq) == 1:
        return [seq[0], seq[0]]
    i = a % len(seq)
    j = b % len(seq)
    if i == j:
        j = (j + 1) % len(seq)
    return [seq[i], seq[j]]


def add(
    out: list[dict],
    *,
    sk: str,
    key: str,
    cat: str,
    q: str,
    sql: str | None,
    mode: str,
    spec: dict,
    govern_subtype: str | None = None,
    hitl_replies: list[str] | None = None,
    tags: list[str] | None = None,
) -> None:
    tag_list = [f"sk:{sk}"]
    for t in tags or []:
        if t and not str(t).startswith("sk:"):
            tag_list.append(t)
    out.append(
        case(
            key,
            cat,
            q,
            sql,
            mode,
            spec,
            govern_subtype=govern_subtype,
            hitl_replies=hitl_replies,
            tags=tag_list,
        )
    )


async def load_meta(conn: asyncpg.Connection):
    from gen_cases_build import (
        CORE_ZH,
        SchemaMeta,
        TableMeta,
        pick_business_key,
        pick_display_cols,
    )

    catalog: dict = {}
    if META_CATALOG.is_file():
        catalog = json.loads(META_CATALOG.read_text(encoding="utf-8")).get("tables", {})

    table_names = [
        r["table_name"]
        for r in await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'company' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    ]

    comments = {
        r["table_name"]: r["zh"]
        for r in await conn.fetch(
            """
            SELECT c.relname AS table_name, obj_description(c.oid) AS zh
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'company' AND c.relkind = 'r'
            """
        )
    }

    col_rows = await conn.fetch(
        """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'company'
        ORDER BY table_name, ordinal_position
        """
    )
    cols_by: dict[str, list[str]] = defaultdict(list)
    types_by: dict[str, dict[str, str]] = defaultdict(dict)
    for r in col_rows:
        cols_by[r["table_name"]].append(r["column_name"])
        types_by[r["table_name"]][r["column_name"]] = r["data_type"]

    col_zh_rows = await conn.fetch(
        """
        SELECT c.relname AS table_name, a.attname AS column_name,
               col_description(a.attrelid, a.attnum) AS zh
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'company' AND c.relkind = 'r'
          AND a.attnum > 0 AND NOT a.attisdropped
        """
    )
    col_zh_by: dict[str, dict[str, str]] = defaultdict(dict)
    for r in col_zh_rows:
        if r["zh"]:
            col_zh_by[r["table_name"]][r["column_name"]] = r["zh"]

    fk_rows = await conn.fetch(
        """
        SELECT
          tc.table_name AS src_table,
          kcu.column_name AS src_col,
          ccu.table_name AS dst_table,
          ccu.column_name AS dst_col
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'company'
        """
    )
    fk_edges = [
        (r["src_table"], r["src_col"], r["dst_table"], r["dst_col"]) for r in fk_rows
    ]
    fks_by: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for src, scol, dst, dcol in fk_edges:
        fks_by[src].append((scol, dst, dcol))

    tables: dict[str, TableMeta] = {}
    for tname in table_names:
        columns = cols_by[tname]
        col_types = types_by[tname]
        bk, has_code, has_user = pick_business_key(columns)
        cat_entry = catalog.get(tname) or {}
        zh = (
            CORE_ZH.get(tname)
            or (cat_entry.get("zh") if isinstance(cat_entry, dict) else None)
            or comments.get(tname)
            or tname
        )
        col_zh = dict(col_zh_by.get(tname) or {})
        if isinstance(cat_entry, dict):
            for ck, cv in (cat_entry.get("columns") or {}).items():
                if cv and ck not in col_zh:
                    col_zh[ck] = cv
        display = pick_display_cols(columns, col_types, bk)
        # 业务键抽样：名称类尽量取唯一值，避免单行 scalar 撞车
        vals: list = []
        if has_user and bk != "id":
            if has_code:
                q = (
                    f'SELECT "{bk}" AS v FROM company."{tname}" '
                    f'WHERE "{bk}" IS NOT NULL ORDER BY 1 LIMIT 8'
                )
            else:
                q = (
                    f'SELECT "{bk}" AS v FROM company."{tname}" '
                    f'WHERE "{bk}" IS NOT NULL '
                    f'GROUP BY "{bk}" HAVING count(*) = 1 ORDER BY 1 LIMIT 8'
                )
            try:
                vals = [r["v"] for r in await conn.fetch(q)]
            except Exception:
                vals = []
            if not vals:
                try:
                    vals = [
                        r["v"]
                        for r in await conn.fetch(
                            f'SELECT "{bk}" AS v FROM company."{tname}" '
                            f'WHERE "{bk}" IS NOT NULL ORDER BY 1 LIMIT 8'
                        )
                    ]
                except Exception:
                    vals = []
        tables[tname] = TableMeta(
            name=tname,
            zh=str(zh),
            columns=columns,
            col_types=col_types,
            col_zh=col_zh,
            business_key=bk,
            key_values=vals,
            display_cols=display,
            has_code_key=has_code,
            has_user_key=has_user and bool(vals),
            fks=fks_by.get(tname, []),
        )

    conflict = [
        r["emp_no"]
        for r in await conn.fetch(
            """
            SELECT emp_no FROM company.hr_employee
            WHERE leave_date IS NOT NULL AND employment_status = 'active'
            ORDER BY emp_no
            """
        )
    ]

    neighbors: dict[str, list] = defaultdict(list)
    for src, scol, dst, dcol in fk_edges:
        neighbors[src].append((dst, scol, dcol, "child"))
        neighbors[dst].append((src, scol, dcol, "parent"))

    return SchemaMeta(
        tables=tables,
        fk_edges=fk_edges,
        conflict_emps=conflict,
        neighbors=dict(neighbors),
    )


def _finalize_questions(cases: list[dict]) -> list[dict]:
    by_key = {c["case_key"]: c for c in cases}
    cases = list(by_key.values())
    seen: set[str] = set()
    for c in cases:
        q = c["question"]
        if q in seen:
            base = q
            for n in range(12):
                cand = diversify_question(base, f"{c['case_key']}:{n}")
                if cand not in seen:
                    q = cand
                    break
            else:
                q = diversify_question(base, c["case_key"] + "-x")
        c["question"] = q
        seen.add(q)
    for c in cases:
        seed_i = sum(ord(ch) for ch in c["case_key"])
        c["question"] = with_ask(seed_i, c["question"])
    seen2: set[str] = set()
    for c in cases:
        q = c["question"]
        if q in seen2:
            for n in range(12):
                cand = diversify_question(q, f"ask:{c['case_key']}:{n}")
                if cand not in seen2:
                    q = cand
                    break
        c["question"] = q
        seen2.add(q)
    return cases


def _has_internal_id_in_question(question: str) -> bool:
    q = question or ""
    if "主键" in q:
        return True
    if re.search(r"内部\s*id", q, re.I):
        return True
    # 「编号 1」「编号是 2」等裸数字行号口吻（业务单号一般带字母前缀）
    if re.search(r"编号\s*(是\s*)?\d+\b", q):
        return True
    return False


def _sql_where_filters_bare_id(sql: str | None) -> bool:
    """期望 SQL 的 WHERE 是否用内部 id 数值过滤（JOIN ON 技术键允许）。"""
    if not sql:
        return False
    # 粗切 WHERE 段，避免误伤 SELECT/JOIN
    m = re.search(r"\bWHERE\b([\s\S]+?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|$)", sql, re.I)
    if not m:
        return False
    where = m.group(1)
    return bool(re.search(r"\b(?:\w+\.)?id\s*=\s*\d+\b", where, re.I))


def _has_english_field_leak(question: str) -> bool:
    """题面禁止出现明显英文字段名（允许业务编码值如 E230001、ROOM01）。"""
    # snake_case 字段
    if re.search(r"\b[a-z]+_[a-z0-9_]+\b", question):
        return True
    return False


def govern_score(sql: str) -> int:
    """对齐 govern_boundary.md 的粗分（用于 BOARD 门禁）。"""
    from gen_cases_build import tables_in_sql

    s = sql.strip()
    low = s.lower()
    score = 0
    tables = tables_in_sql(s)
    joins = len(re.findall(r"\bjoin\b", low))
    # 多表：源表≥3 或 JOIN≥2；两表单 JOIN 不计
    if len(tables) >= 3 or joins >= 2:
        if not (len(tables) == 2 and joins <= 1):
            score += 1
    # 单层汇总
    if re.search(r"\b(group\s+by|count\s*\(|sum\s*\(|avg\s*\(|max\s*\(|min\s*\()", low):
        score += 1
    # 去重后再算 / DISTINCT ON
    if re.search(r"\bdistinct\s+on\b", low) or (
        "distinct" in low and re.search(r"\b(group\s+by|count\s*\(|sum\s*\()", low)
    ):
        score += 1
    # 窗口后再算
    if re.search(r"\b(row_number|rank|dense_rank|lag|lead)\s*\(", low):
        score += 1
    # 嵌套 / CTE / EXISTS
    if re.search(r"\bwith\b", low) or re.search(r"\bexists\b", low):
        score += 1
    elif low.count("select") >= 2:
        score += 1
    # UNION
    if re.search(r"\bunion\b", low):
        score += 1
    # 源表≥4 / JOIN≥3 / 嵌套≥2 → 直接治理
    if len(tables) >= 4 or joins >= 3 or low.count("select") >= 3:
        return max(score, 2)
    return score


def norm_sql_stats(cases: list[dict]) -> tuple[int, list[tuple[str, int, str]]]:
    """返回全局 max 及超限列表 (category, count, norm)。"""
    over: list[tuple[str, int, str]] = []
    global_max = 0
    for cat in {
        c["category"] for c in cases
    }:
        groups: dict[str, list[str]] = defaultdict(list)
        for c in cases:
            if c["category"] != cat:
                continue
            ns = norm_sql(c.get("expect_sql"))
            if ns:
                groups[ns].append(c["case_key"])
        for ns, keys in groups.items():
            global_max = max(global_max, len(keys))
            if len(keys) > 2:
                over.append((cat, len(keys), ns[:120]))
    return global_max, over


def coverage_stats(cases: list[dict], all_tables: set[str]) -> tuple[set[str], list[str]]:
    from gen_cases_build import tables_in_sql

    mentioned: set[str] = set()
    for c in cases:
        if c.get("expect_sql"):
            mentioned |= tables_in_sql(c["expect_sql"])
    missing = sorted(all_tables - mentioned)
    return mentioned, missing


def skeleton_tag_stats(cases: list[dict]) -> tuple[Counter, int]:
    ctr: Counter = Counter()
    missing: list[str] = []
    for c in cases:
        sk = next((t for t in (c.get("tags") or []) if str(t).startswith("sk:")), None)
        if not sk:
            missing.append(c["case_key"])
            continue
        ctr[sk] += 1
    mx = max(ctr.values()) if ctr else 0
    print("by_category:", dict(Counter(c["category"] for c in cases)))
    print(
        "govern_subtype:",
        dict(Counter((c.get("govern_subtype") or "-") for c in cases if "GOVERN" in c["category"])),
    )
    print(f"skeleton_tag: unique={len(ctr)} max={mx} missing={len(missing)}")
    return ctr, mx


def build_cases(meta, rng: random.Random) -> list[dict]:
    from gen_cases_build import append_dirty_sample, build_core_cases

    out = build_core_cases(meta, rng)
    append_dirty_sample(out, meta, rng)
    return _finalize_questions(out)


async def validate(conn: asyncpg.Connection, cases: list[dict]) -> tuple[int, int, int]:
    ok = fail = skip = 0
    for c in cases:
        sql = c.get("expect_sql")
        if not sql:
            skip += 1
            continue
        try:
            await conn.fetch(sql)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"FAIL {c['case_key']}: {e}\nSQL: {sql}\n")
    return ok, fail, skip


def write_cases(cases: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    grouping = {
        "SINGLE_FILTER": "01_single_filter.jsonl",
        "MULTI_JOIN_FILTER": "02_multi_join_filter.jsonl",
        "SINGLE_AGG": "03_single_agg.jsonl",
        "MULTI_JOIN_AGG": "04_multi_join_agg.jsonl",
    }
    buckets: dict[str, list] = {k: [] for k in grouping}
    extras: list[dict] = []
    for c in cases:
        cat = c["category"]
        if cat in REMOVED_CATEGORIES:
            continue
        if cat in buckets:
            buckets[cat].append(c)
        else:
            extras.append(c)
    for cat, name in grouping.items():
        path = OUT / name
        rows = sorted(buckets[cat], key=lambda x: x["case_key"])
        path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
        print(f"write {path.name}: {len(rows)}")
    if extras:
        path = OUT / "99_extra.jsonl"
        path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in extras) + "\n",
            encoding="utf-8",
        )
        print(f"write {path.name}: {len(extras)}")


def load_cases_from_disk() -> list[dict]:
    cases: list[dict] = []
    for p in sorted(OUT.glob("*.jsonl")):
        if p.name == "smoke.jsonl":
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                case = json.loads(line)
                if case.get("category") not in REMOVED_CATEGORIES:
                    cases.append(case)
    return cases


async def import_to_db(conn: asyncpg.Connection, cases: list[dict]) -> tuple[int, int]:
    tpl = await conn.fetchrow(
        "SELECT id FROM askdata.eval_template WHERE code = $1", TEMPLATE_CODE
    )
    if not tpl:
        tpl = await conn.fetchrow(
            """
            INSERT INTO askdata.eval_template (code, name, version, remark, enabled)
            VALUES ($1, $2, $3, $4, TRUE)
            RETURNING id
            """,
            TEMPLATE_CODE,
            "演示公司测评模板 v2",
            "v2",
            "演示公司 company_eval_v2；全表覆盖+归一化骨架≤2",
        )
    template_id = tpl["id"]
    upserted = 0
    skipped = 0
    for c in cases:
        case_key = str(c.get("case_key") or "").strip()
        question = str(c.get("question") or "").strip()
        compare_mode = str(c.get("compare_mode") or "").strip()
        category = str(c.get("category") or "").strip()
        if not case_key or not question or not compare_mode or not category or category in REMOVED_CATEGORIES:
            skipped += 1
            continue
        spec = c.get("compare_spec") if isinstance(c.get("compare_spec"), dict) else {}
        replies = c.get("hitl_replies")
        tags = c.get("tags")
        existing = await conn.fetchrow(
            "SELECT id, scope FROM askdata.eval_case WHERE case_key = $1", case_key
        )
        if existing is None:
            await conn.execute(
                """
                INSERT INTO askdata.eval_case (
                  case_key, scope, template_id, project_id, category, govern_subtype,
                  question, expect_sql, compare_mode, compare_spec_json,
                  hitl_replies_json, tags_json, difficulty, enabled
                ) VALUES (
                  $1,'TEMPLATE',$2,NULL,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10::jsonb,$11,TRUE
                )
                """,
                case_key,
                template_id,
                category,
                c.get("govern_subtype"),
                question,
                c.get("expect_sql"),
                compare_mode,
                json.dumps(spec, ensure_ascii=False),
                json.dumps(replies, ensure_ascii=False) if replies is not None else None,
                json.dumps(tags, ensure_ascii=False) if tags is not None else None,
                c.get("difficulty"),
            )
        else:
            if existing["scope"] != "TEMPLATE":
                skipped += 1
                continue
            await conn.execute(
                """
                UPDATE askdata.eval_case SET
                  template_id = $2,
                  category = $3,
                  govern_subtype = $4,
                  question = $5,
                  expect_sql = $6,
                  compare_mode = $7,
                  compare_spec_json = $8::jsonb,
                  hitl_replies_json = $9::jsonb,
                  tags_json = $10::jsonb,
                  difficulty = COALESCE($11, difficulty),
                  enabled = TRUE,
                  updated_at = NOW()
                WHERE case_key = $1
                """,
                case_key,
                template_id,
                category,
                c.get("govern_subtype"),
                question,
                c.get("expect_sql"),
                compare_mode,
                json.dumps(spec, ensure_ascii=False),
                json.dumps(replies, ensure_ascii=False) if replies is not None else None,
                json.dumps(tags, ensure_ascii=False) if tags is not None else None,
                c.get("difficulty"),
            )
        upserted += 1
    return upserted, skipped


def gate_cases(cases: list[dict], all_tables: set[str]) -> None:
    # 题面英文字段
    leaks = [c["case_key"] for c in cases if _has_english_field_leak(c["question"])]
    if leaks:
        print("WARN english-like field in question:", leaks[:20], f"... n={len(leaks)}")

    id_q = [c["case_key"] for c in cases if _has_internal_id_in_question(c["question"])]
    if id_q:
        print("internal id in question:", id_q[:20], f"... n={len(id_q)}")
        raise SystemExit("question must not use 主键/内部 id")

    id_sql = [c["case_key"] for c in cases if _sql_where_filters_bare_id(c.get("expect_sql"))]
    if id_sql:
        print("WHERE id=N in expect_sql:", id_sql[:20], f"... n={len(id_sql)}")
        raise SystemExit("expect_sql must not filter by bare internal id")

    # 复杂类：有 requiredColumns 则题面须提示返回
    complex_cats = {
        "MULTI_JOIN_FILTER",
        "MULTI_JOIN_AGG",
        "MULTI_GOVERN_FILTER",
        "MULTI_GOVERN_AGG",
    }
    miss_ret = []
    for c in cases:
        if c["category"] not in complex_cats or not c.get("expect_sql"):
            continue
        if (c.get("govern_subtype") or "") == "HITL_NO_SUPPLEMENT":
            continue
        # HITL 题面故意含糊，返回字段写在 hitl_replies
        if (c.get("govern_subtype") or "") == "HITL_SUPPLEMENT":
            continue
        spec = c.get("compare_spec") or {}
        req = spec.get("requiredColumns") or spec.get("columns") or []
        if not req:
            continue
        q = c.get("question") or ""
        if not any(k in q for k in ("需要返回", "把", "带出", "列出来", "查出来", "查回")):
            miss_ret.append(c["case_key"])
    if miss_ret:
        print("complex case missing return hint:", miss_ret[:20], f"... n={len(miss_ret)}")
        raise SystemExit("complex cases with requiredColumns must state return fields in question")

    # BOARD 金标按最简正确写法（两表直连）；不再为凑治理分堆 JOIN/EXISTS
    mx, over = norm_sql_stats(cases)
    print(f"norm_sql max={mx} over_groups={len(over)}")
    for cat, n, ns in over[:20]:
        print(f"  OVER {cat} x{n} :: {ns}")
    if mx > 2 or over:
        raise SystemExit("norm_sql skeleton gate failed")

    mentioned, missing = coverage_stats(cases, all_tables)
    print(f"table_coverage: {len(mentioned)}/{len(all_tables)} missing={missing[:40]}")
    if missing:
        raise SystemExit(f"coverage incomplete: {len(missing)} tables")

    # 配额
    by_cat = Counter(c["category"] for c in cases)
    expect = {
        "SINGLE_FILTER": (100, 101),  # +dirty
        "MULTI_JOIN_FILTER": (100, 100),
        "SINGLE_AGG": (100, 100),
        "MULTI_JOIN_AGG": (100, 100),
    }
    for cat, (lo, hi) in expect.items():
        n = by_cat.get(cat, 0)
        if not (lo <= n <= hi):
            raise SystemExit(f"quota fail {cat}={n} expected {lo}..{hi}")

    if any(c["category"] in REMOVED_CATEGORIES for c in cases):
        raise SystemExit("retired evaluation categories are not allowed")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--import-db", action="store_true", help="upsert jsonl into askdata.eval_case")
    parser.add_argument("--dsn", default=DSN)
    args = parser.parse_args()

    conn = await asyncpg.connect(args.dsn)
    try:
        if args.validate_only:
            cases = load_cases_from_disk()
            all_tables = {
                r["table_name"]
                for r in await conn.fetch(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema='company' AND table_type='BASE TABLE'
                    """
                )
            }
            ok, fail, skip = await validate(conn, cases)
            print(f"validate: ok={ok} fail={fail} skip={skip} total={len(cases)}")
            skeleton_tag_stats(cases)
            gate_cases(cases, all_tables)
            if fail:
                raise SystemExit(1)
            if args.import_db:
                up, sk = await import_to_db(conn, cases)
                total = await conn.fetchval(
                    "SELECT count(*) FROM askdata.eval_case WHERE scope='TEMPLATE'"
                )
                print(f"import: upserted={up} skipped={sk} template_cases={total}")
            raise SystemExit(0)

        meta = await load_meta(conn)
        print(f"meta tables={len(meta.tables)} fks={len(meta.fk_edges)}")
        rng = random.Random(SEED)
        cases = build_cases(meta, rng)
        ok, fail, skip = await validate(conn, cases)
        print(f"pre-write validate: ok={ok} fail={fail} skip={skip} total={len(cases)}")
        skeleton_tag_stats(cases)
        gate_cases(cases, set(meta.tables.keys()))
        if fail:
            raise SystemExit(1)
        write_cases(cases)

        if args.import_db:
            up, sk = await import_to_db(conn, cases)
            total = await conn.fetchval(
                "SELECT count(*) FROM askdata.eval_case WHERE scope='TEMPLATE'"
            )
            print(f"import: upserted={up} skipped={sk} template_cases={total}")
        else:
            # 默认也导入（用户要求生成后写库）；可用环境跳过？用户明确要求导入
            up, sk = await import_to_db(conn, cases)
            total = await conn.fetchval(
                "SELECT count(*) FROM askdata.eval_case WHERE scope='TEMPLATE'"
            )
            print(f"import: upserted={up} skipped={sk} template_cases={total}")

        # 交付摘要
        mx, _ = norm_sql_stats(cases)
        mentioned, missing = coverage_stats(cases, set(meta.tables.keys()))
        print("--- DELIVERY ---")
        print("by_category:", dict(Counter(c["category"] for c in cases)))
        print(
            "govern:",
            dict(Counter((c.get("govern_subtype") or "-") for c in cases if "GOVERN" in c["category"])),
        )
        print(f"norm_sql_max={mx}")
        print(f"coverage={len(mentioned)}/{len(meta.tables)} missing={missing}")
        print(f"validate ok={ok} fail={fail} skip={skip}")
        total = await conn.fetchval("SELECT count(*) FROM askdata.eval_case WHERE scope='TEMPLATE'")
        print(f"db_eval_case_template={total}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
