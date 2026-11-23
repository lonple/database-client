from __future__ import annotations

from decimal import Decimal
from typing import Any


def _norm_col(name: str) -> str:
    return (name or "").strip().lower()


def _to_decimal(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        return Decimal(int(v))
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    s = str(v).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def _eq(a: Any, b: Any, *, tol: Decimal) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    da, db = _to_decimal(a), _to_decimal(b)
    if da is not None and db is not None:
        return abs(da - db) <= tol
    return str(a).strip() == str(b).strip()


def _extract_columns(result: dict[str, Any]) -> list[str]:
    cols = result.get("columns") or []
    names: list[str] = []
    for c in cols:
        if isinstance(c, dict):
            names.append(str(c.get("name") or c.get("columnName") or ""))
        else:
            names.append(str(c))
    return names


def _extract_rows(result: dict[str, Any]) -> list[list[Any]]:
    rows = result.get("rows") or []
    return [list(r) if not isinstance(r, list) else r for r in rows]


def _rows_as_dicts(columns: list[str], rows: list[list[Any]]) -> list[dict[str, Any]]:
    cols = [_norm_col(c) for c in columns]
    out: list[dict[str, Any]] = []
    for row in rows or []:
        d: dict[str, Any] = {}
        for i, c in enumerate(cols):
            d[c] = row[i] if i < len(row) else None
        out.append(d)
    return out


def _required_columns(spec: dict[str, Any]) -> list[str]:
    """用例必须返回列：requiredColumns / required_columns / columns。"""
    raw = (
        spec.get("requiredColumns")
        or spec.get("required_columns")
        or spec.get("columns")
        or []
    )
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for c in raw:
        n = _norm_col(str(c))
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _missing_required(required: list[str], cols: list[str]) -> list[str]:
    have = {_norm_col(c) for c in cols}
    return [c for c in required if c not in have]


def _duplicate_rate(rows: list[dict[str, Any]], col: str) -> float:
    """重复率 = 1 - 唯一值数/行数；空表视为 0。"""
    if not rows:
        return 0.0
    vals = ["" if r.get(col) is None else str(r.get(col)) for r in rows]
    uniq = len(set(vals))
    return 1.0 - (uniq / len(vals))


def _is_fully_unique(rows: list[dict[str, Any]], col: str) -> bool:
    if not rows:
        return True
    vals = ["" if r.get(col) is None else str(r.get(col)) for r in rows]
    return len(set(vals)) == len(vals)


def pick_sort_columns(
    required: list[str],
    *,
    expect_rows: list[dict[str, Any]],
    ask_rows: list[dict[str, Any]],
    expect_cols: list[str],
    ask_cols: list[str],
) -> list[str]:
    """选排序键（用于多行对齐）。

    1. 必须列中存在完全唯一列 → 用该列
    2. 否则双方都有的非必须列中存在完全唯一列 → 用该列
    3. 否则在双方都有的字段中取重复率最低的两列（合并作键）
    唯一性/重复率以期望结果行为准（问数侧同名列参与候选过滤）。
    """
    e_set = {_norm_col(c) for c in expect_cols}
    a_set = {_norm_col(c) for c in ask_cols}
    both = [c for c in expect_cols if _norm_col(c) in a_set]
    # 保序去重
    seen: set[str] = set()
    both_cols: list[str] = []
    for c in both:
        n = _norm_col(c)
        if n and n not in seen and n in e_set:
            seen.add(n)
            both_cols.append(n)

    req = [_norm_col(c) for c in required if _norm_col(c)]
    req_in_both = [c for c in req if c in set(both_cols)]

    # 1) 必须列唯一
    for c in req_in_both or req:
        if c in e_set and c in a_set and _is_fully_unique(expect_rows, c):
            return [c]

    # 2) 非必须、双方都有的唯一列
    optional = [c for c in both_cols if c not in set(req)]
    for c in optional:
        if _is_fully_unique(expect_rows, c):
            return [c]

    # 3) 双方共有列中重复率最低的两列
    pool = both_cols or req_in_both or req
    if not pool:
        return []
    if len(pool) == 1:
        return [pool[0]]
    ranked = sorted(pool, key=lambda c: (_duplicate_rate(expect_rows, c), c))
    return ranked[:2]


def _rows_equal(a: dict[str, Any], b: dict[str, Any], cols: list[str], *, tol: Decimal) -> bool:
    return all(_eq(a.get(c), b.get(c), tol=tol) for c in cols)


def _row_tuple(row: dict[str, Any], cols: list[str], *, tol: Decimal) -> tuple:
    """用于多重集比对的规范化元组（数值按容差量化）。"""
    parts: list[Any] = []
    for c in cols:
        v = row.get(c)
        d = _to_decimal(v)
        if d is not None:
            # 量化到容差格子，避免 1.000 vs 1.001 在 tol=0.01 下误判为不同键
            q = (d / tol).to_integral_value(rounding="ROUND_HALF_UP") if tol > 0 else d
            parts.append(("n", q))
        elif v is None:
            parts.append(("z", None))
        else:
            parts.append(("s", str(v).strip()))
    return tuple(parts)


def _score_multiset(
    e_rows: list[dict[str, Any]],
    a_rows: list[dict[str, Any]],
    *,
    compare_cols: list[str],
    tol: Decimal,
) -> tuple[float, int, int, int]:
    """多重集计分。

    - matched = |expect ∩ ask|（按必须列元组）
    - 用例行更多：score = matched / expect_n
    - 问数行更多：matched' = max(0, matched - (ask_n - expect_n))，score = matched' / expect_n
    """
    from collections import Counter

    e_n = len(e_rows)
    a_n = len(a_rows)
    if e_n == 0 and a_n == 0:
        return 1.0, 0, 0, 0
    if e_n == 0:
        return 0.0, 0, 0, a_n

    ec = Counter(_row_tuple(r, compare_cols, tol=tol) for r in e_rows)
    ac = Counter(_row_tuple(r, compare_cols, tol=tol) for r in a_rows)
    matched = sum((ec & ac).values())
    if a_n > e_n:
        matched = max(0, matched - (a_n - e_n))
    score = matched / e_n
    return score, matched, e_n, a_n


def _score_join_by_sort_keys(
    e_rows: list[dict[str, Any]],
    a_rows: list[dict[str, Any]],
    *,
    sort_cols: list[str],
    compare_cols: list[str],
    tol: Decimal,
) -> tuple[float, int, int, int]:
    """按排序键分组后，组内对必须列做多重集比对，再套多余行惩罚。"""
    from collections import Counter, defaultdict

    e_n = len(e_rows)
    a_n = len(a_rows)
    if e_n == 0 and a_n == 0:
        return 1.0, 0, 0, 0
    if e_n == 0:
        return 0.0, 0, 0, a_n

    def sk(r: dict[str, Any]) -> tuple:
        return tuple("" if r.get(c) is None else str(r.get(c)) for c in sort_cols)

    e_g: dict[tuple, list] = defaultdict(list)
    a_g: dict[tuple, list] = defaultdict(list)
    for r in e_rows:
        e_g[sk(r)].append(r)
    for r in a_rows:
        a_g[sk(r)].append(r)

    matched = 0
    for k, er in e_g.items():
        ar = a_g.get(k) or []
        ec = Counter(_row_tuple(r, compare_cols, tol=tol) for r in er)
        ac = Counter(_row_tuple(r, compare_cols, tol=tol) for r in ar)
        matched += sum((ec & ac).values())

    if a_n > e_n:
        matched = max(0, matched - (a_n - e_n))
    return matched / e_n, matched, e_n, a_n


def _status_from_score(score: float, *, e_n: int, a_n: int) -> str:
    if score >= 1.0 and e_n == a_n:
        return "PASSED"
    if score >= 0.8:
        return "PARTIAL_GE_80"
    return "FAILED_COMPARE"


def compare_results(
    *,
    expect: dict[str, Any] | None,
    ask: dict[str, Any] | None,
    compare_mode: str,
    compare_spec: dict[str, Any] | None,
    ask_truncated: bool = False,
    refused: bool = False,
    dimension_lookups: dict[str, dict[str, str]] | None = None,  # 兼容旧调用，已忽略
) -> dict[str, Any]:
    """结果比对（无字段映射）。

    1. 双方都只有一列：该列降序后按值多重集比对
    2. 多列：校验用例必须列；缺则 MISSING_REQUIRED；
       在必须列中选排序列（全唯一用 1 列，否则重复率最低 2 列），
       按键分组比对必须列；仅一行时直接比必须列
    """
    _ = dimension_lookups
    spec = compare_spec or {}
    tol = _to_decimal(spec.get("tolerance")) or Decimal("0.01")
    if spec.get("numeric_tolerance") is not None:
        tol = _to_decimal(spec.get("numeric_tolerance")) or tol
    mode = (compare_mode or "").strip().lower()

    if ask_truncated and mode != "empty_or_refuse":
        return {"score": 0.0, "status": "FAILED_COMPARE", "detail": {"reason": "ask_result_truncated"}}

    if mode == "empty_or_refuse":
        ask_rows = _extract_rows(ask or {})
        has_data = len(ask_rows) > 0
        if refused or not has_data:
            return {
                "score": 1.0,
                "status": "REFUSED_OK",
                "detail": {"refused": refused, "askRowCount": len(ask_rows)},
            }
        return {
            "score": 0.0,
            "status": "REFUSED_BAD",
            "detail": {"reason": "leaked_rows", "askRowCount": len(ask_rows)},
        }

    if expect is None or ask is None:
        return {"score": 0.0, "status": "FAILED_COMPARE", "detail": {"reason": "missing_result_set"}}

    e_cols_raw = _extract_columns(expect)
    a_cols_raw = _extract_columns(ask)
    e_cols = [_norm_col(c) for c in e_cols_raw]
    a_cols = [_norm_col(c) for c in a_cols_raw]
    e_rows = _rows_as_dicts(e_cols_raw, _extract_rows(expect))
    a_rows = _rows_as_dicts(a_cols_raw, _extract_rows(ask))

    # —— 规则 1：双方都只有一列 ——
    if len(e_cols) == 1 and len(a_cols) == 1:
        ec, ac = e_cols[0], a_cols[0]
        e_cmp = [{ec: r.get(ec)} for r in e_rows]
        a_cmp = [{ec: r.get(ac)} for r in a_rows]
        score, matched, e_n, a_n = _score_multiset(e_cmp, a_cmp, compare_cols=[ec], tol=tol)
        return {
            "score": score,
            "status": _status_from_score(score, e_n=e_n, a_n=a_n),
            "detail": {
                "mode": "single_column",
                "expectColumn": ec,
                "askColumn": ac,
                "matched": matched,
                "expectRows": e_n,
                "askRows": a_n,
            },
        }

    # —— 多列：必须列 ——
    required = _required_columns(spec)
    if not required:
        return {
            "score": 0.0,
            "status": "MISSING_REQUIRED",
            "detail": {
                "reason": "missing_required_columns",
                "requiredColumns": [],
                "hint": "用例未配置必须返回列",
            },
        }

    miss_e = _missing_required(required, e_cols)
    miss_a = _missing_required(required, a_cols)
    if miss_e or miss_a:
        return {
            "score": 0.0,
            "status": "MISSING_REQUIRED",
            "detail": {
                "reason": "missing_required_columns",
                "requiredColumns": required,
                "missingInExpect": miss_e,
                "missingInAsk": miss_a,
            },
        }

    # 仅一行（双方都 ≤1）：直接比必须列
    if len(e_rows) <= 1 and len(a_rows) <= 1:
        if len(e_rows) == 0 and len(a_rows) == 0:
            return {
                "score": 1.0,
                "status": "PASSED",
                "detail": {
                    "mode": "single_row",
                    "requiredColumns": required,
                    "expectRows": 0,
                    "askRows": 0,
                },
            }
        if len(e_rows) != 1 or len(a_rows) != 1:
            score, matched, e_n, a_n = _score_multiset(
                e_rows, a_rows, compare_cols=required, tol=tol
            )
            return {
                "score": score,
                "status": _status_from_score(score, e_n=e_n, a_n=a_n),
                "detail": {
                    "mode": "single_row",
                    "requiredColumns": required,
                    "matched": matched,
                    "expectRows": e_n,
                    "askRows": a_n,
                },
            }
        ok = _rows_equal(e_rows[0], a_rows[0], required, tol=tol)
        return {
            "score": 1.0 if ok else 0.0,
            "status": "PASSED" if ok else "FAILED_COMPARE",
            "detail": {"mode": "single_row", "requiredColumns": required},
        }

    # 多行：选排序键后按键分组比对必须列
    sort_cols = pick_sort_columns(
        required,
        expect_rows=e_rows,
        ask_rows=a_rows,
        expect_cols=e_cols,
        ask_cols=a_cols,
    )
    score, matched, e_n, a_n = _score_join_by_sort_keys(
        e_rows,
        a_rows,
        sort_cols=sort_cols,
        compare_cols=required,
        tol=tol,
    )
    return {
        "score": score,
        "status": _status_from_score(score, e_n=e_n, a_n=a_n),
        "detail": {
            "mode": "multi_column",
            "requiredColumns": required,
            "sortColumns": sort_cols,
            "matched": matched,
            "expectRows": e_n,
            "askRows": a_n,
        },
    }
