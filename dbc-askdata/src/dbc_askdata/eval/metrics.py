from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def _case_elapsed_ms(c: Any) -> int | None:
    started = getattr(c, "started_at", None)
    finished = getattr(c, "finished_at", None)
    if started is None or finished is None:
        return None
    return max(0, int((finished - started).total_seconds() * 1000))


def _is_pass_status(status: str) -> bool:
    """通过：精确比对通过，或拒答用例判定正确。"""
    return status in ("PASSED", "REFUSED_OK")


def _category_of(c: Any) -> str:
    raw = (getattr(c, "category", None) or "").strip()
    return raw or "未知"


def _pass_rate(passed: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(100.0 * passed / total, 1)


def _table_select_of(c: Any) -> dict[str, Any] | None:
    detail = getattr(c, "compare_detail_json", None)
    if not isinstance(detail, dict):
        return None
    ts = detail.get("tableSelect")
    return ts if isinstance(ts, dict) else None


def aggregate_metrics(cases: Iterable[Any]) -> dict[str, Any]:
    """汇总任务指标（详设 §6）。cases 为 EvalTaskCase 或同类属性对象。"""
    total = 0
    ask_failed = 0
    has_result = 0
    exact_pass = 0
    partial_ge_80 = 0
    hitl_supplement_pass = 0
    refuse_ok = 0
    refuse_bad = 0
    board_pass = 0
    table_select_scored = 0
    table_select_ok = 0
    elapsed_sum = 0
    elapsed_n = 0
    passed = 0
    by_cat: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "passed": 0,
            "exactPass": 0,
            "refuseOk": 0,
            "askFailed": 0,
            "tableSelectScored": 0,
            "tableSelectOk": 0,
        }
    )

    for c in cases:
        total += 1
        status = (getattr(c, "status", None) or "").upper()
        subtype = (getattr(c, "govern_subtype", None) or "").upper() or None
        score = getattr(c, "compare_score", None)
        ask_rows = getattr(c, "ask_row_count", None)
        cat = _category_of(c)
        bucket = by_cat[cat]
        bucket["total"] += 1
        ems = _case_elapsed_ms(c)
        if ems is not None:
            elapsed_sum += ems
            elapsed_n += 1

        ts = _table_select_of(c)
        if isinstance(ts, dict) and ts.get("scored") is True:
            table_select_scored += 1
            bucket["tableSelectScored"] += 1
            if ts.get("ok") is True:
                table_select_ok += 1
                bucket["tableSelectOk"] += 1

        if _is_pass_status(status):
            passed += 1
            bucket["passed"] += 1
        if status == "PASSED":
            bucket["exactPass"] += 1
        if status == "REFUSED_OK":
            bucket["refuseOk"] += 1
        if status in ("ASK_FAILED", "MISSING_REQUIRED"):
            bucket["askFailed"] += 1

        if status == "MISSING_REQUIRED":
            ask_failed += 1  # 缺必须列视为硬失败口径
            continue
        if status == "ASK_FAILED":
            ask_failed += 1
            continue
        if status == "REFUSED_OK":
            refuse_ok += 1
            continue
        if status == "REFUSED_BAD":
            refuse_bad += 1
            continue
        if ask_rows is not None and ask_rows > 0:
            has_result += 1
        if status == "PASSED":
            exact_pass += 1
            if subtype == "HITL_SUPPLEMENT":
                hitl_supplement_pass += 1
            if subtype == "BOARD" or subtype is None:
                # 非治理类也计入 boardPass 口径中的「看板/无 HITL 通过」时：
                # 详设 boardPass 主要指治理 BOARD；此处仅 BOARD 计入
                if subtype == "BOARD":
                    board_pass += 1
            continue
        if status == "PARTIAL_GE_80" or (score is not None and float(score) >= 0.8 and status != "PASSED"):
            partial_ge_80 += 1

    by_category = []
    for name in sorted(by_cat.keys()):
        b = by_cat[name]
        by_category.append(
            {
                "category": name,
                "total": b["total"],
                "passed": b["passed"],
                "exactPass": b["exactPass"],
                "refuseOk": b["refuseOk"],
                "askFailed": b["askFailed"],
                "passRate": _pass_rate(b["passed"], b["total"]),
                "tableSelectOk": b["tableSelectOk"],
                "tableSelectScored": b["tableSelectScored"],
                "tableSelectRate": _pass_rate(b["tableSelectOk"], b["tableSelectScored"]),
            }
        )

    return {
        "total": total,
        "passed": passed,
        "passRate": _pass_rate(passed, total),
        "askFailed": ask_failed,
        "hasResult": has_result,
        "exactPass": exact_pass,
        "partialGe80": partial_ge_80,
        "hitlSupplementPass": hitl_supplement_pass,
        "refuseOk": refuse_ok,
        "refuseBadLeak": refuse_bad,
        "boardPass": board_pass,
        "tableSelectOk": table_select_ok,
        "tableSelectScored": table_select_scored,
        "tableSelectRate": _pass_rate(table_select_ok, table_select_scored),
        "elapsedMsSum": elapsed_sum,
        "elapsedMsAvg": int(elapsed_sum / elapsed_n) if elapsed_n else 0,
        "elapsedCaseCount": elapsed_n,
        "byCategory": by_category,
    }
