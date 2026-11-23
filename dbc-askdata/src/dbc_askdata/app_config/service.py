"""问数应用运行配置：DB 持久化 + 内存缓存。"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.db.models import AskAppConfig

log = logging.getLogger(__name__)

MODULE_ASKDATA = "askdata"
_ALLOWED_PROVIDERS = frozenset({"qwen"})

_cache: AskdataRuntimeConfig | None = None
_cache_gen = 0


@dataclass(frozen=True)
class AskdataRuntimeConfig:
    daily_token_limit: int = 500_000
    llm_provider: str = "qwen"
    concurrent_chat_limit: int = 20
    eval_task_concurrency: int = 20

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "dailyTokenLimit": self.daily_token_limit,
            "llmProvider": self.llm_provider,
            "concurrentChatLimit": self.concurrent_chat_limit,
            "evalTaskConcurrency": self.eval_task_concurrency,
        }


def default_askdata_config() -> AskdataRuntimeConfig:
    return AskdataRuntimeConfig()


def invalidate_askdata_config_cache() -> None:
    global _cache, _cache_gen
    _cache = None
    _cache_gen += 1


def config_generation() -> int:
    return _cache_gen


def _normalize(raw: dict[str, Any] | None) -> AskdataRuntimeConfig:
    d = default_askdata_config()
    if not isinstance(raw, dict):
        return d
    # 兼容 camelCase / snake_case
    token = raw.get("dailyTokenLimit", raw.get("daily_token_limit", d.daily_token_limit))
    provider = str(raw.get("llmProvider", raw.get("llm_provider", d.llm_provider)) or "").strip().lower()
    concurrent = raw.get("concurrentChatLimit", raw.get("concurrent_chat_limit", d.concurrent_chat_limit))
    eval_conc = raw.get(
        "evalTaskConcurrency", raw.get("eval_task_concurrency", d.eval_task_concurrency)
    )
    try:
        token_i = max(0, int(token))
    except (TypeError, ValueError):
        token_i = d.daily_token_limit
    if provider not in _ALLOWED_PROVIDERS:
        provider = d.llm_provider
    try:
        conc_i = max(1, min(500, int(concurrent)))
    except (TypeError, ValueError):
        conc_i = d.concurrent_chat_limit
    try:
        eval_i = max(1, min(200, int(eval_conc)))
    except (TypeError, ValueError):
        eval_i = d.eval_task_concurrency
    return AskdataRuntimeConfig(
        daily_token_limit=token_i,
        llm_provider=provider,
        concurrent_chat_limit=conc_i,
        eval_task_concurrency=eval_i,
    )


async def load_askdata_config(session: AsyncSession, *, use_cache: bool = True) -> AskdataRuntimeConfig:
    global _cache
    if use_cache and _cache is not None:
        return _cache
    row = (
        await session.execute(select(AskAppConfig).where(AskAppConfig.module == MODULE_ASKDATA))
    ).scalar_one_or_none()
    cfg = _normalize(row.config_json if row else None)
    _cache = cfg
    return cfg


async def get_askdata_runtime_config(session: AsyncSession) -> AskdataRuntimeConfig:
    return await load_askdata_config(session, use_cache=True)


async def save_askdata_config(
    session: AsyncSession,
    *,
    patch: dict[str, Any],
    updated_by: int | None,
) -> AskdataRuntimeConfig:
    current = await load_askdata_config(session, use_cache=False)
    merged = {
        **asdict(current),
        **{
            k: v
            for k, v in {
                "daily_token_limit": patch.get("dailyTokenLimit", patch.get("daily_token_limit")),
                "llm_provider": patch.get("llmProvider", patch.get("llm_provider")),
                "concurrent_chat_limit": patch.get(
                    "concurrentChatLimit", patch.get("concurrent_chat_limit")
                ),
                "eval_task_concurrency": patch.get(
                    "evalTaskConcurrency", patch.get("eval_task_concurrency")
                ),
            }.items()
            if v is not None
        },
    }
    cfg = _normalize(merged)
    row = (
        await session.execute(select(AskAppConfig).where(AskAppConfig.module == MODULE_ASKDATA))
    ).scalar_one_or_none()
    payload = {
        "dailyTokenLimit": cfg.daily_token_limit,
        "llmProvider": cfg.llm_provider,
        "concurrentChatLimit": cfg.concurrent_chat_limit,
        "evalTaskConcurrency": cfg.eval_task_concurrency,
    }
    if row is None:
        session.add(
            AskAppConfig(module=MODULE_ASKDATA, config_json=payload, updated_by=updated_by)
        )
    else:
        row.config_json = payload
        row.updated_by = updated_by
    await session.commit()
    invalidate_askdata_config_cache()
    global _cache
    _cache = cfg
    log.info(
        "已保存问数应用配置 provider=%s daily_token=%s concurrent_chat=%s eval_concurrency=%s by=%s",
        cfg.llm_provider,
        cfg.daily_token_limit,
        cfg.concurrent_chat_limit,
        cfg.eval_task_concurrency,
        updated_by,
    )
    return cfg
