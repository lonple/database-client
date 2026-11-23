from __future__ import annotations

import re
from typing import Any


def build_hitl_ui(
    *,
    kind: str,
    title: str,
    hint: str,
    fields: list[dict[str, Any]] | None = None,
    candidates: list[str] | None = None,
) -> dict[str, Any]:
    """前端 HITL 渲染契约。"""
    return {
        "kind": kind,
        "title": title,
        "hint": hint,
        "fields": fields
        or [
            {
                "key": "text",
                "label": "补充信息",
                "required": True,
                "candidates": candidates or [],
            }
        ],
    }


# 明确「只要一个物理列名」的问法
_COLUMN_MARKERS = (
    "字段名是什么",
    "字段名是",
    "列名是什么",
    "列名是",
    "哪一列",
    "哪个字段名",
    "用哪一列",
    "用哪个字段",
    "请确认字段名",
    "请提供字段名",
    "请填写字段名",
)
_LITERAL_MARKERS = ("码值", "字面量", "真实取值", "真实码值", "枚举值", "库内取值")
_TABLE_MARKERS = (
    "确认查询表",
    "确认表名",
    "选择表",
    "选哪张表",
    "要查哪张表",
    "物理表名",
    "查询哪张表",
    "补充要查询的表",
)


def _is_open_clarification(q: str) -> bool:
    """多问句 / 是否·还是 / CASE 方案等：应自由文本回答，不能收成单字段。"""
    if not q:
        return False
    qmarks = q.count("？") + q.count("?")
    if qmarks >= 2:
        return True
    if re.search(r"[1-9]\s*[\.\)、]", q) and (
        "是否" in q or "还是" in q or "CASE" in q.upper() or "关联" in q
    ):
        return True
    if "是否" in q or "还是需要" in q or "还是要" in q:
        return True
    if "CASE WHEN" in q.upper() or "生成明确" in q:
        return True
    return False


def _is_single_column_ask(q: str) -> bool:
    """仅当整句目标是「给出一个物理列名」时才 COLUMN。"""
    if _is_open_clarification(q):
        return False
    if any(m in q for m in _COLUMN_MARKERS):
        return True
    # 「…的字段名是什么？」且无多问
    if "字段名" in q and ("什么" in q or "哪" in q or "确认" in q):
        return True
    if "列名" in q and ("什么" in q or "哪" in q or "确认" in q):
        return True
    return False


def infer_hitl_kind(state: dict[str, Any]) -> str:
    """由打断节点 + 问句推断 HITL 类型；显式 hitl_kind 优先。

    多问/是否类 → SCOPE（自由回答）；不得误判为 COLUMN/TABLE。
    """
    explicit = str(state.get("hitl_kind") or "").strip().upper()
    if explicit:
        return explicit

    node = str(state.get("interrupted_node") or "")
    q = str(state.get("hitl_question") or "")

    if _is_open_clarification(q):
        return "SCOPE"

    if _is_single_column_ask(q):
        return "COLUMN"

    if node == "verify" or any(m in q for m in _LITERAL_MARKERS):
        return "EQ_LITERAL"

    if any(m in q for m in _TABLE_MARKERS):
        return "TABLE"

    if node in ("fine_router", "after_router", "gather_context"):
        # 找表失败时默认选表；开放澄清已在上面返回 SCOPE
        return "TABLE"

    if node == "review" or "语义" in q or "评审" in q or "口径" in q:
        return "REVIEW"

    if "知识" in q:
        return "KNOWLEDGE_DOWN"

    return "SCOPE"


def _catalog_table_candidates(state: dict[str, Any]) -> list[str]:
    items = ((state.get("catalog") or {}) if isinstance(state.get("catalog"), dict) else {}).get(
        "items"
    ) or []
    return [str(it.get("name")) for it in items if isinstance(it, dict) and it.get("name")]


def _column_candidates(state: dict[str, Any]) -> list[str]:
    """从已描述列或问句中提到的表，给出字段候选。"""
    described = state.get("described_columns")
    if not isinstance(described, dict) or not described:
        return []

    q = str(state.get("hitl_question") or "")
    hinted: list[str] = re.findall(r"`([A-Za-z_][\w]*)`", q)
    hinted += re.findall(r"\b([a-z][a-z0-9_]{2,})\b", q.lower())

    keys = list(described.keys())
    picked_key = None
    for h in hinted:
        hl = h.lower()
        for k in keys:
            kl = str(k).lower()
            if kl == hl or kl.endswith("." + hl) or kl.split(".")[-1] == hl:
                picked_key = k
                break
        if picked_key:
            break
    if picked_key is None and len(keys) == 1:
        picked_key = keys[0]

    cols = described.get(picked_key) if picked_key else None
    if not isinstance(cols, list):
        return []
    out: list[str] = []
    for c in cols:
        name = str(c).strip() if not isinstance(c, dict) else str(c.get("name") or "").strip()
        if name and name not in out:
            out.append(name)
        if len(out) >= 20:
            break
    return out


def hitl_ui_for_state(state: dict[str, Any]) -> dict[str, Any]:
    """根据打断原因推断默认 UI；问句与表单类型必须一致。"""
    kind = infer_hitl_kind(state)
    q = str(state.get("hitl_question") or "请确认后继续")

    if kind == "COLUMN":
        return build_hitl_ui(
            kind="COLUMN",
            title="请确认字段名",
            hint="请填写或选择物理列名（如 leave_date），不要填表名或口语描述。",
            fields=[
                {
                    "key": "column",
                    "label": "字段名",
                    "required": True,
                    "candidates": _column_candidates(state),
                }
            ],
        )

    if kind == "EQ_LITERAL":
        return build_hitl_ui(
            kind="EQ_LITERAL",
            title="请确认过滤码值",
            hint="请填写库内真实码值（与列画像一致），不要填口语缩写。",
            fields=[
                {
                    "key": "text",
                    "label": "真实码值",
                    "required": True,
                    "candidates": [],
                }
            ],
        )

    if kind == "TABLE":
        return build_hitl_ui(
            kind="TABLE",
            title="请确认查询表",
            hint="请填写或选择物理表名（schema.table 或 table）。",
            fields=[
                {
                    "key": "table",
                    "label": "表名",
                    "required": True,
                    "candidates": _catalog_table_candidates(state)[:10],
                }
            ],
        )

    if kind == "REVIEW":
        return build_hitl_ui(
            kind="REVIEW",
            title="请确认查询口径",
            hint="请针对上方问题补充口径；可逐条简要回答。",
            fields=[
                {
                    "key": "text",
                    "label": "您的回答",
                    "required": True,
                    "candidates": [],
                }
            ],
        )

    if kind == "KNOWLEDGE_DOWN":
        return build_hitl_ui(
            kind="KNOWLEDGE_DOWN",
            title="知识检索失败",
            hint="请直接补充要查的表名或指标口径。",
            fields=[
                {"key": "table", "label": "表名（可选）", "required": False, "candidates": []},
                {"key": "text", "label": "补充说明", "required": True, "candidates": []},
            ],
        )

    # SCOPE：开放澄清（含多问）——用自由文本一次答完
    return build_hitl_ui(
        kind="SCOPE",
        title="请确认查询口径",
        hint="请针对上方问题作答（可逐条编号回复）；不要只填一个无关字段名。",
        fields=[
            {
                "key": "text",
                "label": "您的回答",
                "required": True,
                "candidates": [],
            }
        ],
    )
