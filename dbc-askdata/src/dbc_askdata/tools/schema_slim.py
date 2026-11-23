"""LLM 可见的 Tool JSON Schema 瘦身（校验仍用完整 Pydantic 模型）。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# 作用域由服务端注入，不对模型暴露（含 alias 名）
SCOPE_PARAM_KEYS = frozenset(
    {
        "workspace_id",
        "connection_id",
        "database",
        "schema",
        "schema_name",
    }
)

_SKIP_KEYS = frozenset(
    {
        "title",
        "additionalProperties",
        "$defs",
        "definitions",
        "$schema",
        "$id",
    }
)


def slim_json_schema(node: Any, *, hide_scope: bool = True) -> Any:
    """删除 Pydantic 噪声、展平 anyOf[T,null]；可选去掉作用域字段。"""
    if isinstance(node, list):
        return [slim_json_schema(x, hide_scope=hide_scope) for x in node]
    if not isinstance(node, dict):
        return node

    data = node
    if "anyOf" in data and isinstance(data["anyOf"], list):
        variants = data["anyOf"]
        non_null = [
            x
            for x in variants
            if not (isinstance(x, dict) and x.get("type") == "null")
        ]
        has_null = any(isinstance(x, dict) and x.get("type") == "null" for x in variants)
        if len(non_null) == 1 and has_null:
            merged = dict(slim_json_schema(non_null[0], hide_scope=hide_scope))
            for k, v in data.items():
                if k != "anyOf" and k not in merged:
                    merged[k] = v
            data = merged

    out: dict[str, Any] = {}
    for k, v in data.items():
        if k in _SKIP_KEYS:
            continue
        if k == "description" and isinstance(v, str) and len(v) > 80:
            v = v[:80].rstrip() + "…"
        out[k] = slim_json_schema(v, hide_scope=hide_scope)

    props = out.get("properties")
    if hide_scope and isinstance(props, dict):
        props2 = {pk: pv for pk, pv in props.items() if pk not in SCOPE_PARAM_KEYS}
        out["properties"] = props2
        req = out.get("required")
        if isinstance(req, list):
            out["required"] = [r for r in req if r in props2]
    return out


def slim_tool_description(text: str, *, max_chars: int = 96) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def build_scope_args(
    *,
    workspace_id: int | None = None,
    connection_id: int | None = None,
    database: str | None = None,
    schema: str | None = None,
) -> dict[str, Any]:
    """构造可注入的作用域参数（仅非 None；schema 允许显式空则不传）。"""
    out: dict[str, Any] = {}
    if workspace_id is not None:
        out["workspace_id"] = workspace_id
    if connection_id is not None:
        out["connection_id"] = connection_id
    if database is not None:
        out["database"] = database
    if schema is not None:
        out["schema"] = schema
    return out


def merge_tool_args(
    args: dict[str, Any] | None,
    *,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """合并模型参数与服务端作用域。

    - workspace_id / connection_id：始终以服务端为准（防越权）
    - database / schema：仅当模型未传时补齐（允许 FQN 指定 schema）
    """
    merged = dict(args or {})
    if "schema_name" in merged and not merged.get("schema"):
        merged["schema"] = merged.pop("schema_name")
    else:
        merged.pop("schema_name", None)
    if not scope:
        return merged
    for key in ("workspace_id", "connection_id"):
        if key in scope:
            merged[key] = scope[key]
    for key in ("database", "schema"):
        if key in scope and (key not in merged or merged.get(key) in (None, "")):
            merged[key] = scope[key]
    return merged


def openai_tool_from_decl(
    *,
    name: str,
    description: str,
    parameters_schema: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": slim_tool_description(description),
            "parameters": slim_json_schema(deepcopy(parameters_schema), hide_scope=True),
        },
    }
