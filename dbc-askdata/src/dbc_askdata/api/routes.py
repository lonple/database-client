from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

from dbc_askdata.api.schemas import (
    ApiResponse,
    ChatRequest,
    ConfirmSqlCorrectRequest,
    HitlResolveRequest,
    ProjectCreateRequest,
    ProjectVO,
    RunFeedbackRequest,
    RunStartRequest,
    SessionCreateRequest,
    TreeProjectVO,
    TreeWorkflowVO,
    WorkflowSaveRequest,
)
from dbc_askdata.feedback.service import (
    apply_run_feedback,
    feedback_vo,
    find_assistant_message_by_draft,
    get_feedback,
    mark_message_workflow_saved,
)
from dbc_askdata.checkpoint.store import (
    complete_checkpoint,
    load_checkpoint_for_hitl,
    save_interrupted_checkpoint,
)
from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.context.session_context import (
    KEEP_WINDOW,
    load_chat_recent_turns,
    load_verified_sample_tables,
)
from dbc_askdata.db.models import (
    AskHitl,
    AskLlmSpan,
    AskMessage,
    AskProject,
    AskSession,
    AskWorkflow,
    AskWorkflowDraft,
    AskWorkflowRun,
    AskWorkflowRunResult,
)
from dbc_askdata.graph.hitl_ui import hitl_ui_for_state
from dbc_askdata.idempotency.service import begin_idempotent, finish_idempotent, get_cached_response
from dbc_askdata.db.scope import find_connection, normalize_scope
from dbc_askdata.db.session import get_session
from dbc_askdata.graph.generate import run_generate_graph
from dbc_askdata.llm.client import LlmError
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.observability.trace import get_trace_id
from dbc_askdata.observability.turn import (
    TURN_STATUS_CANCELLED,
    TURN_STATUS_ERROR,
    TURN_STATUS_HITL,
    TURN_STATUS_OK,
    begin_turn,
    clear_turn,
    find_turn_by_hitl,
    finish_turn,
    resume_turn,
)
from dbc_askdata.observability.worklog import append_work_log, clear_work_logs, list_work_logs
from dbc_askdata.quota.context import bind_quota, clear_quota
from dbc_askdata.quota.service import check_quota_or_raise, get_daily_usage, today_shanghai
from dbc_askdata.redis.client import get_redis
from dbc_askdata.security.auth import LoginUser, extract_bearer, require_permission, require_user
from dbc_askdata.tools.gateway import build_tool_registry
from dbc_askdata.tools.registry import ToolGateway
from dbc_askdata.workflow.runner import WorkflowRunner, get_run, list_run_logs, load_project, load_workflow
import dbc_askdata.main as app_main

router = APIRouter(prefix="/api")


def _llm_unavailable(ex: LlmError) -> HTTPException:
    """LLM 不可达时返回 503，栈已在 LlmClient 打过。"""
    detail = str(ex) or "LLM 调用失败"
    if "All connection attempts failed" in detail or "ConnectError" in detail:
        return HTTPException(
            status_code=503,
            detail=(
                "LLM 服务不可达。默认对接通义千问 DashScope（与 ai-dev-assistant 一致），"
                "请检查 DBC_ASKDATA_LLM_BASE_URL/MODEL/API_KEY（或 ADA_LLM_*）；"
                "本地 Ollama 须设 DBC_ASKDATA_LLM_RESIDENCY=local"
            ),
        )
    return HTTPException(status_code=503, detail=f"LLM 调用失败: {detail}")


def _project_vo(p: AskProject) -> dict:
    return ProjectVO(
        id=p.id,
        name=p.name,
        description=p.description,
        workspaceId=p.workspace_id,
        sourceConnectionId=p.source_connection_id,
        sourceDatabase=p.source_database,
        sourceSchema=p.source_schema,
        workConnectionId=p.work_connection_id,
        workDatabase=p.work_database,
        workSchema=p.work_schema,
        ownerUserId=p.owner_user_id,
        createdAt=p.created_at,
    ).model_dump(by_alias=True)


@router.post("/projects")
async def create_project(
    body: ProjectCreateRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
):
    auth = extract_bearer(authorization)
    sqlwork = SqlworkClient(settings, auth)
    conns = await sqlwork.list_connections(body.workspace_id)
    source_conn = find_connection(conns, body.source_connection_id)
    work_conn = find_connection(conns, body.work_connection_id)
    if source_conn is None:
        raise HTTPException(status_code=400, detail="数据来源连接不在当前空间授权范围内")
    if work_conn is None:
        raise HTTPException(status_code=400, detail="工作连接不在当前空间授权范围内")
    try:
        source_db, source_schema = normalize_scope(
            label="数据来源",
            connection_id=body.source_connection_id,
            database=body.source_database,
            schema=body.source_schema,
            db_type=str(source_conn.get("dbType") or ""),
        )
        work_db, work_schema = normalize_scope(
            label="工作连接",
            connection_id=body.work_connection_id,
            database=body.work_database,
            schema=body.work_schema,
            db_type=str(work_conn.get("dbType") or ""),
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex)) from ex

    project = AskProject(
        name=body.name.strip(),
        description=body.description,
        workspace_id=body.workspace_id,
        source_connection_id=body.source_connection_id,
        source_database=source_db,
        source_schema=source_schema,
        work_connection_id=body.work_connection_id,
        work_database=work_db,
        work_schema=work_schema,
        owner_user_id=user.user_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="CREATE",
            resource_type="ask_project",
            resource_id=str(project.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            details={
                "workspaceId": project.workspace_id,
                "sourceConnectionId": project.source_connection_id,
                "workConnectionId": project.work_connection_id,
            },
        )
    return ApiResponse.ok(_project_vo(project))


@router.get("/projects")
async def list_projects(
    workspace_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AskProject)
        .where(
            AskProject.workspace_id == workspace_id,
            AskProject.deleted.is_(False),
            AskProject.hidden.is_(False),
            AskProject.owner_user_id == user.user_id,
        )
        .order_by(AskProject.id.desc())
    )
    items = [_project_vo(p) for p in result.scalars().all()]
    return ApiResponse.ok(items)


@router.get("/tree")
async def project_tree(
    workspace_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    projects = (
        await session.execute(
            select(AskProject)
            .where(
                AskProject.workspace_id == workspace_id,
                AskProject.deleted.is_(False),
                AskProject.hidden.is_(False),
                AskProject.owner_user_id == user.user_id,
            )
            .order_by(AskProject.id.desc())
        )
    ).scalars().all()
    tree: list[dict] = []
    for p in projects:
        wfs = (
            await session.execute(
                select(AskWorkflow)
                .where(AskWorkflow.project_id == p.id, AskWorkflow.deleted.is_(False))
                .order_by(AskWorkflow.id.asc())
            )
        ).scalars().all()
        tree.append(
            TreeProjectVO(
                id=p.id,
                name=p.name,
                description=p.description,
                sourceConnectionId=p.source_connection_id,
                sourceDatabase=p.source_database,
                sourceSchema=p.source_schema,
                workConnectionId=p.work_connection_id,
                workDatabase=p.work_database,
                workSchema=p.work_schema,
                workflows=[TreeWorkflowVO(id=w.id, name=w.name) for w in wfs],
            ).model_dump(by_alias=True)
        )
    return ApiResponse.ok(tree)


@router.post("/sessions")
async def create_session(
    body: SessionCreateRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(AskProject, body.project_id)
    if project is None or project.deleted or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工程不存在")
    s = AskSession(project_id=project.id, title=body.title or "新会话", owner_user_id=user.user_id)
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return ApiResponse.ok({"id": s.id, "projectId": s.project_id, "title": s.title})


@router.post("/sessions/open")
async def open_session(
    body: SessionCreateRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    """打开工程会话：复用该工程下用户最近 ACTIVE 会话并带回历史；无则新建。"""
    project = await session.get(AskProject, body.project_id)
    if project is None or project.deleted or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工程不存在")
    existing = (
        await session.execute(
            select(AskSession)
            .where(
                AskSession.project_id == project.id,
                AskSession.owner_user_id == user.user_id,
                AskSession.status == "ACTIVE",
            )
            .order_by(AskSession.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    created = False
    if existing is None:
        existing = AskSession(
            project_id=project.id,
            title=body.title or f"{project.name} 会话",
            owner_user_id=user.user_id,
        )
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        created = True
    msgs = (
        await session.execute(
            select(AskMessage).where(AskMessage.session_id == existing.id).order_by(AskMessage.id.asc())
        )
    ).scalars().all()
    pending_hitl = (
        await session.execute(
            select(AskHitl)
            .where(AskHitl.session_id == existing.id, AskHitl.status == "PENDING")
            .order_by(AskHitl.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return ApiResponse.ok(
        {
            "id": existing.id,
            "projectId": existing.project_id,
            "title": existing.title,
            "created": created,
            "pendingHitlId": pending_hitl.id if pending_hitl else None,
            "pendingHitlQuestion": pending_hitl.question if pending_hitl else None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "contentType": m.content_type,
                    "payload": m.payload,
                    "createdAt": m.created_at,
                }
                for m in msgs
            ],
        }
    )


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(AskSession, session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    rows = (
        await session.execute(
            select(AskMessage).where(AskMessage.session_id == session_id).order_by(AskMessage.id.asc())
        )
    ).scalars().all()
    return ApiResponse.ok(
        [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "contentType": m.content_type,
                "payload": m.payload,
                "createdAt": m.created_at,
            }
            for m in rows
        ]
    )


@router.delete("/sessions/{session_id}/messages")
async def clear_session_messages(
    session_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    """清空会话消息与待确认 HITL；工作日志一并清理（已确认样本保留）。"""
    s = await session.get(AskSession, session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    msg_result = await session.execute(delete(AskMessage).where(AskMessage.session_id == session_id))
    hitl_result = await session.execute(
        delete(AskHitl).where(AskHitl.session_id == session_id, AskHitl.status == "PENDING")
    )
    await session.commit()
    await clear_work_logs(session_id)
    return ApiResponse.ok(
        {
            "sessionId": session_id,
            "deletedMessages": int(msg_result.rowcount or 0),
            "deletedPendingHitl": int(hitl_result.rowcount or 0),
        }
    )


@router.get("/sessions/{session_id}/work-logs")
async def get_work_logs(
    session_id: int,
    after: int = 0,
    turn_id: int | None = None,
    turnId: int | None = None,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    """按 turn 拉取进度日志。turn_id/turnId 缺省时回落该会话最近一轮。"""
    s = await session.get(AskSession, session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    tid = turn_id if turn_id is not None else turnId
    return ApiResponse.ok(
        await list_work_logs(session_id, turn_id=tid, after=max(0, after))
    )


@router.get("/sessions/{session_id}/llm-spans")
async def list_session_llm_spans(
    session_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    """会话归属者可查看本会话 LLM/图/工具 span（运维诊断用；产品侧执行日志以 work-log 为准）。"""
    s = await session.get(AskSession, session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    rows = (
        await session.execute(
            select(AskLlmSpan)
            .where(AskLlmSpan.session_id == session_id)
            .order_by(AskLlmSpan.id.asc())
            .limit(500)
        )
    ).scalars().all()
    return ApiResponse.ok(
        {
            "sessionId": session_id,
            "items": [
                {
                    "id": r.id,
                    "phase": r.phase,
                    "kind": r.kind,
                    "name": r.name,
                    "status": r.status,
                    "latencyMs": r.latency_ms,
                    "model": r.model,
                    "errorMessage": r.error_message,
                    "startedAt": r.started_at,
                    "finishedAt": r.finished_at,
                }
                for r in rows
            ],
        }
    )


@router.get("/quota/me")
async def my_quota(
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """工作台展示今日额度；测评页勿调用。"""
    limit = int(settings.daily_token_limit or 0)
    used = await get_daily_usage(session, user_id=user.user_id) if limit > 0 else 0
    return ApiResponse.ok(
        {
            "usageDate": str(today_shanghai()),
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used) if limit > 0 else None,
            "enabled": limit > 0,
        }
    )


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    auth = extract_bearer(authorization)
    s = await session.get(AskSession, body.session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    project = await session.get(AskProject, s.project_id)
    if project is None or project.deleted:
        raise HTTPException(status_code=404, detail="工程不存在")

    await check_quota_or_raise(session, settings, user_id=user.user_id, eval_mode=False)

    from dbc_askdata.concurrency.chat_gate import acquire_chat_slot

    idem_key = (idempotency_key or "").strip()
    if idem_key:
        cached = await get_cached_response(session, user_id=user.user_id, key=idem_key, route="chat")
        if cached is not None:
            return ApiResponse.ok(cached)
        await begin_idempotent(
            session,
            user_id=user.user_id,
            key=idem_key,
            route="chat",
            request_payload={"sessionId": body.session_id, "message": body.message},
        )

    session.add(AskMessage(session_id=s.id, role="user", content=body.message))
    await session.commit()

    if app_main.llm_client is None:
        raise HTTPException(status_code=503, detail="LLM 未就绪")

    turn = await begin_turn(
        session,
        root_trace_id=trace_id,
        question=body.message,
        workspace_id=project.workspace_id,
        project_id=project.id,
        session_id=s.id,
        user_id=user.user_id,
    )
    turn_id = int(turn.id)

    # 按 turn 持久化：新一轮单独桶，不清历史 turn 日志
    await append_work_log(s.id, f"收到消息：{body.message[:120]}", turn_id=turn_id)

    recent = await load_chat_recent_turns(session, session_id=s.id, max_turns=KEEP_WINDOW)
    # 近窗不含刚写入的本轮 user（避免与 question 重复）
    if recent and recent[-1].get("role") == "user" and recent[-1].get("content") == body.message:
        recent = recent[:-1]
    verified = await load_verified_sample_tables(
        session,
        session_id=s.id,
        default_schema=project.source_schema,
        keep=KEEP_WINDOW,
    )

    sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
    registry = build_tool_registry(settings, sqlwork)
    gateway = ToolGateway(registry)
    spans = SpanRecorder(settings)
    bind_quota(user_id=user.user_id, eval_mode=False)
    try:
        async with acquire_chat_slot():
            try:
                state = await run_generate_graph(
                    settings=settings,
                    session=session,
                    spans=spans,
                    tool_gateway=gateway,
                    sqlwork=sqlwork,
                    llm=app_main.llm_client,
                    state={
                        "question": body.message,
                        "workspace_id": project.workspace_id,
                        "connection_id": project.source_connection_id,
                        "database": project.source_database or "",
                        "schema": project.source_schema or "",
                        "project_id": project.id,
                        "session_id": s.id,
                        "user_id": user.user_id,
                        "trace_id": trace_id,
                        "turn_id": turn_id,
                        "authorization": auth,
                        "recent_turns": recent,
                        "verified_samples": verified,
                    },
                )
            except LlmError as ex:
                await append_work_log(
                    s.id, f"失败：{ex}", level="ERROR", turn_id=turn_id
                )
                await finish_turn(
                    session,
                    turn_id=turn_id,
                    status=TURN_STATUS_ERROR,
                    error_message=str(ex),
                    close=True,
                )
                raise _llm_unavailable(ex) from ex
            except Exception as ex:
                await finish_turn(
                    session,
                    turn_id=turn_id,
                    status=TURN_STATUS_ERROR,
                    error_message=str(ex),
                    close=True,
                )
                raise
    finally:
        clear_quota()
        clear_turn()

    draft_id = None
    if state.get("draft"):
        draft = AskWorkflowDraft(
            project_id=project.id,
            session_id=s.id,
            name=(state["draft"].get("name") or "草稿")[:128],
            nodes_json=state["draft"],
            owner_user_id=user.user_id,
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        draft_id = draft.id

    hitl_id = None
    hitl_ui = None
    if state.get("needs_hitl"):
        hitl_ui = hitl_ui_for_state(state)
        hitl = AskHitl(
            session_id=s.id,
            question=state.get("hitl_question") or "请确认",
            status="PENDING",
            options={
                "question": body.message,
                "workspaceId": project.workspace_id,
                "projectId": project.id,
                "ui": hitl_ui,
                "interruptedNode": state.get("interrupted_node"),
                "turnId": turn_id,
            },
        )
        session.add(hitl)
        await session.commit()
        await session.refresh(hitl)
        hitl_id = hitl.id
        await save_interrupted_checkpoint(
            session, session_id=s.id, hitl_id=hitl.id, state=dict(state)
        )
        await finish_turn(
            session,
            turn_id=turn_id,
            status=TURN_STATUS_HITL,
            route=state.get("route"),
            hitl_id=hitl_id,
            close=False,
        )
    else:
        await finish_turn(
            session,
            turn_id=turn_id,
            status=TURN_STATUS_OK if not state.get("error") else TURN_STATUS_ERROR,
            route=state.get("route"),
            error_message=str(state.get("error") or "") or None,
            close=True,
        )

    reply = state.get("reply") or "已处理"
    await append_work_log(s.id, "本轮处理完成", turn_id=turn_id)
    session.add(
        AskMessage(
            session_id=s.id,
            role="assistant",
            content=reply,
            content_type="markdown",
            payload={
                "draftId": draft_id,
                "hitlId": hitl_id,
                "draft": state.get("draft"),
                "route": state.get("route"),
                "traceId": trace_id,
                "turnId": turn_id,
                "hitlUi": hitl_ui,
            },
        )
    )
    await session.commit()
    resp_data = {
        "reply": reply,
        "draftId": draft_id,
        "hitlId": hitl_id,
        "draft": state.get("draft"),
        "needsHitl": bool(state.get("needs_hitl")),
        "route": state.get("route"),
        "traceId": trace_id,
        "turnId": turn_id,
        "hitlUi": hitl_ui,
    }
    if idem_key:
        await finish_idempotent(
            session, user_id=user.user_id, key=idem_key, route="chat", response=resp_data
        )
    return ApiResponse.ok(resp_data)


def _hitl_is_cancel(resolution: dict | None) -> bool:
    if not isinstance(resolution, dict):
        return False
    if resolution.get("cancel") is True:
        return True
    action = str(resolution.get("action") or "").strip().lower()
    return action in ("cancel", "abort", "reject")


@router.post("/hitl/resolve")
async def resolve_hitl(
    body: HitlResolveRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    auth = extract_bearer(authorization)
    cancel_req = _hitl_is_cancel(body.resolution)
    # 取消不消耗 LLM，额度用尽时也应允许取消
    if not cancel_req:
        await check_quota_or_raise(session, settings, user_id=user.user_id, eval_mode=False)

    idem_key = (idempotency_key or "").strip() or f"hitl-{body.hitl_id}"
    cached = await get_cached_response(session, user_id=user.user_id, key=idem_key, route="hitl_resolve")
    if cached is not None:
        return ApiResponse.ok(cached)

    redis = get_redis()

    async def _run() -> dict:
        await begin_idempotent(
            session,
            user_id=user.user_id,
            key=idem_key,
            route="hitl_resolve",
            request_payload={"hitlId": body.hitl_id, "resolution": body.resolution},
        )
        hitl = await session.get(AskHitl, body.hitl_id)
        if hitl is None:
            raise HTTPException(status_code=404, detail="HITL 不存在")
        s = await session.get(AskSession, hitl.session_id)
        if s is None or s.owner_user_id != user.user_id:
            raise HTTPException(status_code=403, detail="无权限")
        if hitl.status != "PENDING":
            raise HTTPException(status_code=400, detail="HITL 已处理")
        project = await session.get(AskProject, s.project_id)
        if project is None or project.deleted:
            raise HTTPException(status_code=404, detail="工程不存在")

        turn_row = await find_turn_by_hitl(
            session, hitl_options=hitl.options if isinstance(hitl.options, dict) else None, hitl_id=hitl.id
        )
        turn_id = int(turn_row.id) if turn_row is not None else None

        if cancel_req:
            resolution = dict(body.resolution or {})
            resolution["cancel"] = True
            resolution["action"] = "cancel"
            hitl.status = "CANCELLED"
            hitl.resolution = resolution
            hitl.resolved_at = datetime.now(timezone.utc)
            await session.commit()
            await complete_checkpoint(session, hitl_id=hitl.id, status="CANCELLED")
            await finish_turn(
                session,
                turn_id=turn_id,
                status=TURN_STATUS_CANCELLED,
                hitl_id=hitl.id,
                close=True,
            )
            reply = "已取消本次确认，本轮生成已终止。如需继续，请重新提问。"
            await append_work_log(
                s.id, "用户取消 HITL，终止本轮生成", turn_id=turn_id
            )
            session.add(
                AskMessage(
                    session_id=s.id,
                    role="assistant",
                    content=reply,
                    content_type="markdown",
                    payload={
                        "hitlId": hitl.id,
                        "cancelled": True,
                        "traceId": trace_id,
                        "turnId": turn_id,
                    },
                )
            )
            await session.commit()
            resp_data = {
                "id": hitl.id,
                "status": hitl.status,
                "reply": reply,
                "draftId": None,
                "draft": None,
                "needsHitl": False,
                "hitlId": None,
                "cancelled": True,
                "traceId": trace_id,
                "turnId": turn_id,
            }
            await finish_idempotent(
                session, user_id=user.user_id, key=idem_key, route="hitl_resolve", response=resp_data
            )
            return resp_data

        # 前端分槽未必带回 kind，用 options.ui.kind 补全
        resolution = dict(body.resolution or {})
        if not str(resolution.get("kind") or "").strip():
            ui = (hitl.options or {}).get("ui") if isinstance(hitl.options, dict) else None
            if isinstance(ui, dict) and ui.get("kind"):
                resolution["kind"] = ui.get("kind")
        hitl.status = "RESOLVED"
        hitl.resolution = resolution
        hitl.resolved_at = datetime.now(timezone.utc)
        await session.commit()

        if turn_id is not None:
            await resume_turn(session, turn_id=turn_id)

        question = (hitl.options or {}).get("question") or hitl.question
        if app_main.llm_client is None:
            raise HTTPException(status_code=503, detail="LLM 未就绪")

        cp = await load_checkpoint_for_hitl(session, hitl_id=hitl.id)
        try:
            from dbc_askdata.knowledge.hitl_card import save_hitl_card

            await save_hitl_card(
                session,
                hitl=hitl,
                resolution=resolution,
                connection_id=project.source_connection_id,
                database=project.source_database,
                schema=project.source_schema,
                project_id=project.id,
                owner_user_id=user.user_id,
                checkpoint_state=cp.state_json if cp is not None else None,
            )
        except Exception:
            log.warning("HITL 确认卡片写入失败 hitl_id=%s", hitl.id, exc_info=True)
        recent = await load_chat_recent_turns(session, session_id=s.id, max_turns=KEEP_WINDOW)
        verified = await load_verified_sample_tables(
            session,
            session_id=s.id,
            default_schema=project.source_schema,
            keep=KEEP_WINDOW,
        )
        state_in: dict = {
            "question": str(question),
            "workspace_id": project.workspace_id,
            "connection_id": project.source_connection_id,
            "database": project.source_database or "",
            "schema": project.source_schema or "",
            "project_id": project.id,
            "session_id": s.id,
            "user_id": user.user_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
            "authorization": auth,
            "hitl_resolution": resolution,
            "recent_turns": recent,
            "verified_samples": verified,
        }
        if cp is not None and isinstance(cp.state_json, dict):
            snap = dict(cp.state_json)
            snap.pop("authorization", None)
            state_in.update(snap)
            state_in["hitl_resolution"] = resolution
            state_in["resume_from"] = cp.resume_from or "build"
            state_in["trace_id"] = trace_id
            state_in["turn_id"] = turn_id or state_in.get("turn_id")
            state_in["authorization"] = auth
            log.info(
                "HITL 断点续跑 hitl_id=%s resume_from=%s interrupted=%s",
                hitl.id,
                state_in.get("resume_from"),
                cp.interrupted_node,
            )

        sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
        gateway = ToolGateway(build_tool_registry(settings, sqlwork))
        spans = SpanRecorder(settings)
        bind_quota(user_id=user.user_id, eval_mode=False)
        from dbc_askdata.concurrency.chat_gate import acquire_chat_slot as _acquire_hitl_slot

        try:
            async with _acquire_hitl_slot():
                try:
                    state = await run_generate_graph(
                        settings=settings,
                        session=session,
                        spans=spans,
                        tool_gateway=gateway,
                        sqlwork=sqlwork,
                        llm=app_main.llm_client,
                        state=state_in,
                    )
                except LlmError as ex:
                    await finish_turn(
                        session,
                        turn_id=turn_id,
                        status=TURN_STATUS_ERROR,
                        error_message=str(ex),
                        close=True,
                    )
                    raise _llm_unavailable(ex) from ex
                except Exception as ex:
                    await finish_turn(
                        session,
                        turn_id=turn_id,
                        status=TURN_STATUS_ERROR,
                        error_message=str(ex),
                        close=True,
                    )
                    raise
        finally:
            clear_quota()
            clear_turn()

        draft_id = None
        if state.get("draft"):
            draft = AskWorkflowDraft(
                project_id=project.id,
                session_id=s.id,
                name=(state["draft"].get("name") or "草稿")[:128],
                nodes_json=state["draft"],
                owner_user_id=user.user_id,
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
            draft_id = draft.id

        hitl_ui = None
        next_hitl_id = None
        if state.get("needs_hitl"):
            hitl_ui = hitl_ui_for_state(state)
            new_hitl = AskHitl(
                session_id=s.id,
                question=state.get("hitl_question") or "请确认",
                status="PENDING",
                options={
                    "question": question,
                    "workspaceId": project.workspace_id,
                    "projectId": project.id,
                    "ui": hitl_ui,
                    "interruptedNode": state.get("interrupted_node"),
                    "turnId": turn_id,
                },
            )
            session.add(new_hitl)
            await session.commit()
            await session.refresh(new_hitl)
            await save_interrupted_checkpoint(
                session, session_id=s.id, hitl_id=new_hitl.id, state=dict(state)
            )
            next_hitl_id = new_hitl.id
            await finish_turn(
                session,
                turn_id=turn_id,
                status=TURN_STATUS_HITL,
                route=state.get("route"),
                hitl_id=next_hitl_id,
                close=False,
            )
        else:
            await complete_checkpoint(session, hitl_id=hitl.id)
            await finish_turn(
                session,
                turn_id=turn_id,
                status=TURN_STATUS_OK if not state.get("error") else TURN_STATUS_ERROR,
                route=state.get("route"),
                error_message=str(state.get("error") or "") or None,
                close=True,
            )

        reply = state.get("reply") or "已根据确认继续生成"
        session.add(
            AskMessage(
                session_id=s.id,
                role="assistant",
                content=reply,
                content_type="markdown",
                payload={
                    "draftId": draft_id,
                    "hitlId": next_hitl_id or hitl.id,
                    "draft": state.get("draft"),
                    "resumed": True,
                    "traceId": trace_id,
                    "turnId": turn_id,
                    "hitlUi": hitl_ui,
                },
            )
        )
        await session.commit()
        resp_data = {
            "id": hitl.id,
            "status": hitl.status,
            "reply": reply,
            "draftId": draft_id,
            "draft": state.get("draft"),
            "needsHitl": bool(state.get("needs_hitl")),
            "hitlId": next_hitl_id,
            "hitlUi": hitl_ui,
            "traceId": trace_id,
            "turnId": turn_id,
        }
        await finish_idempotent(
            session, user_id=user.user_id, key=idem_key, route="hitl_resolve", response=resp_data
        )
        return resp_data

    if redis is None:
        return ApiResponse.ok(await _run())
    async with redis.lock("hitl", str(body.hitl_id), ttl_seconds=120, wait_seconds=30):
        return ApiResponse.ok(await _run())


@router.post("/workflows")
async def save_workflow(
    body: WorkflowSaveRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(AskProject, body.project_id)
    if project is None or project.deleted or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工程不存在")

    linked_msg = None
    if body.session_id and body.draft_id:
        ask_session = await session.get(AskSession, body.session_id)
        if ask_session is None or ask_session.owner_user_id != user.user_id:
            raise HTTPException(status_code=404, detail="会话不存在")
        linked_msg = await find_assistant_message_by_draft(
            session, session_id=body.session_id, draft_id=int(body.draft_id)
        )
        if linked_msg is not None:
            payload = linked_msg.payload if isinstance(linked_msg.payload, dict) else {}
            existing_wf_id = payload.get("workflowId") or payload.get("workflow_id")
            if existing_wf_id and payload.get("saved"):
                try:
                    wid = int(existing_wf_id)
                except (TypeError, ValueError):
                    wid = None
                if wid is not None:
                    existing = await session.get(AskWorkflow, wid)
                    if existing is not None and not existing.deleted:
                        return ApiResponse.ok(
                            {
                                "id": existing.id,
                                "name": existing.name,
                                "projectId": existing.project_id,
                                "alreadySaved": True,
                                "messageId": linked_msg.id,
                            }
                        )

    wf = AskWorkflow(
        project_id=project.id,
        name=body.name.strip(),
        description=body.description,
        nodes_json=body.nodes_json,
        owner_user_id=user.user_id,
    )
    session.add(wf)
    if body.draft_id:
        draft = await session.get(AskWorkflowDraft, body.draft_id)
        if draft and draft.owner_user_id == user.user_id:
            await session.delete(draft)
    await session.commit()
    await session.refresh(wf)

    if linked_msg is not None:
        await mark_message_workflow_saved(session, message=linked_msg, workflow_id=int(wf.id))

    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="CREATE",
            resource_type="ask_workflow",
            resource_id=str(wf.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            details={"projectId": wf.project_id, "name": wf.name},
        )
    return ApiResponse.ok(
        {
            "id": wf.id,
            "name": wf.name,
            "projectId": wf.project_id,
            "alreadySaved": False,
            "messageId": linked_msg.id if linked_msg is not None else None,
        }
    )


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    wf = await session.get(AskWorkflow, workflow_id)
    if wf is None or wf.deleted or wf.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工作流不存在")
    return ApiResponse.ok(
        {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "projectId": wf.project_id,
            "nodesJson": wf.nodes_json,
        }
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(AskProject, project_id)
    if project is None or project.deleted or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工程不存在")
    project.deleted = True
    wfs = (
        await session.execute(
            select(AskWorkflow).where(AskWorkflow.project_id == project_id, AskWorkflow.deleted.is_(False))
        )
    ).scalars().all()
    for wf in wfs:
        wf.deleted = True
    await session.commit()
    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="DELETE",
            resource_type="ask_project",
            resource_id=str(project.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            details={"workflowCount": len(wfs)},
        )
    return ApiResponse.ok({"id": project.id, "deleted": True})


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    wf = await session.get(AskWorkflow, workflow_id)
    if wf is None or wf.deleted or wf.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工作流不存在")
    wf.deleted = True
    await session.commit()
    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="DELETE",
            resource_type="ask_workflow",
            resource_id=str(wf.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            details={"projectId": wf.project_id, "name": wf.name},
        )
    return ApiResponse.ok({"id": wf.id, "deleted": True})


@router.post("/runs")
async def start_run(
    body: RunStartRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
):
    auth = extract_bearer(authorization)
    wf = await load_workflow(session, body.workflow_id)
    if wf is None or wf.deleted or wf.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工作流不存在")
    project = await load_project(session, wf.project_id)
    if project is None or project.deleted:
        raise HTTPException(status_code=404, detail="工程不存在")
    sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
    conns = await sqlwork.list_connections(project.workspace_id)
    work_db_type = "POSTGRESQL"
    for c in conns:
        if int(c.get("connectionId") or 0) == project.work_connection_id:
            work_db_type = str(c.get("dbType") or "POSTGRESQL")
            break
    runner = WorkflowRunner(settings, SpanRecorder(settings), work_db_type=work_db_type)
    run = await runner.start_run(
        session,
        workflow=wf,
        project=project,
        sqlwork=sqlwork,
        user_id=user.user_id,
        session_id=body.session_id,
        trace_id=trace_id,
        authorization=auth,
        work_db_type=work_db_type,
    )
    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="EXECUTE",
            resource_type="ask_workflow_run",
            resource_id=str(run.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            result="SUCCESS" if run.status == "SUCCESS" else "FAIL",
            fail_reason=run.error_message,
            details={"workflowId": wf.id, "status": run.status},
            trace_id=trace_id,
        )
    return ApiResponse.ok(
        {
            "id": run.id,
            "status": run.status,
            "errorMessage": run.error_message,
            "resultTableFqn": run.result_table_fqn,
            "traceId": trace_id,
        }
    )


@router.post("/runs/confirm-correct")
async def confirm_sql_correct(
    body: ConfirmSqlCorrectRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
):
    """兼容旧入口：等价于 feedback action=useful（幂等）。"""
    auth = extract_bearer(authorization)
    run = await session.get(AskWorkflowRun, body.run_id)
    if run is None or run.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="运行不存在")
    if (run.status or "").upper() != "SUCCESS":
        raise HTTPException(status_code=400, detail="仅执行成功的运行可确认")
    wf = await load_workflow(session, run.workflow_id)
    if wf is None or wf.deleted:
        raise HTTPException(status_code=404, detail="工作流不存在")
    sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
    try:
        data = await apply_run_feedback(
            session,
            settings=settings,
            sqlwork=sqlwork,
            user_id=user.user_id,
            run_id=run.id,
            workflow=wf,
            action="useful",
            session_id=body.session_id,
            question=body.question,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex)) from ex
    return ApiResponse.ok(
        {
            "sampleId": data.get("sampleId"),
            "workflowId": wf.id,
            "runId": run.id,
            "question": body.question,
            "knowledge": data.get("knowledge"),
            "alreadyProcessed": data.get("alreadyProcessed"),
            "feedback": data.get("feedback"),
        }
    )


@router.post("/runs/{run_id}/feedback")
async def submit_run_feedback(
    run_id: int,
    body: RunFeedbackRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
):
    """画布右下角：有用 / 无用 / 保存记忆（幂等）。"""
    auth = extract_bearer(authorization)
    run = await get_run(session, run_id)
    if run is None or run.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="运行不存在")
    if (run.status or "").upper() != "SUCCESS":
        raise HTTPException(status_code=400, detail="仅执行成功后可反馈")
    wf = await load_workflow(session, run.workflow_id)
    if wf is None or wf.deleted:
        raise HTTPException(status_code=404, detail="工作流不存在")
    sid = body.session_id if body.session_id is not None else run.session_id
    sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
    try:
        data = await apply_run_feedback(
            session,
            settings=settings,
            sqlwork=sqlwork,
            user_id=user.user_id,
            run_id=run.id,
            workflow=wf,
            action=body.action,
            session_id=sid,
            question=body.question,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex)) from ex
    return ApiResponse.ok(data)


@router.post("/runs/{run_id}/stop")
async def stop_run(
    run_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
):
    auth = extract_bearer(authorization)
    run = await get_run(session, run_id)
    if run is None or run.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="运行不存在")
    sqlwork = SqlworkClient(settings, auth)
    runner = WorkflowRunner(settings, SpanRecorder(settings))
    run = await runner.stop(session, run, sqlwork)
    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="STOP",
            resource_type="ask_workflow_run",
            resource_id=str(run.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            details={"status": run.status},
        )
    return ApiResponse.ok({"id": run.id, "status": run.status})


@router.get("/runs/{run_id}")
async def run_detail(
    run_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    run = await get_run(session, run_id)
    if run is None or run.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="运行不存在")
    logs = await list_run_logs(session, run_id)
    result = (
        await session.execute(select(AskWorkflowRunResult).where(AskWorkflowRunResult.run_id == run_id))
    ).scalar_one_or_none()
    elapsed_ms: int | None = None
    if run.started_at is not None and run.finished_at is not None:
        elapsed_ms = max(0, int((run.finished_at - run.started_at).total_seconds() * 1000))
    fb = await get_feedback(session, run_id=run_id, user_id=user.user_id)
    return ApiResponse.ok(
        {
            "id": run.id,
            "status": run.status,
            "errorMessage": run.error_message,
            "sessionId": run.session_id,
            "workflowId": run.workflow_id,
            "startedAt": run.started_at,
            "finishedAt": run.finished_at,
            "elapsedMs": elapsed_ms,
            "feedback": feedback_vo(fb),
            "feedbackReady": (run.status or "").upper() == "SUCCESS",
            "logs": [
                {"id": l.id, "level": l.level, "message": l.message, "createdAt": l.created_at}
                for l in logs
                if (l.level or "INFO").upper() != "DEBUG"
            ],
            "result": None
            if result is None
            else {
                "columns": result.columns_json,
                "rows": result.rows_json,
                "rowCount": result.row_count,
                "truncated": result.truncated,
            },
        }
    )
