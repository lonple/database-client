import httpx
import pytest

from dbc_askdata.clients.ada_memory import (
    AdaMemoryClient,
    merge_unit_detail,
    parse_unit_ref_id,
)
from dbc_askdata.config import Settings


def test_parse_unit_ref_id_uses_ref_id_not_list_id() -> None:
    assert parse_unit_ref_id({"id": 11, "refId": 42}) == 42
    assert parse_unit_ref_id({"id": 11, "ref_id": 42}) == 42
    assert parse_unit_ref_id({"id": 11}) is None


def test_merge_unit_detail_fills_body() -> None:
    hit = {"kind": "SLICE", "refId": 42, "title": "t", "summary": "s"}
    out = merge_unit_detail(hit, {"body": "完整切片正文", "title": "t"})
    assert out["body"] == "完整切片正文"
    assert out["summary"] == "s"


def _client_with_transport(handler) -> AdaMemoryClient:
    transport = httpx.MockTransport(handler)
    settings = Settings(ada_memory_base_url="http://memory.test")
    client = AdaMemoryClient(settings)
    client._client = lambda: httpx.AsyncClient(
        transport=transport, timeout=5.0, trust_env=False
    )
    return client


@pytest.mark.asyncio
async def test_search_hydrates_body_via_get_knowledge() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/api/search"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "units": [
                            {
                                "id": 11,
                                "kind": "SLICE",
                                "refId": 42,
                                "title": "员工表",
                                "summary": "简介而已",
                                "score": 0.9,
                            }
                        ]
                    },
                },
            )
        if path.endswith("/api/units/SLICE/42"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "kind": "SLICE",
                        "refId": 42,
                        "title": "员工表",
                        "summary": "简介而已",
                        "body": "emp 存在职员工，status=1 表示在职。",
                    },
                },
            )
        return httpx.Response(404, json={"code": 404, "message": path})

    client = _client_with_transport(handler)
    data = await client.search(
        query="emp", product_name="dbc产品", top_k=1, rewrite=False
    )
    units = data["units"]
    assert len(units) == 1
    assert units[0]["body"] == "emp 存在职员工，status=1 表示在职。"
    assert units[0]["refId"] == 42
    assert "/api/search" in "".join(calls)
    assert "/api/units/SLICE/42" in "".join(calls)
    assert "/api/units/SLICE/11" not in "".join(calls)


@pytest.mark.asyncio
async def test_search_can_skip_hydrate() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "units": [
                        {"id": 11, "kind": "SLICE", "refId": 42, "title": "t", "summary": "s"}
                    ]
                },
            },
        )

    client = _client_with_transport(handler)
    data = await client.search(
        query="emp",
        product_name="dbc产品",
        hydrate_body=False,
    )
    assert data["units"][0].get("body") is None
    assert all("/api/units/" not in p for p in calls)
