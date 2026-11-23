"""条件值与字典说明、列画像格式的匹配。类型是否同一类由模型判断，这里不比较数据库类型。"""

from __future__ import annotations

import json
import math
import re
from typing import Any

_CJK = re.compile(r"[\u4e00-\u9fff]")
# 仅接受模型已拆好的 planning=规划中;active=进行中，不解析中文说明全文
_NORM_PAIR = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_\-]*)=(.+)$")


def normalize_dictionary_pairs(raw: Any) -> list[tuple[str, str]]:
    """接收模型已拆好的码表，不做字段说明全文解析。

    支持：
    - [{key,value}, ...]
    - JSON 字符串同结构
    - 规范化串：planning=规划中;active=进行中
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                loaded = json.loads(text)
            except Exception:
                return []
            return normalize_dictionary_pairs(loaded)
        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()
        for part in re.split(r"[;；|\n]+", text):
            part = part.strip()
            if not part:
                continue
            matched = _NORM_PAIR.match(part)
            if not matched:
                continue
            key, value = matched.group(1).strip(), matched.group(2).strip()
            if not key or not value:
                continue
            marker = key.casefold()
            if marker in seen:
                continue
            seen.add(marker)
            pairs.append((key, value))
        return pairs
    if isinstance(raw, list):
        pairs = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("k") or "").strip()
            value = str(item.get("value") or item.get("v") or "").strip()
            if not key or not value:
                continue
            marker = key.casefold()
            if marker in seen:
                continue
            seen.add(marker)
            pairs.append((key, value))
        return pairs
    return []


# 兼容旧测试名
def parse_kv_pairs(comment: str | None) -> list[tuple[str, str]]:
    return normalize_dictionary_pairs(comment)


def _norm(text: str) -> str:
    raw = (text or "").strip().casefold()
    return re.sub(r"[\s_\-]+", "", raw)


def match_dictionary(literal: str, pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """规范化后相等且唯一才直接用 key。不相等时交给余弦相似度。"""
    nlit = _norm(literal)
    if not nlit or not pairs:
        return {
            "action": "hitl",
            "dictionary": True,
            "reason": "字典字段缺少条件值或没有可解析的 value",
        }
    exact = [key for key, value in pairs if _norm(value) == nlit]
    if len(exact) == 1:
        return {"action": "use_key", "dictionary": True, "key": exact[0], "similarity": 1.0}
    if len(exact) > 1:
        return {"action": "hitl", "dictionary": True, "reason": "多个字典 value 与条件值相同"}
    return {
        "action": "need_similarity",
        "dictionary": True,
        "values": [value for _, value in pairs],
    }


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = 0.0
    norm_l = 0.0
    norm_r = 0.0
    for a, b in zip(left, right, strict=True):
        dot += a * b
        norm_l += a * a
        norm_r += b * b
    if norm_l <= 0.0 or norm_r <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_l) * math.sqrt(norm_r))


def match_dictionary_cosine(
    pairs: list[tuple[str, str]],
    literal_vec: list[float],
    value_vecs: list[list[float]],
    *,
    threshold: float,
) -> dict[str, Any]:
    """取超过阈值的最高余弦。并列超过阈值则 HITL。"""
    if len(value_vecs) != len(pairs):
        return {
            "action": "hitl",
            "dictionary": True,
            "reason": "字典 value 向量数量与码表不一致",
            "values": [value for _, value in pairs],
        }
    scored: list[tuple[float, str, str]] = []
    for (key, value), vec in zip(pairs, value_vecs, strict=True):
        scored.append((cosine(literal_vec, vec), key, value))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] < threshold:
        return {
            "action": "hitl",
            "dictionary": True,
            "reason": f"字典 value 余弦相似度未达到 {threshold}",
            "values": [value for _, value in pairs],
            "similarity": scored[0][0] if scored else 0.0,
        }
    if len(scored) > 1 and scored[1][0] >= threshold and scored[0][0] - scored[1][0] < 0.02:
        return {
            "action": "hitl",
            "dictionary": True,
            "reason": "多个字典 value 的余弦相似度都超过阈值",
            "values": [value for _, value in pairs],
        }
    return {
        "action": "use_key",
        "dictionary": True,
        "key": scored[0][1],
        "similarity": round(scored[0][0], 4),
    }


def value_format(text: str | None) -> str:
    """中文为一类；字母、数字、特殊字符组成的编码为另一类。"""
    raw = "" if text is None else str(text)
    if _CJK.search(raw):
        return "zh"
    return "code"


def column_format(values: list[Any]) -> str:
    """Top 样本的主导格式。没有样本时为 unknown，调用方视为可直接使用条件值。"""
    labels = [value_format(v) for v in values if v is not None and str(v).strip() != ""]
    if not labels:
        return "unknown"
    zh = sum(1 for item in labels if item == "zh")
    if zh * 2 >= len(labels):
        return "zh"
    return "code"


def format_decision(literal: str, samples: list[Any]) -> dict[str, Any]:
    kind = column_format(samples)
    lit = value_format(literal)
    if kind == "unknown" or kind == lit:
        return {
            "action": "use_literal",
            "dictionary": False,
            "columnFormat": kind,
            "conditionFormat": lit,
            "message": "格式同一类，WHERE 直接使用条件值，不必出现在 value_counts 中",
        }
    return {
        "action": "format_mismatch",
        "dictionary": False,
        "columnFormat": kind,
        "conditionFormat": lit,
    }


def fk_targets(table: str, column: str, relations: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """该列在 edges 上的对端表和列。多条都返回，不取第一条。"""
    table_l = (table or "").rsplit(".", 1)[-1].casefold()
    col_l = (column or "").casefold()
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for rel in relations or []:
        if not isinstance(rel, dict):
            continue
        edges = rel.get("edges") or []
        if not isinstance(edges, list):
            continue
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            from_table = str(edge.get("fromTable") or "").rsplit(".", 1)[-1]
            to_table = str(edge.get("toTable") or "").rsplit(".", 1)[-1]
            from_col = str(edge.get("fromColumn") or "")
            to_col = str(edge.get("toColumn") or "")
            target: dict[str, str] | None = None
            if from_table.casefold() == table_l and from_col.casefold() == col_l:
                target = {"table": to_table, "column": to_col}
            elif to_table.casefold() == table_l and to_col.casefold() == col_l:
                target = {"table": from_table, "column": from_col}
            if target is None or not target["table"]:
                continue
            marker = f"{target['table'].casefold()}.{target['column'].casefold()}"
            if marker in seen:
                continue
            seen.add(marker)
            out.append(target)
    return out


def mismatch_action(
    *,
    hop: int,
    targets: list[dict[str, str]],
    column_format_name: str,
    condition_format_name: str,
) -> dict[str, Any]:
    """格式不一致：有外键则跟到对端；没有则同表重选。超过 3 跳 HITL。"""
    base = {
        "dictionary": False,
        "columnFormat": column_format_name,
        "conditionFormat": condition_format_name,
        "hop": hop,
    }
    if hop >= 3:
        return {
            **base,
            "action": "hitl",
            "reason": "同一条件已沿外键重选 3 次，仍没有格式匹配的字段",
        }
    if targets:
        return {
            **base,
            "action": "follow_fk",
            "targets": targets,
            "nextHop": hop + 1,
            "message": "格式不一致。到 targets 中的对端表重选条件字段，下次 hop 传 nextHop。不要锁定第一列。",
        }
    return {
        **base,
        "action": "retry_same_table",
        "message": "该字段不是外键。只在同表其他列重选；没有其他列则 HITL，不要自由游走图谱。",
    }


def accept_sql_literal(literal: str, profile: dict[str, Any] | None) -> dict[str, Any]:
    """校验侧：SQL 字面量是否符合 get_column_profile 的判定逻辑。

    返回 {ok, action, message}。ok=True 放行；False 应回灌大模型改 SQL（不在此强制 HITL）。
    - use_literal：格式同类，字面量可直接用
    - use_key：仅当 SQL 字面量已是字典 key 时放行，否则要求改成 key
    - follow_fk / retry_same_table / hitl / format_mismatch / need_condition：不放行
    - 无 action：用 value_counts 样本做 format_decision
    """
    lit = (literal or "").strip()
    if not lit:
        return {
            "ok": False,
            "action": "missing_literal",
            "message": "WHERE 条件缺少可校验的字面量",
        }
    if not isinstance(profile, dict):
        return {
            "ok": False,
            "action": "need_profile",
            "message": "缺少列画像，无法校验条件值",
        }

    action = str(profile.get("action") or "").strip()
    if not action:
        samples = [
            row.get("value")
            for row in (profile.get("value_counts") or [])
            if isinstance(row, dict)
        ][:30]
        decision = format_decision(lit, samples)
        action = str(decision.get("action") or "")
        if action == "use_literal":
            return {"ok": True, "action": action, "message": decision.get("message") or ""}
        return {
            "ok": False,
            "action": action or "format_mismatch",
            "message": (
                f"条件值 {lit!r} 与列样本格式不一致"
                f"（列={decision.get('columnFormat')}，条件={decision.get('conditionFormat')}）；"
                "请换列、跟外键或改用库内真实码值。"
            ),
            "decision": decision,
        }

    if action == "use_literal":
        return {"ok": True, "action": action, "message": profile.get("message") or ""}

    if action == "use_key":
        key = str(profile.get("key") or "").strip()
        if key and _norm(lit) == _norm(key):
            return {"ok": True, "action": action, "message": "", "key": key}
        if key:
            # 校验侧可代码改写为 key，不必回灌大模型
            return {
                "ok": False,
                "action": action,
                "rewritable": True,
                "key": key,
                "message": (
                    f"字典列条件将由校验自动改写：{lit!r} → key={key!r}"
                ),
            }
        return {
            "ok": False,
            "action": action,
            "message": (
                f"字典列判定为 use_key，但未返回 key；当前 SQL 字面量为 {lit!r}。"
            ),
            "key": key,
        }

    reason = str(profile.get("message") or profile.get("reason") or "").strip()
    if action == "follow_fk":
        targets = profile.get("targets") or []
        return {
            "ok": False,
            "action": action,
            "message": reason
            or (
                f"条件值 {lit!r} 与当前列格式不一致，应跟外键到对端重选条件列"
                f"（targets={targets}）。"
            ),
            "targets": targets,
        }
    if action == "retry_same_table":
        return {
            "ok": False,
            "action": action,
            "message": reason
            or f"条件值 {lit!r} 与当前列格式不一致，请在同表其他列重选条件字段。",
        }
    if action in ("hitl", "format_mismatch", "need_condition", "need_similarity"):
        return {
            "ok": False,
            "action": action,
            "message": reason
            or f"条件值 {lit!r} 未通过画像判定（action={action}），请改正 WHERE。",
        }
    return {
        "ok": False,
        "action": action,
        "message": reason or f"未知画像 action={action}，条件值 {lit!r} 不能直接放行。",
    }
