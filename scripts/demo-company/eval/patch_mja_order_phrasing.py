"""为 MULTI_JOIN_AGG 题面补上「按度量从高到低，相同则按维度升序」。

更新：
- cases/04_multi_join_agg.jsonl
- askdata.eval_case（category=MULTI_JOIN_AGG）
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import asyncpg

HERE = Path(__file__).resolve().parent
JSONL = HERE / "cases" / "04_multi_join_agg.jsonl"
DSN = "postgresql://postgres:root@127.0.0.1:5432/postgres"

METRIC_ZH = {
    "cnt": "条数",
    "amt": "合计金额",
}


def dim_zh_from_question(q: str, metric_zh: str) -> str:
    """从「需要返回A、B」推断维度中文名。"""
    marker = "需要返回"
    if marker not in q:
        return "编码"
    tail = q.split(marker, 1)[1]
    tail = tail.split("；", 1)[0].split("。", 1)[0]
    parts = [p.strip() for p in tail.replace("，", "、").split("、") if p.strip()]
    for p in parts:
        if p != metric_zh:
            return p
    return parts[0] if parts else "编码"


def with_order_hint(q: str, *, primary_zh: str, tie_zh: str) -> str:
    hint = f"按{primary_zh}从高到低排序，相同则按{tie_zh}升序"
    base = q.rstrip("。．. ")
    if "从高到低" in base and "相同则按" in base:
        return base + "。"
    return f"{base}；{hint}。"


def patch_row(row: dict) -> dict:
    spec = row.get("compare_spec") or row.get("compare_spec_json") or {}
    if isinstance(spec, str):
        spec = json.loads(spec)
    order_cols = spec.get("order_columns") or []
    if len(order_cols) < 2:
        return row
    metric, dim = order_cols[0], order_cols[1]
    metric_zh = METRIC_ZH.get(metric, metric)
    q = row.get("question") or ""
    tie_zh = dim_zh_from_question(q, metric_zh)
    row = dict(row)
    row["question"] = with_order_hint(q, primary_zh=metric_zh, tie_zh=tie_zh)
    return row


def patch_jsonl() -> int:
    lines = JSONL.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    n = 0
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        neu = patch_row(row)
        if neu["question"] != row.get("question"):
            n += 1
        out.append(json.dumps(neu, ensure_ascii=False))
    JSONL.write_text("\n".join(out) + "\n", encoding="utf-8")
    return n


async def patch_db() -> int:
    c = await asyncpg.connect(DSN)
    rows = await c.fetch(
        """
        SELECT id, question, compare_spec_json
        FROM askdata.eval_case
        WHERE category='MULTI_JOIN_AGG' AND enabled=true
        """
    )
    n = 0
    for r in rows:
        spec = r["compare_spec_json"]
        if isinstance(spec, str):
            spec = json.loads(spec)
        fake = {
            "question": r["question"],
            "compare_spec": spec,
        }
        neu = patch_row(fake)
        if neu["question"] != r["question"]:
            await c.execute(
                "UPDATE askdata.eval_case SET question=$1, updated_at=NOW() WHERE id=$2",
                neu["question"],
                r["id"],
            )
            n += 1
    await c.close()
    return n


async def main() -> None:
    n_file = patch_jsonl()
    n_db = await patch_db()
    print(f"jsonl updated={n_file} path={JSONL}")
    print(f"db eval_case updated={n_db}")


if __name__ == "__main__":
    asyncio.run(main())
