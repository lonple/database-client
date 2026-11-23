from __future__ import annotations

from typing import Any

# 监控详情展示用：截断避免 JSONB 过大
_MAX_CONTENT_CHARS = 16_000
_MAX_MESSAGES = 80
_MAX_TOOL_ARGS_CHARS = 4_000


def _clip_text(value: Any, limit: int = _MAX_CONTENT_CHARS) -> str:
    text = value if isinstance(value, str) else ("" if value is None else str(value))
    if len(text) <= limit:
        return text
    return text[:limit] + f"…(truncated,{len(text)} chars)"


def _sanitize_message(msg: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(msg, dict):
        return None
    out: dict[str, Any] = {}
    role = msg.get("role")
    if role is not None:
        out["role"] = role
    if "content" in msg:
        out["content"] = _clip_text(msg.get("content"))
    if "name" in msg and msg.get("name"):
        out["name"] = str(msg.get("name"))
    if "tool_call_id" in msg and msg.get("tool_call_id"):
        out["tool_call_id"] = str(msg.get("tool_call_id"))
    tool_calls = msg.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        slim_calls: list[dict[str, Any]] = []
        for tc in tool_calls[:20]:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
            slim_calls.append(
                {
                    "id": tc.get("id"),
                    "type": tc.get("type") or "function",
                    "function": {
                        "name": (fn or {}).get("name"),
                        "arguments": _clip_text((fn or {}).get("arguments"), _MAX_TOOL_ARGS_CHARS),
                    },
                }
            )
        out["tool_calls"] = slim_calls
    return out


def sanitize_messages(messages: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not messages:
        return []
    out: list[dict[str, Any]] = []
    for m in messages[:_MAX_MESSAGES]:
        if not isinstance(m, dict):
            continue
        sm = _sanitize_message(m)
        if sm:
            out.append(sm)
    if len(messages) > _MAX_MESSAGES:
        out.append(
            {
                "role": "system",
                "content": f"…(truncated {len(messages) - _MAX_MESSAGES} earlier messages)",
            }
        )
    return out


def build_llm_rounds_meta(
    *,
    messages: list[dict[str, Any]] | None,
    response: dict[str, Any] | None,
    step: int | None = None,
    role: str | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    """写入 LLM span.payload_meta：单轮 prompt + response，并带上提示词版本。"""
    from dbc_askdata.llm.prompt_version import current_prompt_version

    version = (prompt_version if prompt_version is not None else current_prompt_version()) or ""
    round_item: dict[str, Any] = {
        "step": 0 if step is None else int(step),
        "promptVersion": version,
        "prompt": sanitize_messages(messages),
        "response": _sanitize_message(response),
    }
    if role:
        round_item["role"] = role
    return {"promptVersion": version, "llmRounds": [round_item]}


def extract_llm_rounds(payload_meta: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload_meta, dict):
        return []
    rounds = payload_meta.get("llmRounds")
    if isinstance(rounds, list):
        return [r for r in rounds if isinstance(r, dict)]
    # 兼容旧字段
    prompt = payload_meta.get("prompt")
    response = payload_meta.get("response")
    if prompt is not None or response is not None:
        return [
            {
                "step": 0,
                "prompt": prompt if isinstance(prompt, list) else sanitize_messages(
                    [{"role": "user", "content": str(prompt)}]
                )
                if prompt is not None
                else [],
                "response": response
                if isinstance(response, dict)
                else {"role": "assistant", "content": _clip_text(response)}
                if response is not None
                else None,
                "role": payload_meta.get("role"),
            }
        ]
    return []
