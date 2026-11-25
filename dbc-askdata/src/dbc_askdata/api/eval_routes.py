from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.api.schemas import (
    ApiResponse,
    EvalCaseCreateRequest,
    EvalCasePatchRequest,
    EvalProjectCreateRequest,
    EvalTaskCreateRequest,
    EvalTaskPatchRequest,
    EvalTaskStartRequest,
)
from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings, get_settings
from dbc_askdata.db.models import AskProject
from dbc_askdata.db.scope import find_connection, normalize_scope
from dbc_askdata.db.session import get_session
from dbc_askdata.eval.categories import REMOVED_CATEGORIES
from dbc_askdata.eval.metrics import aggregate_metrics
from dbc_askdata.eval.models import EvalCase, EvalProject, EvalTask, EvalTaskCase, EvalTemplate
from dbc_askdata.eval.runner import (
    request_cancel,
    start_eval_task_background,
    stop_eval_task_background,
)
from dbc_askdata.security.auth import LoginUser, extract_bearer, require_permission

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/eval")


def _elapsed_ms(
    started: datetime | None,
    finished: datetime | None,
    *,
    live_if_running: bool = False,
) -> int | None:
    if started is None:
        return None
    end = finished
    if end is None:
        if not live_if_running:
            return None
        end = datetime.now(timezone.utc)
    return max(0, int((end - started).total_seconds() * 1000))


def _template_vo(t: EvalTemplate) -> dict:
    return {
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "version": t.version,
        "remark": t.remark,
        "enabled": t.enabled,
        "createdAt": t.created_at,
    }


def _project_vo(p: EvalProject) -> dict:
    return {
        "id": p.id,
        "workspaceId": p.workspace_id,
        "name": p.name,
        "remark": p.remark,
        "templateId": p.template_id,
        "sourceConnectionId": p.source_connection_id,
        "sourceDatabase": p.source_database,
        "sourceSchema": p.source_schema,
        "workConnectionId": p.work_connection_id,
        "workDatabase": p.work_database,
        "workSchema": p.work_schema,
        "askProjectId": p.ask_project_id,
        "ownerUserId": p.owner_user_id,
        "createdAt": p.created_at,
        "updatedAt": p.updated_at,
    }


def _case_vo(c: EvalCase) -> dict:
    return {
        "id": c.id,
        "caseKey": c.case_key,
        "scope": c.scope,
        "templateId": c.template_id,
        "projectId": c.project_id,
        "category": c.category,
        "governSubtype": c.govern_subtype,
        "question": c.question,
        "expectSql": c.expect_sql,
        "compareMode": c.compare_mode,
        "compareSpec": c.compare_spec_json or {},
        "hitlReplies": c.hitl_replies_json,
        "tags": c.tags_json,
        "difficulty": c.difficulty,
        "enabled": c.enabled,
        "createdAt": c.created_at,
        "updatedAt": c.updated_at,
    }


def _task_vo(t: EvalTask) -> dict:
    live = (t.status or "").upper() == "RUNNING"
    elapsed = _elapsed_ms(t.started_at, t.finished_at, live_if_running=live)
    metrics = dict(t.metrics_json or {}) if t.metrics_json else {}
    if elapsed is not None and "elapsedMs" not in metrics:
        metrics = {**metrics, "elapsedMs": elapsed}
    return {
        "id": t.id,
        "projectId": t.project_id,
        "workspaceId": t.workspace_id,
        "name": t.name,
        "status": t.status,
        "metrics": metrics or None,
        "errorMessage": t.error_message,
        "createdBy": t.created_by,
        "startedAt": t.started_at,
        "finishedAt": t.finished_at,
        "createdAt": t.created_at,
        "elapsedMs": elapsed,
    }


def _task_case_vo(c: EvalTaskCase) -> dict:
    live = (c.status or "").upper() == "RUNNING"
    return {
        "id": c.id,
        "taskId": c.task_id,
        "caseId": c.case_id,
        "caseKey": c.case_key,
        "question": c.question,
        "expectSql": c.expect_sql,
        "compareMode": c.compare_mode,
        "compareSpec": c.compare_spec_json or {},
        "governSubtype": c.govern_subtype,
        "category": c.category,
        "hitlReplies": c.hitl_replies_json,
        "status": c.status,
        "askSql": c.ask_sql,
        "askError": c.ask_error,
        "hitlRounds": c.hitl_rounds,
        "compareScore": float(c.compare_score) if c.compare_score is not None else None,
        "compareDetail": c.compare_detail_json,
        "expectRowCount": c.expect_row_count,
        "askRowCount": c.ask_row_count,
        "traceId": c.trace_id,
        "workflowId": c.workflow_id,
        "runId": c.run_id,
        "sessionId": c.session_id,
        "startedAt": c.started_at,
        "finishedAt": c.finished_at,
        "elapsedMs": _elapsed_ms(c.started_at, c.finished_at, live_if_running=live),
    }


async def _get_owned_project(session: AsyncSession, project_id: int, user: LoginUser) -> EvalProject:
    p = await session.get(EvalProject, project_id)
    if p is None or p.owner_user_id != user.user_id:
        raise HTTPException(status_code=404, detail="测评工程不存在")
    return p


@router.get("/templates")
async def list_templates(
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(EvalTemplate).where(EvalTemplate.enabled.is_(True)).order_by(EvalTemplate.id.asc())
        )
    ).scalars().all()
    return ApiResponse.ok([_template_vo(t) for t in rows])


@router.post("/projects")
async def create_eval_project(
    body: EvalProjectCreateRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
):
    tpl = await session.get(EvalTemplate, body.template_id)
    if tpl is None or not tpl.enabled:
        raise HTTPException(status_code=400, detail="测评模板不存在或未启用")

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

    shadow = AskProject(
        name=f"[测评] {body.name.strip()}"[:128],
        description="eval_shadow",
        workspace_id=body.workspace_id,
        source_connection_id=body.source_connection_id,
        source_database=source_db,
        source_schema=source_schema,
        work_connection_id=body.work_connection_id,
        work_database=work_db,
        work_schema=work_schema,
        owner_user_id=user.user_id,
        hidden=True,
    )
    session.add(shadow)
    await session.flush()

    project = EvalProject(
        workspace_id=body.workspace_id,
        name=body.name.strip(),
        remark=body.remark,
        template_id=tpl.id,
        source_connection_id=body.source_connection_id,
        source_database=source_db,
        source_schema=source_schema,
        work_connection_id=body.work_connection_id,
        work_database=work_db,
        work_schema=work_schema,
        ask_project_id=shadow.id,
        owner_user_id=user.user_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return ApiResponse.ok(_project_vo(project))


@router.get("/projects")
async def list_eval_projects(
    workspace_id: int = Query(..., alias="workspaceId"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(EvalProject)
            .where(
                EvalProject.workspace_id == workspace_id,
                EvalProject.owner_user_id == user.user_id,
            )
            .order_by(EvalProject.id.desc())
        )
    ).scalars().all()
    return ApiResponse.ok([_project_vo(p) for p in rows])


@router.delete("/projects/{project_id}")
async def delete_eval_project(
    project_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await _get_owned_project(session, project_id, user)
    running = (
        await session.execute(
            select(EvalTask.id).where(
                EvalTask.project_id == project.id,
                EvalTask.status == "RUNNING",
            ).limit(1)
        )
    ).scalar_one_or_none()
    if running is not None:
        raise HTTPException(status_code=400, detail="存在 RUNNING 任务，禁止删除工程")

    shadow = await session.get(AskProject, project.ask_project_id)
    if shadow is not None:
        shadow.deleted = True
    # 自定义用例随 FK cascade；模板用例保留
    await session.delete(project)
    await session.commit()
    return ApiResponse.ok({"id": project_id, "deleted": True})


@router.get("/projects/{project_id}/cases")
async def list_project_cases(
    project_id: int,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await _get_owned_project(session, project_id, user)
    cond = [
        EvalCase.enabled.is_(True),
        EvalCase.category.not_in(REMOVED_CATEGORIES),
        or_(
            and_(EvalCase.scope == "TEMPLATE", EvalCase.template_id == project.template_id),
            and_(EvalCase.scope == "PROJECT_CUSTOM", EvalCase.project_id == project.id),
        ),
    ]
    if category:
        cond.append(EvalCase.category == category)
    total = int(
        (await session.execute(select(func.count()).select_from(EvalCase).where(*cond))).scalar_one()
    )
    rows = (
        await session.execute(
            select(EvalCase)
            .where(*cond)
            .order_by(EvalCase.case_key.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ApiResponse.ok(
        {
            "items": [_case_vo(c) for c in rows],
            "page": page,
            "pageSize": page_size,
            "total": total,
        }
    )


@router.post("/projects/{project_id}/cases")
async def create_custom_case(
    project_id: int,
    body: EvalCaseCreateRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await _get_owned_project(session, project_id, user)
    case_key = (body.case_key or f"CUSTOM_{project.id}_{uuid.uuid4().hex[:10]}").strip()
    if body.category.strip() in REMOVED_CATEGORIES:
        raise HTTPException(status_code=400, detail="该测评分类已下线")
    exists = (
        await session.execute(select(EvalCase.id).where(EvalCase.case_key == case_key))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="caseKey 已存在")
    row = EvalCase(
        case_key=case_key,
        scope="PROJECT_CUSTOM",
        template_id=None,
        project_id=project.id,
        category=body.category.strip(),
        govern_subtype=body.govern_subtype,
        question=body.question.strip(),
        expect_sql=body.expect_sql,
        compare_mode=(body.compare_mode or "order_by").strip() or "order_by",
        compare_spec_json=body.compare_spec or {},
        hitl_replies_json=body.hitl_replies,
        tags_json=body.tags,
        difficulty=body.difficulty,
        enabled=True,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ApiResponse.ok(_case_vo(row))


@router.patch("/cases/{case_id}")
async def patch_case(
    case_id: int,
    body: EvalCasePatchRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(EvalCase, case_id)
    if row is None or row.scope != "PROJECT_CUSTOM":
        raise HTTPException(status_code=404, detail="仅自定义用例可修改")
    project = await session.get(EvalProject, row.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    data = body.model_dump(exclude_unset=True, by_alias=False)
    if "category" in data:
        category = (data["category"] or "").strip()
        if not category or category in REMOVED_CATEGORIES:
            raise HTTPException(status_code=400, detail="测评分类无效或已下线")
        data["category"] = category
    mapping = {
        "expect_sql": "expect_sql",
        "compare_mode": "compare_mode",
        "compare_spec": "compare_spec_json",
        "hitl_replies": "hitl_replies_json",
        "govern_subtype": "govern_subtype",
        "tags": "tags_json",
    }
    for k, v in data.items():
        attr = mapping.get(k, k)
        setattr(row, attr, v)
    row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return ApiResponse.ok(_case_vo(row))


@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(EvalCase, case_id)
    if row is None or row.scope != "PROJECT_CUSTOM":
        raise HTTPException(status_code=404, detail="仅自定义用例可删除")
    project = await session.get(EvalProject, row.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    await session.delete(row)
    await session.commit()
    return ApiResponse.ok({"id": case_id, "deleted": True})


@router.post("/tasks")
async def create_task(
    body: EvalTaskCreateRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    project = await _get_owned_project(session, body.project_id, user)
    # 校验用例属于模板或本工程
    cases = (
        await session.execute(select(EvalCase).where(EvalCase.id.in_(body.case_ids)))
    ).scalars().all()
    if len(cases) != len(set(body.case_ids)):
        raise HTTPException(status_code=400, detail="部分用例不存在")
    for c in cases:
        ok = (
            (c.scope == "TEMPLATE" and c.template_id == project.template_id)
            or (c.scope == "PROJECT_CUSTOM" and c.project_id == project.id)
        )
        if not ok or not c.enabled or c.category in REMOVED_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"用例不可用于本工程: {c.case_key}")

    name = (body.name or f"测评任务 {datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}").strip()[:128]
    task = EvalTask(
        project_id=project.id,
        workspace_id=project.workspace_id,
        name=name,
        status="PENDING",
        created_by=user.user_id,
    )
    session.add(task)
    await session.flush()
    for c in cases:
        session.add(
            EvalTaskCase(
                task_id=task.id,
                case_id=c.id,
                case_key=c.case_key,
                question=c.question,
                expect_sql=c.expect_sql,
                compare_mode=c.compare_mode,
                compare_spec_json=c.compare_spec_json or {},
                govern_subtype=c.govern_subtype,
                category=c.category,
                hitl_replies_json=c.hitl_replies_json,
                status="PENDING",
            )
        )
    await session.commit()
    await session.refresh(task)
    return ApiResponse.ok(_task_vo(task))


def _reset_task_case(c: EvalTaskCase) -> None:
    """清空用例跑批历史，回到 PENDING，便于再次执行。"""
    c.status = "PENDING"
    c.ask_sql = None
    c.ask_error = None
    c.compare_score = None
    c.compare_detail_json = None
    c.expect_row_count = None
    c.ask_row_count = None
    c.hitl_rounds = 0
    c.trace_id = None
    c.workflow_id = None
    c.run_id = None
    c.session_id = None
    c.started_at = None
    c.finished_at = None


@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: int,
    body: EvalTaskStartRequest = Body(default_factory=EvalTaskStartRequest),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    """启动跑批与重新执行同一入口：可选 taskCaseIds；已跑过的用例会先清历史再跑。"""
    import dbc_askdata.main as app_main

    task = await session.get(EvalTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = await session.get(EvalProject, task.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    status = (task.status or "").upper()
    if status == "RUNNING":
        raise HTTPException(status_code=409, detail="任务正在运行，请先取消或等待结束后再启动")
    if status not in ("PENDING", "CANCELLED", "SUCCEEDED", "FAILED"):
        raise HTTPException(status_code=400, detail=f"任务状态不可启动: {task.status}")
    if app_main.llm_client is None:
        raise HTTPException(status_code=503, detail="LLM 未就绪")
    auth = extract_bearer(authorization)

    # 必须先停稳旧后台，再清 PENDING；否则旧协程收尾会把刚重置的用例标成 CANCELLED，新跑批空跑
    await stop_eval_task_background(task.id)

    cases = (
        await session.execute(select(EvalTaskCase).where(EvalTaskCase.task_id == task.id))
    ).scalars().all()
    selected_ids = [int(x) for x in (body.task_case_ids or []) if x is not None]
    # 去重保序
    seen: set[int] = set()
    selected_unique: list[int] = []
    for i in selected_ids:
        if i not in seen:
            seen.add(i)
            selected_unique.append(i)

    if selected_unique:
        by_id = {c.id: c for c in cases}
        missing = [i for i in selected_unique if i not in by_id]
        if missing:
            raise HTTPException(status_code=400, detail=f"用例不属于本任务: {missing[:10]}")
        to_reset = [by_id[i] for i in selected_unique]
        run_ids: list[int] | None = selected_unique
    else:
        # 未勾选：清理全部用例历史后整任务跑批
        to_reset = list(cases)
        run_ids = None

    if not to_reset:
        raise HTTPException(status_code=400, detail="没有可执行的用例")

    for c in to_reset:
        _reset_task_case(c)

    task.status = "PENDING"
    task.error_message = None
    task.started_at = None
    task.finished_at = None
    task.metrics_json = None
    await session.commit()
    await start_eval_task_background(
        task_id=task.id,
        llm=app_main.llm_client,
        authorization=auth or "",
        user_id=user.user_id,
        task_case_ids=run_ids,
    )
    await session.refresh(task)
    return ApiResponse.ok(_task_vo(task))


@router.patch("/tasks/{task_id}")
async def patch_task(
    task_id: int,
    body: EvalTaskPatchRequest,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    """修改测评任务名称（任意状态可改，不影响跑批）。"""
    task = await session.get(EvalTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = await session.get(EvalProject, task.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="任务名称不能为空")
    task.name = name[:128]
    await session.commit()
    await session.refresh(task)
    return ApiResponse.ok(_task_vo(task))


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(EvalTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = await session.get(EvalProject, task.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    request_cancel(task_id)
    await stop_eval_task_background(task_id)
    # 停稳后按库内状态收口：仍 RUNNING/PENDING 的标为 CANCELLED
    await session.refresh(task)
    if (task.status or "").upper() in ("PENDING", "RUNNING"):
        task.status = "CANCELLED"
        task.finished_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(task)
    return ApiResponse.ok(_task_vo(task))


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(EvalTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = await session.get(EvalProject, task.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    if (task.status or "").upper() == "RUNNING":
        raise HTTPException(status_code=400, detail="运行中任务请先取消后再删除")
    await session.delete(task)
    await session.commit()
    return ApiResponse.ok({"id": task_id, "deleted": True})


@router.get("/tasks")
async def list_tasks(
    workspace_id: int | None = Query(default=None, alias="workspaceId"),
    project_id: int | None = Query(default=None, alias="projectId"),
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    q = select(EvalTask).join(EvalProject, EvalProject.id == EvalTask.project_id).where(
        EvalProject.owner_user_id == user.user_id
    )
    if workspace_id is not None:
        q = q.where(EvalTask.workspace_id == workspace_id)
    if project_id is not None:
        q = q.where(EvalTask.project_id == project_id)
    rows = (await session.execute(q.order_by(EvalTask.id.desc()).limit(200))).scalars().all()
    return ApiResponse.ok([_task_vo(t) for t in rows])


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(EvalTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = await session.get(EvalProject, task.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    return ApiResponse.ok(_task_vo(task))


@router.get("/tasks/{task_id}/cases")
async def list_task_cases(
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    status: str | None = None,
    category: str | None = None,
    user: LoginUser = Depends(require_permission("askdata.use")),
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(EvalTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    project = await session.get(EvalProject, task.project_id)
    if project is None or project.owner_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="无权限")
    cond = [EvalTaskCase.task_id == task_id]
    if status:
        cond.append(EvalTaskCase.status == status.strip())
    if category and category.strip():
        cond.append(EvalTaskCase.category == category.strip())
    total = int(
        (await session.execute(select(func.count()).select_from(EvalTaskCase).where(*cond))).scalar_one()
    )
    rows = (
        await session.execute(
            select(EvalTaskCase)
            .where(*cond)
            .order_by(EvalTaskCase.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    all_cases = (
        await session.execute(select(EvalTaskCase).where(EvalTaskCase.task_id == task_id))
    ).scalars().all()
    missing_ids = [c.case_id for c in all_cases if c.case_id and not (c.category or "").strip()]
    if missing_ids:
        cat_rows = (
            await session.execute(select(EvalCase.id, EvalCase.category).where(EvalCase.id.in_(missing_ids)))
        ).all()
        cat_map = {int(i): str(cat) for i, cat in cat_rows if cat}
        for c in all_cases:
            if not (c.category or "").strip() and c.case_id in cat_map:
                c.category = cat_map[c.case_id]
    task_vo = _task_vo(task)
    live = aggregate_metrics(all_cases)
    elapsed = task_vo.get("elapsedMs")
    if elapsed is not None:
        live = {**live, "elapsedMs": elapsed}
    task_vo["metrics"] = live
    return ApiResponse.ok(
        {
            "items": [_task_case_vo(c) for c in rows],
            "page": page,
            "pageSize": page_size,
            "total": total,
            "task": task_vo,
        }
    )
