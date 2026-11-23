from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from dbc_askdata.graph.time_context import current_time_context

log = logging.getLogger(__name__)

ReviewAction = Literal["pass", "regen", "hitl"]

REVIEW_SYSTEM = """你是企业智能问数的 SQL 语义评审员。机械校验（语法、EXPLAIN、等值投影、画像字面量）已通过。
你只判断：草稿 SQL 是否忠实覆盖用户话术中的实体、口径、粒度和过滤意图。
只输出一个 JSON：
{"ok":true|false,"action":"pass|regen|hitl","critique":"...","hitl_question":"仅 hitl 时填写"}
规则：
- 相对时间（今天/本月/今年等）以上下文 current_time 为准；SQL 日期与 current_time 一致即视为覆盖，勿用训练截止年否决
- pass：话术中的关键实体/过滤/粒度已被 SQL 表达，或话术本身没有可落地的过滤条件
- regen：SQL 漏掉、扭曲或扩大了话术意图，且仅凭已有上下文就能改写（例如丢掉了用户提到的产品/部门/状态，或粒度过粗/过细）
- hitl：上下文不足以确定用户指哪一个实体或哪一种口径，必须问人；禁止猜测
禁止编造目录中没有的表。禁止因为风格、别名、列顺序而否决。禁止输出 JSON 以外的内容。"""


@dataclass(frozen=True)
class ReviewVerdict:
    ok: bool
    action: ReviewAction
    critique: str
    hitl_question: str = ""


def _review_fail_hitl(critique: str, hitl_question: str | None = None) -> ReviewVerdict:
    """评审异常或不确定：一律 HITL，禁止放行可执行草稿。"""
    q = (hitl_question or critique or "语义评审异常，请确认 SQL 是否覆盖您的问题意图。").strip()
    return ReviewVerdict(False, "hitl", critique or q, q)


def parse_review_verdict(text: str) -> ReviewVerdict:
    """解析评审 JSON；空/解析失败/未知 action → HITL（禁止放行）。"""
    raw = (text or "").strip()
    if not raw:
        return _review_fail_hitl("评审输出为空，需人工确认")
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        data = json.loads(raw[start : end + 1] if start >= 0 and end > start else raw)
    except Exception:
        log.warning("SQL 评审 JSON 解析失败", exc_info=True)
        return _review_fail_hitl("评审结果无法解析，需人工确认")
    if not isinstance(data, dict):
        return _review_fail_hitl("评审结果非对象，需人工确认")
    ok = bool(data.get("ok"))
    action_raw = str(data.get("action") or "").strip().lower()
    critique = str(data.get("critique") or "").strip()
    hitl_q = str(data.get("hitl_question") or "").strip()
    if ok:
        return ReviewVerdict(True, "pass", critique or "评审通过")
    if action_raw == "hitl":
        return ReviewVerdict(
            False,
            "hitl",
            critique or "语义不确定，需人工确认",
            hitl_q or critique or "请确认查询对象或过滤口径。",
        )
    if action_raw in ("regen", "rebuild", "retry", ""):
        return ReviewVerdict(
            False,
            "regen",
            critique or "SQL 未覆盖用户话术，需重写草稿",
        )
    return _review_fail_hitl(
        critique or f"未知 action={action_raw}，需人工确认",
        hitl_q or None,
    )


def build_review_user_payload(state: dict[str, Any]) -> dict[str, Any]:
    draft = state.get("draft") or {}
    nodes = []
    for n in draft.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        nodes.append(
            {
                "id": n.get("id"),
                "type": n.get("type"),
                "title": n.get("title"),
                "sql": n.get("sql"),
            }
        )
    payload: dict[str, Any] = {
        "question": state.get("question"),
        "database": state.get("database"),
        "schema": state.get("schema"),
        "route": state.get("route"),
        "draft_name": draft.get("name"),
        "nodes": nodes,
        "current_time": current_time_context(),
    }
    hitl = state.get("hitl_resolution")
    if isinstance(hitl, dict) and hitl:
        payload["hitl_resolution"] = {
            "text": hitl.get("text"),
            "table": hitl.get("table"),
            "ack": hitl.get("ack"),
        }
    kg = state.get("db_general_knowledge")
    if isinstance(kg, dict) and kg.get("body"):
        payload["db_general_knowledge"] = {
            "title": kg.get("title"),
            "summary": kg.get("summary"),
            "body": str(kg.get("body") or "")[:4000],
        }
    catalog = state.get("catalog") if isinstance(state.get("catalog"), dict) else None
    if catalog and isinstance(catalog.get("items"), list):
        payload["catalog_candidates"] = [
            {
                "name": it.get("name"),
                "description": it.get("description"),
            }
            for it in catalog.get("items")[:5]
            if isinstance(it, dict) and it.get("name")
        ]
    described = state.get("described_columns") or {}
    if described:
        payload["described_tables"] = sorted(described.keys())
    return payload
