"""Provider Profile：模型档位 + 提示词包 + Adapter 选项。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dbc_askdata.llm.adapters.openai_compatible import OpenAICompatibleAdapter
from dbc_askdata.llm.protocol import PROMPT_KEYS, LlmAdapter, ModelTier

log = logging.getLogger(__name__)

_INCLUDE_RE = re.compile(r"\{\{\s*include:([^}]+)\}\}")


@dataclass
class ProviderProfile:
    id: str
    version: str = "1"
    model_default: str = ""
    model_light: str = ""
    default_base_url: str = ""
    adapter: LlmAdapter = field(default_factory=OpenAICompatibleAdapter)
    prompts: dict[str, str] = field(default_factory=dict)
    # prompt_version -> 该版本的提示词正文。当前包版本同时放在 prompts。
    prompts_by_version: dict[str, dict[str, str]] = field(default_factory=dict)
    prompt_pack_version: str = "1"
    # model 名 -> prompt_version
    prompt_bindings: dict[str, str] = field(default_factory=dict)
    root_dir: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def resolve_model(self, tier: ModelTier = "default") -> str:
        if tier == "light":
            return (self.model_light or self.model_default or "").strip()
        return (self.model_default or "").strip()

    def prompt_version_for(self, model: str | None) -> str:
        """实际调用的模型名对应的提示词版本。未登记则为 unbound，避免把别的包版本记到这次调用上。"""
        key = (model or "").strip()
        if not key:
            return "unbound"
        return self.prompt_bindings.get(key) or "unbound"

    def get_prompt(self, key: str, *, fallback: str = "", model: str | None = None) -> str:
        ver = self.prompt_version_for(model) if (model or "").strip() else self.prompt_pack_version
        if ver == "unbound":
            ver = self.prompt_pack_version
        bucket = self.prompts_by_version.get(ver) or self.prompts
        text = (bucket.get(key) or "").strip()
        return text if text else (fallback or "")


def providers_root() -> Path:
    return Path(__file__).resolve().parent / "providers"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _expand_includes(text: str, *, base_dir: Path, policy_dir: Path) -> str:
    """支持 {{include:relative/path.md}}；相对 profile 目录，或以 policy/ 开头走共享策略。"""

    def _repl(m: re.Match[str]) -> str:
        rel = m.group(1).strip().replace("\\", "/")
        if rel.startswith("policy/"):
            target = policy_dir / rel[len("policy/") :]
        else:
            target = (base_dir / rel).resolve()
            # 防止逃逸出 providers 根
            try:
                target.relative_to(providers_root().resolve())
            except ValueError:
                log.warning("prompt include 越界已忽略 path=%s", rel)
                return m.group(0)
        if not target.is_file():
            log.warning("prompt include 文件不存在 path=%s", target)
            return m.group(0)
        return _expand_includes(_read_text(target), base_dir=base_dir, policy_dir=policy_dir)

    return _INCLUDE_RE.sub(_repl, text)


def _resolve_prompt_value(
    value: Any,
    *,
    profile_dir: Path,
    policy_dir: Path,
) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        # { template: "...", policies: ["sql_core.md", ...] }
        template_rel = str(value.get("template") or value.get("file") or "").strip()
        parts: list[str] = []
        if template_rel:
            parts.append(
                _resolve_prompt_value(template_rel, profile_dir=profile_dir, policy_dir=policy_dir)
            )
        for pol in value.get("policies") or []:
            pol_name = str(pol or "").strip()
            if not pol_name:
                continue
            pol_path = policy_dir / pol_name
            if pol_path.is_file():
                parts.append(
                    _expand_includes(_read_text(pol_path), base_dir=profile_dir, policy_dir=policy_dir)
                )
            else:
                log.warning("policy 文件不存在 path=%s", pol_path)
        return "\n".join(p for p in parts if p).strip()
    text = str(value).strip()
    if not text:
        return ""
    # 路径式：prompts/foo.md
    if "/" in text or text.endswith((".md", ".txt", ".yaml", ".yml")):
        path = profile_dir / text
        if path.is_file():
            return _expand_includes(_read_text(path), base_dir=profile_dir, policy_dir=policy_dir)
        log.warning("prompt 文件不存在 path=%s", path)
        return ""
    # 内联正文
    return _expand_includes(text, base_dir=profile_dir, policy_dir=policy_dir)


def _build_adapter(provider_id: str, adapter_cfg: dict[str, Any]) -> LlmAdapter:
    kind = str(adapter_cfg.get("kind") or "openai_compatible").strip().lower()
    if kind in ("openai_compatible", "openai", "compatible"):
        pass_thinking = bool(adapter_cfg.get("pass_enable_thinking", False))
        # 兼容旧键 enable_thinking: false 表示「写入且关闭」
        if "pass_enable_thinking" not in adapter_cfg and "enable_thinking" in adapter_cfg:
            pass_thinking = True
        fixed: bool | None = None
        if "enable_thinking" in adapter_cfg:
            fixed = bool(adapter_cfg.get("enable_thinking"))
        return OpenAICompatibleAdapter(
            provider_id=provider_id,
            enable_thinking=fixed,
            default_enable_thinking=bool(adapter_cfg.get("default_enable_thinking", False)),
            pass_enable_thinking=pass_thinking,
        )
    log.warning("未知 adapter.kind=%s，回退 openai_compatible", kind)
    return OpenAICompatibleAdapter(provider_id=provider_id)


def load_profile_from_dir(profile_dir: Path, *, overlay: dict[str, Any] | None = None) -> ProviderProfile:
    """从目录加载 profile.yaml + prompts。"""
    import yaml

    profile_dir = profile_dir.resolve()
    yaml_path = profile_dir / "profile.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"缺少 profile.yaml: {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"profile.yaml 必须是 mapping: {yaml_path}")
    if overlay:
        data = _deep_merge(data, overlay)

    provider_id = str(data.get("id") or profile_dir.name).strip()
    models = data.get("models") if isinstance(data.get("models"), dict) else {}
    adapter_cfg = data.get("adapter") if isinstance(data.get("adapter"), dict) else {}
    prompts_cfg = data.get("prompts") if isinstance(data.get("prompts"), dict) else {}

    policy_dir = Path(__file__).resolve().parent / "prompts" / "_policy"
    pack_version = str(data.get("prompt_pack_version") or "1").strip() or "1"
    bindings = _parse_prompt_bindings(data.get("prompt_bindings"))
    _require_model_bindings(
        bindings,
        default_model=str(models.get("default") or "").strip(),
        light_model=str(models.get("light") or "").strip(),
        profile_path=yaml_path,
    )
    versions = sorted({pack_version, *bindings.values()})
    prompts_by_version = {
        ver: _load_prompt_pack(
            profile_dir,
            prompts_cfg,
            policy_dir=policy_dir,
            version=ver,
        )
        for ver in versions
    }
    prompts = prompts_by_version.get(pack_version) or {}

    return ProviderProfile(
        id=provider_id,
        version=str(data.get("version") or "1"),
        model_default=str(models.get("default") or "").strip(),
        model_light=str(models.get("light") or "").strip(),
        default_base_url=str(data.get("default_base_url") or "").strip(),
        adapter=_build_adapter(provider_id, adapter_cfg),
        prompts=prompts,
        prompts_by_version=prompts_by_version,
        prompt_pack_version=pack_version,
        prompt_bindings=bindings,
        root_dir=profile_dir,
        raw=data,
    )


def _parse_prompt_bindings(raw: Any) -> dict[str, str]:
    if not isinstance(raw, list):
        return {}
    out: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        model = str(item.get("model") or "").strip()
        ver = str(item.get("prompt_version") or item.get("promptVersion") or "").strip()
        if model and ver:
            out[model] = ver
    return out


def _require_model_bindings(
    bindings: dict[str, str],
    *,
    default_model: str,
    light_model: str,
    profile_path: Path,
) -> None:
    missing = [name for name in (default_model, light_model) if name and name not in bindings]
    if missing:
        raise ValueError(
            f"{profile_path} 缺少提示词版本映射: {', '.join(missing)}。"
            "请在 prompt_bindings 中为每个模型指定 prompt_version。"
        )


def _load_prompt_pack(
    profile_dir: Path,
    prompts_cfg: dict[str, Any],
    *,
    policy_dir: Path,
    version: str,
) -> dict[str, str]:
    """version=当前包用 profile 里的路径；其它版本读 prompts/v{version}/。"""
    prompts: dict[str, str] = {}
    for key in PROMPT_KEYS:
        if key in prompts_cfg:
            value = prompts_cfg.get(key)
            if version != "1" and isinstance(value, str):
                value = _versioned_prompt_path(value, version)
            prompts[key] = _resolve_prompt_value(
                value, profile_dir=profile_dir, policy_dir=policy_dir
            )
        else:
            default_file = _prompt_file(profile_dir, key, version)
            if default_file.is_file():
                prompts[key] = _expand_includes(
                    _read_text(default_file), base_dir=profile_dir, policy_dir=policy_dir
                )
        if version != "1" and not (prompts.get(key) or "").strip():
            raise FileNotFoundError(
                f"提示词包 v{version} 缺少 {key}。请在 {profile_dir / 'prompts' / ('v' + version)} 补齐。"
            )
    return prompts


def _versioned_prompt_path(rel: str, version: str) -> str:
    norm = rel.replace("\\", "/").lstrip("/")
    prefix = "prompts/"
    if norm.startswith(prefix):
        return f"prompts/v{version}/{norm[len(prefix):]}"
    return norm


def _prompt_file(profile_dir: Path, key: str, version: str) -> Path:
    if version == "1":
        return profile_dir / "prompts" / f"{key}.md"
    return profile_dir / "prompts" / f"v{version}" / f"{key}.md"


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def load_overlay_yaml(path: Path) -> dict[str, Any]:
    """加载可选覆盖 YAML（兼容旧 agent_bundle 结构）。"""
    import yaml

    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        log.error("加载 LLM overlay 失败 path=%s", path, exc_info=True)
        return {}
