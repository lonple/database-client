from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dbc_askdata.config import Settings
from dbc_askdata.eval.categories import REMOVED_CATEGORIES
from dbc_askdata.eval.cleanup import purge_removed_categories
from dbc_askdata.eval.models import EvalCase, EvalTemplate

log = logging.getLogger(__name__)

TEMPLATE_CODE = "company_eval_v2"
TEMPLATE_NAME = "演示公司测评模板 v2"
TEMPLATE_VERSION = "v2"


def resolve_cases_dir(settings: Settings) -> Path | None:
    raw = (settings.eval_cases_dir or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        # 相对仓库根：dbc-askdata/src/dbc_askdata/eval/templates.py → parents[4]=repo
        repo = Path(__file__).resolve().parents[4]
        path = (repo / path).resolve()
    return path if path.is_dir() else None


async def ensure_builtin_template(session: AsyncSession) -> EvalTemplate:
    row = (
        await session.execute(select(EvalTemplate).where(EvalTemplate.code == TEMPLATE_CODE))
    ).scalar_one_or_none()
    if row is None:
        row = EvalTemplate(
            code=TEMPLATE_CODE,
            name=TEMPLATE_NAME,
            version=TEMPLATE_VERSION,
            remark="演示公司 company_eval_v2；单表、多表关联及复杂治理测评",
            enabled=True,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        log.info("已创建测评模板 code=%s id=%s", TEMPLATE_CODE, row.id)
    return row


async def import_template_cases_from_jsonl(
    session: AsyncSession,
    *,
    template: EvalTemplate,
    cases_dir: Path,
) -> tuple[int, int]:
    """按 case_key upsert 模板用例。返回 (inserted_or_updated, skipped)。"""
    files = sorted(cases_dir.glob("*.jsonl"))
    # smoke 手写演示集，case_key 与正式编号冲突（如 TPL_GOV_B_001），导入时跳过
    files = [fp for fp in files if fp.name != "smoke.jsonl"]
    if not files:
        log.warning("测评用例目录无 jsonl: %s", cases_dir)
        return 0, 0

    upserted = 0
    skipped = 0
    for fp in files:
        for line_no, line in enumerate(fp.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as ex:
                log.warning("跳过非法 JSON %s:%s", fp.name, line_no, exc_info=True)
                skipped += 1
                continue
            case_key = str(raw.get("case_key") or "").strip()
            question = str(raw.get("question") or "").strip()
            compare_mode = str(raw.get("compare_mode") or "").strip()
            category = str(raw.get("category") or "").strip()
            if not case_key or not question or not compare_mode or not category or category in REMOVED_CATEGORIES:
                skipped += 1
                continue
            spec = raw.get("compare_spec") if "compare_spec" in raw else raw.get("compare_spec_json")
            if not isinstance(spec, dict):
                spec = {}
            replies = raw.get("hitl_replies")
            if replies is None:
                replies = raw.get("hitl_replies_json")
            tags = raw.get("tags")
            if tags is None:
                tags = raw.get("tags_json")

            existing = (
                await session.execute(select(EvalCase).where(EvalCase.case_key == case_key))
            ).scalar_one_or_none()
            if existing is None:
                session.add(
                    EvalCase(
                        case_key=case_key,
                        scope="TEMPLATE",
                        template_id=template.id,
                        project_id=None,
                        category=category,
                        govern_subtype=raw.get("govern_subtype"),
                        question=question,
                        expect_sql=raw.get("expect_sql"),
                        compare_mode=compare_mode,
                        compare_spec_json=spec,
                        hitl_replies_json=replies,
                        tags_json=tags,
                        difficulty=raw.get("difficulty"),
                        enabled=bool(raw.get("enabled", True)),
                    )
                )
            else:
                if existing.scope != "TEMPLATE":
                    log.warning("case_key=%s 已存在非模板 scope=%s，跳过", case_key, existing.scope)
                    skipped += 1
                    continue
                existing.template_id = template.id
                existing.category = category
                existing.govern_subtype = raw.get("govern_subtype")
                existing.question = question
                existing.expect_sql = raw.get("expect_sql")
                existing.compare_mode = compare_mode
                existing.compare_spec_json = spec
                existing.hitl_replies_json = replies
                existing.tags_json = tags
                if raw.get("difficulty") is not None:
                    existing.difficulty = raw.get("difficulty")
                existing.enabled = bool(raw.get("enabled", True))
            upserted += 1
        await session.commit()
    log.info("测评用例导入完成 dir=%s upserted=%s skipped=%s", cases_dir, upserted, skipped)
    return upserted, skipped


async def seed_eval_templates(session: AsyncSession, settings: Settings) -> None:
    result = await purge_removed_categories(session)
    await session.commit()
    if result["cases"] or result["taskCases"]:
        log.info("已清理下线测评分类: %s", result)
    template = await ensure_builtin_template(session)
    cases_dir = resolve_cases_dir(settings)
    if cases_dir is None:
        log.info(
            "未配置有效 DBC_ASKDATA_EVAL_CASES_DIR，跳过用例导入（当前=%r）",
            settings.eval_cases_dir,
        )
        return
    await import_template_cases_from_jsonl(session, template=template, cases_dir=cases_dir)
