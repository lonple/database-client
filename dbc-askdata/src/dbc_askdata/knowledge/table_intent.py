from __future__ import annotations

import json
import logging
import re
from typing import Any

from dbc_askdata.llm.client import LlmClient

log = logging.getLogger(__name__)

_MAX_PAIRS = 12

ROLE_TABLE = "table"
ROLE_ATTR = "attr"
ROLE_FILTER = "filter"
_ROLE_TABLE = ROLE_TABLE
_ROLE_ATTR = ROLE_ATTR
_ROLE_FILTER = ROLE_FILTER

# 兼容旧测试/导入；运行时优先用 provider profile
TABLE_INTENT_SYSTEM = """你是问数选表助手。根据用户的中文问题，抽取找表与理解问句所需的业务实体。
要求：
- 每个实体是：entity（中文业务表意）、english（英文单词/词根，猜不准为 ""）、role（table|attr|filter）
- table、attr、filter 都允许多条。不要编造英文物理表名
- role=table：被查询、统计、筛选或连接的数据对象、记录类型或集合。同一个名词短语保持整段，禁止拆碎
- role=attr：某条 table 上的属性、字段、列、维度、指标或特征
- role=filter：仅当限定值是纯数字、纯字母，或数字与字母的组合（可含 -、_）时，才标为参数/码值；english 通常为 ""。含中文的限定值认定为字段，role=attr
- 只输出 JSON：{"entities":[{"entity":"...","english":"...","role":"table|attr|filter"}, ...]}
- 无法判断时 entities 可为 []；禁止其它文字或 Markdown"""


def normalize_entity_role(raw: str | None) -> str:
    """未知/空 role 默认 table，保持旧抽取结果仍可参与选表。"""
    r = (raw or "").strip().lower()
    if r in ("table", "anchor", "object", "entity"):
        return _ROLE_TABLE
    if r in ("attr", "attribute", "field", "metric", "column"):
        return _ROLE_ATTR
    if r in ("filter", "value", "literal", "predicate"):
        return _ROLE_FILTER
    return _ROLE_TABLE


def _table_intent_system(llm: LlmClient | None = None) -> str:
    if llm is not None:
        return llm.get_prompt("table_intent_system", fallback=TABLE_INTENT_SYSTEM)
    try:
        from dbc_askdata.llm.registry import get_provider_profile

        return get_provider_profile().get_prompt(
            "table_intent_system", fallback=TABLE_INTENT_SYSTEM
        )
    except Exception:
        return TABLE_INTENT_SYSTEM


def _parse_json_obj(raw: str | None) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.I)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except Exception:
            return None
    return data if isinstance(data, dict) else None


def parse_table_intent_pairs(raw: str | None) -> list[dict[str, str]]:
    """解析多对 {entity, english, role}；兼容单对象与旧版 tables[]/englishHints[]。"""
    data = _parse_json_obj(raw)
    if not data:
        return []

    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(zh: str, en: str, role: str | None = None) -> None:
        z = (zh or "").strip()
        e = (en or "").strip()
        if not z and not e:
            return
        r = normalize_entity_role(role)
        key = f"{z.lower()}|{e.lower()}|{r}"
        if key in seen:
            return
        seen.add(key)
        out.append({"entity": z, "english": e, "role": r})

    ents = data.get("entities")
    if isinstance(ents, list):
        for item in ents:
            if isinstance(item, dict):
                _add(
                    str(item.get("entity") or item.get("entityZh") or item.get("zh") or ""),
                    str(
                        item.get("english")
                        or item.get("entityEn")
                        or item.get("en")
                        or item.get("englishHint")
                        or ""
                    ),
                    str(item.get("role") or item.get("kind") or item.get("type") or ""),
                )
            elif isinstance(item, str) and item.strip():
                _add(item.strip(), "")
            if len(out) >= _MAX_PAIRS:
                break

    # 兼容旧单对象 {"entity","english"}
    if not out and (data.get("entity") is not None or data.get("english") is not None):
        _add(
            str(data.get("entity") or ""),
            str(data.get("english") or ""),
            str(data.get("role") or ""),
        )

    # 兼容更旧的并行数组
    if not out:
        tables = data.get("tables")
        hints = data.get("englishHints") or data.get("english_hints") or []
        if isinstance(tables, list):
            for i, t in enumerate(tables):
                zh = str(t or "").strip()
                en = ""
                if isinstance(hints, list) and i < len(hints):
                    en = str(hints[i] or "").strip()
                _add(zh, en, _ROLE_TABLE)
                if len(out) >= _MAX_PAIRS:
                    break

    return out[:_MAX_PAIRS]


def parse_table_intent_pair(raw: str | None) -> tuple[str, str]:
    """兼容：取第一对。"""
    pairs = parse_table_intent_pairs(raw)
    if not pairs:
        return "", ""
    return pairs[0].get("entity") or "", pairs[0].get("english") or ""


def parse_table_intent_payload(raw: str | None) -> tuple[list[str], list[str]]:
    """兼容旧测试：拆成并行数组（按对对齐）。"""
    pairs = parse_table_intent_pairs(raw)
    return [p["entity"] for p in pairs if p.get("entity")], [
        p["english"] for p in pairs if p.get("english")
    ]


def parse_table_intents(raw: str | None) -> list[str]:
    """兼容旧测试：只返回中文 entity 列表。"""
    return [p["entity"] for p in parse_table_intent_pairs(raw) if p.get("entity")]


async def resolve_table_intent_query(
    llm: LlmClient,
    *,
    question: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    抽取多对中文实体 + 英文业务词，供问数分字段找表。
    失败时降级：entities 空，仍带原句。
    调用方可用返回的 latency_ms / token_* 记 LLM span（勿写入 graph state）。
    """
    q = (question or "").strip()
    fallback = {
        "entities": [],
        "entity": "",
        "english": "",
        "tables": [],
        "englishHints": [],
        "query": q,
        "source": "question",
    }
    if not q:
        return fallback
    try:
        system_prompt = _table_intent_system(llm)
        resp = await llm.chat_text(
            system=system_prompt,
            user=json.dumps({"question": q}, ensure_ascii=False),
            temperature=0.1,
            model=model,
            tier="light" if not model else None,
        )
        content = ((resp.get("message") or {}).get("content") or "").strip()
        pairs = parse_table_intent_pairs(content)
        table_zh = [
            p["entity"]
            for p in pairs
            if p.get("entity") and normalize_entity_role(p.get("role")) == _ROLE_TABLE
        ]
        zh_list = [p["entity"] for p in pairs if p.get("entity")]
        en_list = [p["english"] for p in pairs if p.get("english")]
        first = next(
            (p for p in pairs if normalize_entity_role(p.get("role")) == _ROLE_TABLE),
            pairs[0] if pairs else {"entity": "", "english": "", "role": _ROLE_TABLE},
        )
        prompt_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({"question": q}, ensure_ascii=False)},
        ]
        return {
            "entities": pairs,
            "entity": first.get("entity") or "",
            "english": first.get("english") or "",
            "tables": table_zh or zh_list,
            "englishHints": en_list,
            "query": " ".join(table_zh or zh_list) if (table_zh or zh_list) else q,
            "source": "llm" if pairs else "question",
            "raw": content[:800],
            "model": resp.get("model") or model,
            "latency_ms": resp.get("latency_ms"),
            "token_in": resp.get("token_in"),
            "token_out": resp.get("token_out"),
            "prompt_messages": prompt_messages,
            "response_message": resp.get("message"),
        }
    except Exception:
        log.warning("表意图抽取失败，降级为用户原问句", exc_info=True)
        return fallback
