from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import (
    ApiResponse,
    ChatRequest,
    HitlResolveRequest,
    ProjectCreateRequest,
    ProjectVO,
    RunStartRequest,
    SessionCreateRequest,
    TreeProjectVO,
    TreeWorkflowVO,
    WorkflowSaveRequest,
)
from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.models import (
    AskHitl,
    AskLlmSpan,
    AskMessage,
    AskProject,
    AskSession,
    AskWorkflow,
    AskWorkflowDraft,
    AskWorkflowRunResult,
)
from dbc_askdata.db.scope import find_connection, normalize_scope
from dbc_askdata.db.session import get_session
from dbc_askdata.graph.generate import run_generate_graph
from dbc_askdata.llm.client import LlmError
from dbc_askdata.observability.spans import SpanRecorder
from dbc_askdata.observability.trace import get_trace_id
from dbc_askdata.observability.worklog import append_work_log, clear_work_logs, list_work_logs
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
    """清空会话消息与待确认 HITL；工作日志一并清理。"""
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
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(AskSession, session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ApiResponse.ok(await list_work_logs(session_id, after=max(0, after)))


@router.get("/sessions/{session_id}/llm-spans")
async def list_session_llm_spans(
    session_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    """会话归属者可查看本会话 LLM/图/工具 span，作为进程内 work-log 过期后的持久回退。"""
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


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
):
    auth = extract_bearer(authorization)
    s = await session.get(AskSession, body.session_id)
    if s is None or s.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="会话不存在")
    project = await session.get(AskProject, s.project_id)
    if project is None or project.deleted:
        raise HTTPException(status_code=404, detail="工程不存在")

    session.add(AskMessage(session_id=s.id, role="user", content=body.message))
    await session.commit()

    await clear_work_logs(s.id)
    await append_work_log(s.id, f"收到消息：{body.message[:120]}")

    sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
    registry = build_tool_registry(settings, sqlwork)
    gateway = ToolGateway(registry)
    spans = SpanRecorder(settings)
    if app_main.llm_client is None:
        raise HTTPException(status_code=503, detail="LLM 未就绪")
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
                "authorization": auth,
            },
        )
    except LlmError as ex:
        await append_work_log(s.id, f"失败：{ex}", level="ERROR")
        raise _llm_unavailable(ex) from ex

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
    if state.get("needs_hitl"):
        hitl = AskHitl(
            session_id=s.id,
            question=state.get("hitl_question") or "请确认",
            status="PENDING",
            options={
                "question": body.message,
                "workspaceId": project.workspace_id,
                "projectId": project.id,
            },
        )
        session.add(hitl)
        await session.commit()
        await session.refresh(hitl)
        hitl_id = hitl.id

    reply = state.get("reply") or "已处理"
    await append_work_log(s.id, "本轮处理完成")
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
            },
        )
    )
    await session.commit()
    return ApiResponse.ok(
        {
            "reply": reply,
            "draftId": draft_id,
            "hitlId": hitl_id,
            "draft": state.get("draft"),
            "needsHitl": bool(state.get("needs_hitl")),
            "route": state.get("route"),
            "traceId": trace_id,
        }
    )


@router.post("/hitl/resolve")
async def resolve_hitl(
    body: HitlResolveRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    trace_id: str = Depends(get_trace_id),
):
    auth = extract_bearer(authorization)
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

    hitl.status = "RESOLVED"
    hitl.resolution = body.resolution
    hitl.resolved_at = datetime.now(timezone.utc)
    await session.commit()

    # 续跑生成图
    question = (hitl.options or {}).get("question") or hitl.question
    if app_main.llm_client is None:
        raise HTTPException(status_code=503, detail="LLM 未就绪")
    sqlwork = SqlworkClient(settings, auth, trace_id=trace_id)
    gateway = ToolGateway(build_tool_registry(settings, sqlwork))
    spans = SpanRecorder(settings)
    try:
        state = await run_generate_graph(
            settings=settings,
            session=session,
            spans=spans,
            tool_gateway=gateway,
            sqlwork=sqlwork,
            llm=app_main.llm_client,
            state={
                "question": str(question),
                "workspace_id": project.workspace_id,
                "connection_id": project.source_connection_id,
                "database": project.source_database or "",
                "schema": project.source_schema or "",
                "project_id": project.id,
                "session_id": s.id,
                "user_id": user.user_id,
                "trace_id": trace_id,
                "authorization": auth,
                "hitl_resolution": body.resolution,
            },
        )
    except LlmError as ex:
        raise _llm_unavailable(ex) from ex
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
    reply = state.get("reply") or "已根据确认继续生成"
    session.add(
        AskMessage(
            session_id=s.id,
            role="assistant",
            content=reply,
            content_type="markdown",
            payload={
                "draftId": draft_id,
                "hitlId": hitl.id,
                "draft": state.get("draft"),
                "resumed": True,
                "traceId": trace_id,
            },
        )
    )
    await session.commit()
    return ApiResponse.ok(
        {
            "id": hitl.id,
            "status": hitl.status,
            "reply": reply,
            "draftId": draft_id,
            "draft": state.get("draft"),
            "needsHitl": bool(state.get("needs_hitl")),
            "traceId": trace_id,
        }
    )


@router.post("/workflows")
async def save_workflow(
    body: WorkflowSaveRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(AskProject, body.project_id)
    if project is None or project.deleted or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="工程不存在")
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
    if app_main.audit_client:
        await app_main.audit_client.emit_biz(
            action="CREATE",
            resource_type="ask_workflow",
            resource_id=str(wf.id),
            operator_user_id=user.user_id,
            operator_username=user.username,
            details={"projectId": wf.project_id, "name": wf.name},
        )
    return ApiResponse.ok({"id": wf.id, "name": wf.name, "projectId": wf.project_id})


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
    return ApiResponse.ok(
        {
            "id": run.id,
            "status": run.status,
            "errorMessage": run.error_message,
            "sessionId": run.session_id,
            "workflowId": run.workflow_id,
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
