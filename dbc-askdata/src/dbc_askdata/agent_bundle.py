"""兼容门面：AgentBundle 现委托 LLM Provider Profile。

模型档位与提示词真相源为 `dbc_askdata.llm.providers/<provider>/`。
显式 `agent_bundle_path` 仍可作为 overlay（见 llm.registry）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from dbc_askdata.config import Settings

log = logging.getLogger(__name__)


@dataclass
class AgentBundle:
    version: str = "1"
    model_default: str = ""
    model_light: str = ""
    gate_system: str = ""
    fine_router_system: str = ""
    chat_system: str = ""
    build_system: str = ""
    govern_system: str = ""
    review_system: str = ""
    table_intent_system: str = ""
    tool_schema_version: str = "1"
    provider_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def get_prompt(self, key: str, *, fallback: str = "") -> str:
        text = str(getattr(self, key, "") or "").strip()
        return text if text else (fallback or "")


def _default_path() -> Path:
    return Path(__file__).resolve().parent / "agent_bundle.yaml"


def load_agent_bundle(settings: Settings) -> AgentBundle:
    from dbc_askdata.llm.registry import load_provider_profile

    profile = load_provider_profile(settings)
    return AgentBundle(
        version=profile.version,
        model_default=profile.model_default,
        model_light=profile.model_light,
        gate_system=profile.get_prompt("gate_system"),
        fine_router_system=profile.get_prompt("fine_router_system"),
        chat_system=profile.get_prompt("chat_system"),
        build_system=profile.get_prompt("build_system"),
        govern_system=profile.get_prompt("govern_system"),
        review_system=profile.get_prompt("review_system"),
        table_intent_system=profile.get_prompt("table_intent_system"),
        tool_schema_version=str((profile.raw.get("tools") or {}).get("schema_version") or "1")
        if isinstance(profile.raw.get("tools"), dict)
        else "1",
        provider_id=profile.id,
        raw=profile.raw,
    )


@lru_cache
def get_agent_bundle() -> AgentBundle:
    from dbc_askdata.config import get_settings

    return load_agent_bundle(get_settings())


def reload_agent_bundle() -> AgentBundle:
    from dbc_askdata.llm.registry import reload_provider_profile

    reload_provider_profile()
    get_agent_bundle.cache_clear()
    return get_agent_bundle()
