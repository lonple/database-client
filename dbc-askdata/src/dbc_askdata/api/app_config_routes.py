from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import ApiResponse
from dbc_askdata.app_config import runtime_override
from dbc_askdata.app_config.service import load_askdata_config, save_askdata_config
from dbc_askdata.concurrency.chat_gate import refresh_chat_semaphore
from dbc_askdata.db.session import get_session
from dbc_askdata.llm.registry import reload_provider_profile
from dbc_askdata.security.auth import LoginUser, require_super_admin

router = APIRouter(prefix="/api/admin/app-config")


class AskdataConfigUpdate(BaseModel):
    daily_token_limit: int | None = Field(default=None, alias="dailyTokenLimit", ge=0)
    llm_provider: str | None = Field(default=None, alias="llmProvider")
    concurrent_chat_limit: int | None = Field(
        default=None, alias="concurrentChatLimit", ge=1, le=500
    )
    eval_task_concurrency: int | None = Field(
        default=None,
        alias="evalTaskConcurrency",
        ge=1,
        le=200,
        description="单个测评任务内同时跑的用例数",
    )

    model_config = {"populate_by_name": True}


@router.get("/askdata")
async def get_askdata_app_config(
    _: LoginUser = Depends(require_super_admin),
    session: AsyncSession = Depends(get_session),
):
    cfg = await load_askdata_config(session, use_cache=False)
    return ApiResponse.ok(cfg.to_public_dict())


@router.put("/askdata")
async def put_askdata_app_config(
    body: AskdataConfigUpdate,
    user: LoginUser = Depends(require_super_admin),
    session: AsyncSession = Depends(get_session),
):
    cfg = await save_askdata_config(
        session,
        patch=body.model_dump(by_alias=True, exclude_none=True),
        updated_by=user.user_id,
    )
    refresh_chat_semaphore(cfg.concurrent_chat_limit)
    runtime_override.set_llm_provider(cfg.llm_provider)
    reload_provider_profile()
    return ApiResponse.ok(cfg.to_public_dict())
