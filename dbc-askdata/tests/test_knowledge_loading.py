from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from dbc_askdata.config import Settings
from dbc_askdata.knowledge import general_knowledge as knowledge


@pytest.fixture
def dependencies(monkeypatch):
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock()
    session_factory.return_value.__aexit__ = AsyncMock()
    monkeypatch.setattr(knowledge, "SessionLocal", session_factory)
    bindings = AsyncMock(return_value=[3])
    monkeypatch.setattr(knowledge, "list_general_document_ids", bindings)
    redis = MagicMock(get_json=AsyncMock(return_value=None), set_json=AsyncMock())
    monkeypatch.setattr("dbc_askdata.redis.client.get_redis", lambda: redis)
    client = MagicMock(search=AsyncMock(), get_document=AsyncMock())
    monkeypatch.setattr(knowledge, "AdaMemoryClient", lambda _: client)
    return bindings, redis, client


async def search():
    return await knowledge.search_db_general_knowledge(
        Settings(), connection_id=1, database="postgres", schema="company"
    )


async def test_search_is_limited_to_bound_documents(dependencies):
    bindings, redis, client = dependencies
    client.get_document.return_value = {
        "id": 3, "status": "PUBLISHED", "body": "published rules", "slices": []
    }
    result = await search()
    assert result["body"] == "published rules"
    assert result["kind"] == "DOCUMENT"
    assert result["refId"] == result["documentId"] == 3
    client.get_document.assert_awaited_once_with(3)
    client.search.assert_not_awaited()
    redis.get_json.assert_not_awaited()
    redis.set_json.assert_not_awaited()
    assert bindings.call_args.kwargs["schema"] == "company"


async def test_unpublished_document_has_actionable_reason(dependencies):
    _, redis, client = dependencies
    client.get_document.return_value = {"title": "company", "status": "DRAFT", "slices": []}
    result = await search()
    assert "尚未发布" in result["reason"]
    assert knowledge.unwrap_general_knowledge_result(result)[0] is None
    assert "切片" not in result["reason"]
    redis.set_json.assert_not_awaited()


async def test_search_error_is_not_reported_as_empty_result(dependencies):
    _, redis, client = dependencies
    client.get_document.side_effect = HTTPException(401, "expired")
    with pytest.raises(HTTPException):
        await search()
    redis.set_json.assert_not_awaited()


async def test_cached_miss_keeps_reason(dependencies):
    _, redis, client = dependencies
    redis.get_json.return_value = {"__miss__": True, "reason": "尚未发布"}
    result = await knowledge.search_catalog_directory_knowledge(
        Settings(), connection_id=1, database="postgres", schema="company"
    )
    assert result["reason"] == "尚未发布"
    client.search.assert_not_awaited()


async def test_original_updates_are_read_without_stale_slice_cache(dependencies):
    _, redis, client = dependencies
    redis.get_json.return_value = {"__miss__": True}
    client.get_document.side_effect = [
        {"status": "PUBLISHED", "body": "old original", "slices": [{"body": "stale slice"}]},
        {"status": "PUBLISHED", "body": "updated original", "slices": []},
    ]
    assert (await search())["body"] == "old original"
    assert (await search())["body"] == "updated original"
    redis.get_json.assert_not_awaited()
    client.search.assert_not_awaited()


async def test_missing_binding_does_not_search_other_scopes(dependencies):
    bindings, _, client = dependencies
    bindings.return_value = []
    result = await search()
    assert "尚未绑定" in result["reason"]
    client.get_document.assert_not_awaited()
    client.search.assert_not_awaited()


async def test_empty_original_does_not_use_slice_body_or_summary(dependencies):
    _, _, client = dependencies
    client.get_document.return_value = {
        "status": "PUBLISHED", "body": " ", "summary": "summary",
        "slices": [{"body": "slice body"}],
    }
    result = await search()
    assert "正文为空" in result["reason"]
    assert knowledge.unwrap_general_knowledge_result(result)[0] is None


async def test_missing_document_skips_to_next_published_original(dependencies):
    bindings, _, client = dependencies
    bindings.return_value = [3, 4]
    client.get_document.side_effect = [HTTPException(404, "missing"), {
        "status": "PUBLISHED", "body": "available original", "id": 4,
    }]
    result = await search()
    assert result["documentId"] == 4
    assert result["body"] == "available original"
