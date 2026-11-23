from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from dbc_askdata.tools.schema_slim import (
    merge_tool_args,
    openai_tool_from_decl,
)

log = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolDecl:
    name: str
    description: str
    parameters_model: type[BaseModel]
    handler: ToolHandler
    enabled: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDecl] = {}

    def register(self, decl: ToolDecl) -> None:
        if not decl.enabled:
            return
        if decl.name in self._tools:
            raise RuntimeError(f"重复注册 Tool: {decl.name}")
        self._tools[decl.name] = decl

    def get(self, name: str) -> ToolDecl | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def openai_tools(self, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
        """供 LLM function-calling；瘦 schema + 隐藏作用域参数。"""
        skip = exclude or set()
        out: list[dict[str, Any]] = []
        raw_chars = 0
        slim_chars = 0
        for decl in self._tools.values():
            if decl.name in skip:
                continue
            raw_schema = decl.parameters_model.model_json_schema()
            raw_tool = {
                "type": "function",
                "function": {
                    "name": decl.name,
                    "description": decl.description,
                    "parameters": raw_schema,
                },
            }
            raw_chars += len(json.dumps(raw_tool, ensure_ascii=False))
            slim = openai_tool_from_decl(
                name=decl.name,
                description=decl.description,
                parameters_schema=raw_schema,
            )
            slim_chars += len(json.dumps(slim, ensure_ascii=False))
            out.append(slim)
        if out:
            log.debug(
                "openai_tools slim tools=%s raw_chars=%s slim_chars=%s saved=%s",
                len(out),
                raw_chars,
                slim_chars,
                max(0, raw_chars - slim_chars),
            )
        return out


class ToolGateway:
    """模型 tool_call 的唯一出口。"""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def openai_tools(self, *, exclude: set[str] | None = None) -> list[dict[str, Any]]:
        return self._registry.openai_tools(exclude=exclude)

    async def invoke(
        self,
        name: str,
        args: dict[str, Any] | None,
        *,
        scope: dict[str, Any] | None = None,
    ) -> Any:
        decl = self._registry.get(name)
        if decl is None:
            raise ValueError(f"未知或不允许的 Tool: {name}")
        merged = merge_tool_args(args, scope=scope)
        try:
            parsed = decl.parameters_model.model_validate(merged)
        except ValidationError as ex:
            raise ValueError(f"Tool 参数校验失败: {name}: {ex}") from ex
        # 字段名（schema_name / from_table）；handler 内可再兼容 alias
        return await decl.handler(parsed.model_dump())
