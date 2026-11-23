"""按 llm_provider 加载 Provider Profile（进程级；预留 resolve_provider(ctx)）。"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from dbc_askdata.config import Settings, get_settings
from dbc_askdata.llm.profile import (
    ProviderProfile,
    load_overlay_yaml,
    load_profile_from_dir,
    providers_root,
)

log = logging.getLogger(__name__)

# 已注册的内置厂商目录名
BUILTIN_PROVIDERS = frozenset({"qwen"})


def resolve_provider_id(settings: Settings | None = None, *, ctx: dict[str, Any] | None = None) -> str:
    """进程级解析；管理台覆盖优先于 Settings；ctx 预留租户覆盖（当前忽略）。"""
    _ = ctx
    from dbc_askdata.app_config.runtime_override import get_llm_provider_override

    override = get_llm_provider_override()
    if override:
        return override
    s = settings or get_settings()
    pid = (s.llm_provider or "").strip().lower() or "qwen"
    return pid


def _overlay_from_settings(settings: Settings) -> dict[str, Any]:
    """
    合并外部覆盖：
    1) llm_profile_path 指向 profile 目录或 yaml
    2) 兼容 agent_bundle_path / 包内 agent_bundle.yaml（仅 models+prompts 覆盖）
    """
    overlay: dict[str, Any] = {}
    profile_path_raw = (settings.llm_profile_path or "").strip()
    if profile_path_raw:
        p = Path(profile_path_raw)
        if p.is_dir():
            # 目录模式：整包替换，不在此合并
            return {"__profile_dir__": str(p.resolve())}
        if p.is_file():
            overlay = load_overlay_yaml(p)

    # 兼容旧 agent_bundle：仅当显式配置路径时覆盖（避免默认 qwen bundle 污染其它 provider）
    bundle_raw = (settings.agent_bundle_path or "").strip()
    if bundle_raw:
        overlay = _merge_bundle_overlay(overlay, Path(bundle_raw))
    return overlay


def _merge_bundle_overlay(base: dict[str, Any], path: Path) -> dict[str, Any]:
    data = load_overlay_yaml(path)
    if not data:
        return base
    # agent_bundle 结构：models / prompts
    piece: dict[str, Any] = {}
    if isinstance(data.get("models"), dict):
        models = {k: v for k, v in data["models"].items() if str(v or "").strip()}
        if models:
            piece["models"] = models
    if isinstance(data.get("prompts"), dict):
        prompts = {k: v for k, v in data["prompts"].items() if str(v or "").strip()}
        if prompts:
            piece["prompts"] = prompts
    if data.get("id"):
        piece["id"] = data["id"]
    if data.get("default_base_url"):
        piece["default_base_url"] = data["default_base_url"]
    if isinstance(data.get("adapter"), dict):
        piece["adapter"] = data["adapter"]
    if not piece:
        return base
    from dbc_askdata.llm.profile import _deep_merge

    return _deep_merge(base, piece)


def load_provider_profile(settings: Settings | None = None, *, ctx: dict[str, Any] | None = None) -> ProviderProfile:
    s = settings or get_settings()
    provider_id = resolve_provider_id(s, ctx=ctx)
    overlay = _overlay_from_settings(s)

    if overlay.get("__profile_dir__"):
        profile_dir = Path(str(overlay["__profile_dir__"]))
        log.info("加载外部 LLM profile 目录 path=%s", profile_dir)
        return load_profile_from_dir(profile_dir)

    if provider_id not in BUILTIN_PROVIDERS:
        raise RuntimeError(
            f"未知 llm_provider={provider_id!r}；内置: {sorted(BUILTIN_PROVIDERS)}。"
            "或设置 DBC_ASKDATA_LLM_PROFILE_PATH 指向自定义 profile 目录。"
        )
    profile_dir = providers_root() / provider_id
    if not profile_dir.is_dir():
        raise RuntimeError(f"缺少内置 provider 目录: {profile_dir}")

    # 去掉内部标记后再 merge
    clean_overlay = {k: v for k, v in overlay.items() if k != "__profile_dir__"}
    profile = load_profile_from_dir(profile_dir, overlay=clean_overlay or None)
    log.info(
        "已加载 LLM provider=%s version=%s prompt_pack=%s default=%s light=%s bindings=%s",
        profile.id,
        profile.version,
        profile.prompt_pack_version,
        profile.model_default,
        profile.model_light,
        profile.prompt_bindings,
    )
    return profile


@lru_cache
def get_provider_profile() -> ProviderProfile:
    return load_provider_profile(get_settings())


def reload_provider_profile() -> ProviderProfile:
    get_provider_profile.cache_clear()
    return get_provider_profile()


def resolve_model_name(
    settings: Settings,
    *,
    tier: str = "default",
    explicit: str | None = None,
    profile: ProviderProfile | None = None,
) -> str:
    """explicit > Settings 覆盖 > profile 档位。"""
    if (explicit or "").strip():
        return explicit.strip()
    p = profile or get_provider_profile()
    if tier == "light":
        override = (settings.llm_model_light or "").strip()
        if override:
            return override
        return p.resolve_model("light") or (settings.llm_model or "").strip()
    override = (settings.llm_model or "").strip()
    if override:
        return override
    return p.resolve_model("default")
