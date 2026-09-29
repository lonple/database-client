from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError


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

    def openai_tools(self) -> list[dict[str, Any]]:
        """供 LLM function-calling；仅暴露已声明 Tool。"""
        out: list[dict[str, Any]] = []
        for decl in self._tools.values():
            schema = decl.parameters_model.model_json_schema()
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": decl.name,
                        "description": decl.description,
                        "parameters": schema,
                    },
                }
            )
        return out


class ToolGateway:
    """模型 tool_call 的唯一出口。"""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def openai_tools(self) -> list[dict[str, Any]]:
        return self._registry.openai_tools()

    async def invoke(self, name: str, args: dict[str, Any] | None) -> Any:
        decl = self._registry.get(name)
        if decl is None:
            raise ValueError(f"未知或不允许的 Tool: {name}")
        try:
            parsed = decl.parameters_model.model_validate(args or {})
        except ValidationError as ex:
            raise ValueError(f"Tool 参数校验失败: {name}: {ex}") from ex
        return await decl.handler(parsed.model_dump())
