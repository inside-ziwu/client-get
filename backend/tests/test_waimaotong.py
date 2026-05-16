from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.errors import AppError, CredentialExpiredError
from app.integrations.collection import waimaotong as waimaotong_module
from app.integrations.collection.base import CollectionTask
from app.integrations.collection.waimaotong import WaiMaoTongCollectionProvider, _generate_sign
from app.services.collection_service import CollectionService
from tests.helpers import make_engine

CREDS = [
    {
        "cookie": "QIYE_TOKEN=abc; QIYE_SESS=def; _deviceId=device001; qiye_uid=123",
        "secret_key": "mysecret",
        "device_id": "device001",
        "is_active": True,
    }
]


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        body: dict,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.text = str(body)
        self.headers = headers or {}

    def json(self) -> dict:
        return self._body


def make_provider() -> WaiMaoTongCollectionProvider:
    return WaiMaoTongCollectionProvider(CREDS)


def make_task(params: dict | None = None) -> CollectionTask:
    return CollectionTask(
        id="task-waimaotong",
        keyword="pcb",
        source_types=["waimao_tong"],
        params=params or {"max_pages": 1},
    )


def search_response(items: list[dict], total: int | None = None) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "success": True,
            "data": {
                "pageableResult": {
                    "data": items,
                    "total": len(items) if total is None else total,
                }
            },
        },
    )


def detail_response(data: dict) -> FakeResponse:
    return FakeResponse(200, {"success": True, "data": data})


def contacts_response(content: list[dict]) -> FakeResponse:
    return FakeResponse(200, {"success": True, "data": {"content": content}})


async def collect_with_router(
    provider: WaiMaoTongCollectionProvider,
    task: CollectionTask,
    router,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(waimaotong_module.asyncio, "sleep", AsyncMock())
    provider._request_with_retry = AsyncMock(side_effect=router)
    return await provider.collect(task)


def test_sign_generation() -> None:
    sign, ts = _generate_sign("mysecret", {"product": "pcb", "page": "1"})

    assert len(sign) == 32
    assert sign == sign.upper()
    assert ts.isdigit()
    assert len(ts) == 13


async def test_collect_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider()

    async def router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
        if method == "POST" and url.endswith("/globalSearch/v1/search"):
            return search_response([{"id": "co-001", "name": "Test Corp", "country": "IN"}])
        if method == "GET" and url.endswith("/globalSearch/v1/detail/new"):
            return detail_response({"domain": "test.com", "industry": "Electronics"})
        if method == "POST" and url.endswith("/globalSearch/getContactPage"):
            return contacts_response(
                [
                    {
                        "id": "c1",
                        "name": "John",
                        "position": "CEO",
                        "emails": [{"address": "john@test.com"}],
                    }
                ]
            )
        raise AssertionError(f"unexpected request: {method} {url}")

    payload = await collect_with_router(provider, make_task(), router, monkeypatch)

    assert payload.companies[0]["target_table"] == "waimaotong_raw_companies"
    assert payload.companies[0]["collection_type"] == "direct_search"
    assert payload.companies[0]["country_iso3"] == "IND"
    assert payload.contacts[0]["email"] == "john@test.com"
    assert payload.contacts[0]["target_table"] == "waimaotong_raw_contacts"

    task_id = str(uuid4())
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            await CollectionService()._route_and_enqueue(
                conn,
                task_id=task_id,
                rows=[*payload.companies, *payload.contacts],
            )

            # 验证联系人写入 waimaotong_raw_contacts，不再被丢弃
            contacts_count = (
                await conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM waimaotong_raw_contacts wc
                        JOIN waimaotong_raw_companies w ON w.id = wc.raw_company_id
                        WHERE w.source_id = :source_id
                        """
                    ),
                    {"source_id": "co-001"},
                )
            ).scalar_one()
            assert contacts_count >= 1, "联系人应该写入 waimaotong_raw_contacts"

            # 验证字段映射正确
            contact_row = (
                await conn.execute(
                    text(
                        """
                        SELECT wc.name, wc.email, wc.raw_company_id, w.source_id
                        FROM waimaotong_raw_contacts wc
                        JOIN waimaotong_raw_companies w ON w.id = wc.raw_company_id
                        WHERE w.source_id = :source_id
                        LIMIT 1
                        """
                    ),
                    {"source_id": "co-001"},
                )
            ).mappings().one()
            assert contact_row["email"] is not None
            assert contact_row["raw_company_id"] is not None
            assert contact_row["source_id"] == "co-001"
    finally:
        await engine.dispose()


async def test_401_raises_credential_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider()

    async def router(_client, _method: str, _url: str, **_kwargs) -> FakeResponse:
        return FakeResponse(401, {"message": "Unauthorized"})

    with pytest.raises(CredentialExpiredError):
        await collect_with_router(provider, make_task(), router, monkeypatch)


async def test_success_false_raises_credential_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider()

    async def router(_client, _method: str, _url: str, **_kwargs) -> FakeResponse:
        return FakeResponse(200, {"success": False, "message": "Token invalid"})

    with pytest.raises(CredentialExpiredError):
        await collect_with_router(provider, make_task(), router, monkeypatch)


async def test_detail_failure_company_still_saved(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider()

    async def router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
        if method == "POST" and url.endswith("/globalSearch/v1/search"):
            return search_response([{"id": "co-001", "name": "Test Corp", "country": "IN"}])
        if method == "GET" and url.endswith("/globalSearch/v1/detail/new"):
            return FakeResponse(500, {"message": "server error"})
        if method == "POST" and url.endswith("/globalSearch/getContactPage"):
            return contacts_response([])
        raise AssertionError(f"unexpected request: {method} {url}")

    payload = await collect_with_router(provider, make_task(), router, monkeypatch)

    assert len(payload.companies) == 1
    assert payload.companies[0]["industry"] is None


async def test_contact_without_email_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider()

    async def router(_client, method: str, url: str, **_kwargs) -> FakeResponse:
        if method == "POST" and url.endswith("/globalSearch/v1/search"):
            return search_response([{"id": "co-001", "name": "Test Corp", "country": "IN"}])
        if method == "GET" and url.endswith("/globalSearch/v1/detail/new"):
            return detail_response({"domain": "test.com", "industry": "Electronics"})
        if method == "POST" and url.endswith("/globalSearch/getContactPage"):
            return contacts_response(
                [{"id": "c1", "name": "John", "position": "CEO", "emails": []}]
            )
        raise AssertionError(f"unexpected request: {method} {url}")

    payload = await collect_with_router(provider, make_task(), router, monkeypatch)

    assert len(payload.contacts) == 1
    assert payload.contacts[0]["email"] is None
    assert payload.contacts[0]["source_contact_id"] == "c1"


async def test_no_credential_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = WaiMaoTongCollectionProvider([])
    monkeypatch.setattr(waimaotong_module.asyncio, "sleep", AsyncMock())

    with pytest.raises(AppError) as exc_info:
        await provider.collect(make_task())

    assert exc_info.value.code == "NO_CREDENTIAL"
