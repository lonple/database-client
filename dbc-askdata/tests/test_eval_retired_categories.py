import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from dbc_askdata.api.eval_routes import create_custom_case, patch_case
from dbc_askdata.api.schemas import EvalCaseCreateRequest, EvalCasePatchRequest
from dbc_askdata.eval.categories import REMOVED_CATEGORIES
from dbc_askdata.eval.templates import import_template_cases_from_jsonl


@pytest.mark.parametrize("category", sorted(REMOVED_CATEGORIES))
async def test_retired_categories_cannot_be_created_or_patched(category):
    user = SimpleNamespace(user_id=7)
    project = SimpleNamespace(id=1, owner_user_id=7)
    case = SimpleNamespace(scope="PROJECT_CUSTOM", project_id=1)
    session = AsyncMock()
    session.get.return_value = project
    with pytest.raises(HTTPException) as exc:
        await create_custom_case(
            1, EvalCaseCreateRequest(category=f" {category} ", question="test"), user, session
        )
    assert exc.value.status_code == 400
    session.commit.assert_not_awaited()

    session.get.side_effect = [case, project]
    with pytest.raises(HTTPException) as exc:
        await patch_case(1, EvalCasePatchRequest(category=category), user, session)
    assert exc.value.status_code == 400
    session.commit.assert_not_awaited()


async def test_old_seed_files_skip_retired_categories(tmp_path):
    rows = [
        {"case_key": f"OLD_{category}", "category": category,
         "question": "old", "compare_mode": "order_by"}
        for category in sorted(REMOVED_CATEGORIES)
    ]
    (tmp_path / "05_legacy.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    session = AsyncMock()
    assert await import_template_cases_from_jsonl(
        session, template=SimpleNamespace(id=1), cases_dir=tmp_path
    ) == (0, 2)
    session.execute.assert_not_awaited()
