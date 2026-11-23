from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.clients.sqlwork import SqlworkClient
from dbc_askdata.config import Settings
from dbc_askdata.db.models import AskMessage, AskRunFeedback, AskVerifiedSample, AskWorkflow
from dbc_askdata.knowledge.question_knowledge import create_question_knowledge_draft
from dbc_askdata.workflow.runner import load_project

log = logging.getLogger(__name__)

ACTIONS = frozenset({"useful", "useless", "memory"})


async def find_assistant_message_by_draft(
    session: AsyncSession,
    *,
    session_id: int,
    draft_id: int,
) -> AskMessage | None:
    rows = (
        await session.execute(
            select(AskMessage)
            .where(AskMessage.session_id == session_id, AskMessage.role == "assistant")
            .order_by(AskMessage.id.desc())
            .limit(50)
        )
    ).scalars().all()
    for m in rows:
        payload = m.payload if isinstance(m.payload, dict) else {}
        if payload.get("draftId") == draft_id or payload.get("draft_id") == draft_id:
            return m
    return None


async def mark_message_workflow_saved(
    session: AsyncSession,
    *,
    message: AskMessage,
    workflow_id: int,
) -> None:
    payload = dict(message.payload) if isinstance(message.payload, dict) else {}
    payload["saved"] = True
    payload["workflowId"] = workflow_id
    message.payload = payload
    await session.commit()


def feedback_vo(row: AskRunFeedback | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "runId": row.run_id,
        "workflowId": row.workflow_id,
        "usefulDone": bool(row.useful_done),
        "uselessDone": bool(row.useless_done),
        "memoryDone": bool(row.memory_done),
        "sampleId": row.sample_id,
        "knowledgeSaved": bool(row.sample_id) or bool(row.useful_done) or bool(row.memory_done),
    }


async def get_feedback(
    session: AsyncSession,
    *,
    run_id: int,
    user_id: int,
) -> AskRunFeedback | None:
    return (
        await session.execute(
            select(AskRunFeedback).where(
                AskRunFeedback.run_id == run_id,
                AskRunFeedback.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def _ensure_sample_and_knowledge(
    session: AsyncSession,
    *,
    settings: Settings,
    sqlwork: SqlworkClient,
    user_id: int,
    run_id: int,
    workflow: AskWorkflow,
    session_id: int | None,
    question: str | None,
    feedback: AskRunFeedback,
) -> dict[str, Any]:
    """有用 / 保存记忆共用：样本 + 问句知识草稿；已有 sample 则跳过写入。"""
    if feedback.sample_id:
        return {"alreadyProcessed": True, "sampleId": feedback.sample_id}

    project = await load_project(session, workflow.project_id)
    if project is None or project.deleted:
        raise ValueError("工程不存在")

    q = (question or "").strip()
    if not q and session_id:
        last_user = (
            await session.execute(
                select(AskMessage)
                .where(AskMessage.session_id == session_id, AskMessage.role == "user")
                .order_by(AskMessage.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        q = (last_user.content if last_user else "") or ""
    if not q:
        q = workflow.name or "问数样本"

    sid = session_id or feedback.session_id
    if not sid:
        raise ValueError("缺少 sessionId，无法写入会话样本")

    sample = AskVerifiedSample(
        session_id=int(sid),
        project_id=project.id,
        workflow_id=workflow.id,
        question=q,
        run_id=run_id,
        owner_user_id=user_id,
    )
    session.add(sample)
    await session.commit()
    await session.refresh(sample)

    nodes = workflow.nodes_json if isinstance(workflow.nodes_json, dict) else {"nodes": workflow.nodes_json}
    knowledge_meta: dict[str, Any] = {"skipped": True}
    try:
        knowledge_meta = await create_question_knowledge_draft(
            settings=settings,
            session=session,
            sqlwork=sqlwork,
            user_id=user_id,
            workspace_id=project.workspace_id,
            connection_id=project.source_connection_id,
            database=project.source_database,
            schema=project.source_schema,
            question=q,
            nodes_json=nodes if isinstance(nodes, dict) else {"nodes": []},
        )
    except Exception:
        log.warning("问句知识草稿写入失败 sample_id=%s", sample.id, exc_info=True)
        knowledge_meta = {"error": "知识草稿写入失败"}

    hitl_promote_meta: dict[str, Any] = {"skipped": True}
    try:
        from dbc_askdata.knowledge.hitl_promote import promote_session_hitl_cards

        hitl_promote_meta = await promote_session_hitl_cards(
            session,
            settings=settings,
            user_id=user_id,
            session_id=int(sid),
            nodes_json=nodes if isinstance(nodes, dict) else {"nodes": []},
            default_schema=project.source_schema,
        )
    except Exception:
        log.warning("HITL 卡片归并失败 sample_id=%s session_id=%s", sample.id, sid, exc_info=True)
        hitl_promote_meta = {"error": "HITL 卡片归并失败"}

    feedback.sample_id = sample.id
    feedback.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return {
        "alreadyProcessed": False,
        "sampleId": sample.id,
        "question": q,
        "knowledge": knowledge_meta,
        "hitlPromote": hitl_promote_meta,
    }


async def apply_run_feedback(
    session: AsyncSession,
    *,
    settings: Settings,
    sqlwork: SqlworkClient,
    user_id: int,
    run_id: int,
    workflow: AskWorkflow,
    action: str,
    session_id: int | None,
    question: str | None,
) -> dict[str, Any]:
    act = (action or "").strip().lower()
    if act not in ACTIONS:
        raise ValueError("action 须为 useful | useless | memory")

    row = await get_feedback(session, run_id=run_id, user_id=user_id)
    if row is None:
        row = AskRunFeedback(
            run_id=run_id,
            workflow_id=workflow.id,
            session_id=session_id,
            user_id=user_id,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
    elif session_id and not row.session_id:
        row.session_id = session_id
        await session.commit()

    if act == "useless":
        if row.useless_done:
            return {
                "alreadyProcessed": True,
                "action": act,
                "message": "已记录",
                "feedback": feedback_vo(row),
            }
        row.useless_done = True
        row.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
        return {
            "alreadyProcessed": False,
            "action": act,
            "message": "已记录",
            "feedback": feedback_vo(row),
        }

    # useful / memory：共享样本+知识写入；按钮各自标记
    flag = "useful_done" if act == "useful" else "memory_done"
    already_flag = bool(getattr(row, flag))
    write_meta: dict[str, Any] = {"alreadyProcessed": True}
    if not row.sample_id:
        write_meta = await _ensure_sample_and_knowledge(
            session,
            settings=settings,
            sqlwork=sqlwork,
            user_id=user_id,
            run_id=run_id,
            workflow=workflow,
            session_id=session_id or row.session_id,
            question=question,
            feedback=row,
        )
        await session.refresh(row)
    else:
        # 样本已有时仍尝试归并会话内未晋级的 HITL 卡片
        sid = session_id or row.session_id
        if sid:
            try:
                from dbc_askdata.knowledge.hitl_promote import promote_session_hitl_cards

                project = await load_project(session, workflow.project_id)
                nodes = (
                    workflow.nodes_json
                    if isinstance(workflow.nodes_json, dict)
                    else {"nodes": workflow.nodes_json}
                )
                write_meta["hitlPromote"] = await promote_session_hitl_cards(
                    session,
                    settings=settings,
                    user_id=user_id,
                    session_id=int(sid),
                    nodes_json=nodes if isinstance(nodes, dict) else {"nodes": []},
                    default_schema=project.source_schema if project else None,
                )
            except Exception:
                log.warning("HITL 卡片归并失败(已有样本) run_id=%s", run_id, exc_info=True)
                write_meta["hitlPromote"] = {"error": "HITL 卡片归并失败"}

    if not already_flag:
        setattr(row, flag, True)
        # B：有用与保存记忆等价写入；点任一也视另一可标为可再点幂等成功
        if act == "useful":
            row.useful_done = True
        else:
            row.memory_done = True
        row.updated_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)

    hitl_promote = write_meta.get("hitlPromote") if isinstance(write_meta, dict) else None
    msg = (
        "已记录样本并提交知识草稿（含 HITL 确认归并；需审批通过后生效）"
        if act in ("useful", "memory")
        else "已处理"
    )
    return {
        "alreadyProcessed": already_flag or bool(write_meta.get("alreadyProcessed")),
        "action": act,
        "message": msg,
        "sampleId": row.sample_id,
        "knowledge": write_meta.get("knowledge"),
        "hitlPromote": hitl_promote,
        "feedback": feedback_vo(row),
    }
