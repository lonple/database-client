from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.eval.categories import REMOVED_CATEGORIES
from dbc_askdata.eval.metrics import aggregate_metrics
from dbc_askdata.eval.models import EvalCase, EvalTask, EvalTaskCase


async def purge_removed_categories(session: AsyncSession) -> dict[str, int]:
    """Delete retired cases and snapshots, then rebuild affected task metrics.

    The caller owns the transaction. Task records and their other cases remain.
    Match legacy snapshots without a category by case ID or case key as well.
    """
    removed = select(EvalCase.id).where(EvalCase.category.in_(REMOVED_CATEGORIES))
    removed_keys = select(EvalCase.case_key).where(EvalCase.category.in_(REMOVED_CATEGORIES))
    deleted_task_ids = (
        (await session.execute(
            delete(EvalTaskCase).where(or_(
                EvalTaskCase.category.in_(REMOVED_CATEGORIES),
                EvalTaskCase.case_id.in_(removed),
                EvalTaskCase.case_key.in_(removed_keys),
            )).returning(EvalTaskCase.task_id)
        )).scalars().all()
    )
    task_ids = set(deleted_task_ids)
    deleted_cases = (await session.execute(
        delete(EvalCase).where(EvalCase.category.in_(REMOVED_CATEGORIES)).returning(EvalCase.id)
    )).scalars().all()
    for task_id in sorted(task_ids):
        task = await session.get(EvalTask, task_id)
        cases = (await session.execute(
            select(EvalTaskCase).where(EvalTaskCase.task_id == task_id)
        )).scalars().all()
        metrics = aggregate_metrics(cases)
        if task.started_at is not None and task.finished_at is not None:
            metrics["elapsedMs"] = max(
                0, int((task.finished_at - task.started_at).total_seconds() * 1000)
            )
        task.metrics_json = metrics
    await session.flush()
    return {"cases": len(deleted_cases), "taskCases": len(deleted_task_ids), "tasks": len(task_ids)}
