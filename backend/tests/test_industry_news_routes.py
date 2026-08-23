from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.pools import get_connection
from app.main import create_app
from app.security.dependencies import (
    PlatformAuthContext,
    TenantAuthContext,
    get_current_platform_user,
    get_current_tenant_user,
)


def _fake_tenant():
    return TenantAuthContext(
        tenant_id="t-001",
        tenant_slug="acme",
        user_id="u-001",
        email="u@test.com",
        name="U",
        roles=["viewer"],
        must_change_pwd=False,
        connection=AsyncMock(),
    )


def _fake_platform():
    return PlatformAuthContext(
        platform_user_id="pu-001",
        email="admin@test.com",
        name="Admin",
        roles=["super_admin"],
        connection=AsyncMock(),
    )


async def _fake_connection():
    yield AsyncMock()


@pytest.fixture
async def tenant_client():
    app = create_app()
    app.dependency_overrides[get_current_tenant_user] = _fake_tenant
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client():
    app = create_app()
    app.dependency_overrides[get_current_platform_user] = _fake_platform
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def noauth_client():
    app = create_app()
    app.dependency_overrides[get_connection] = _fake_connection
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


ITEM_UUID = "01a02e44-eeef-7257-9ed6-f809ac615de1"
SOURCE_UUID = "01a02e44-d7d8-7cc1-9b67-5b5b7f06bba1"


@pytest.mark.asyncio
async def test_tenant_and_admin_require_auth(noauth_client):
    tenant = await noauth_client.get("/t/acme/api/v1/industry-news/items")
    admin = await noauth_client.get("/admin/api/v1/industry-news-sources")
    fetch = await noauth_client.post("/admin/api/v1/industry-news-sources/fetch")
    assert tenant.status_code == 401
    assert admin.status_code == 401
    assert fetch.status_code == 401


@pytest.mark.asyncio
async def test_tenant_list_passes_filters_and_has_more(tenant_client, monkeypatch):
    mock = AsyncMock(return_value=([{"id": "i1"}], 120))
    monkeypatch.setattr("app.api.tenant.industry_news.service.list_items", mock)
    resp = await tenant_client.get(
        "/t/acme/api/v1/industry-news/items",
        params=(
            ("category[]", "A"),
            ("category[]", "B"),
            ("source_id[]", SOURCE_UUID),
            ("unread_only", "true"),
            ("page", "1"),
            ("page_size", "50"),
        ),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["total"] == 120
    assert body["pagination"]["has_more"] is True
    kwargs = mock.await_args.kwargs
    assert kwargs["categories"] == ["A", "B"]
    assert kwargs["source_ids"] == [SOURCE_UUID]
    assert kwargs["lang"] is None
    assert kwargs["unread_only"] is True
    assert kwargs["page"] == 1
    assert kwargs["page_size"] == 50
    assert kwargs["tenant_id"] == "t-001"
    assert kwargs["user_id"] == "u-001"
    assert kwargs["instance_id"] == "default"


@pytest.mark.asyncio
async def test_tenant_list_defaults_and_page_size_cap(tenant_client, monkeypatch):
    mock = AsyncMock(return_value=([], 0))
    monkeypatch.setattr("app.api.tenant.industry_news.service.list_items", mock)
    resp = await tenant_client.get("/t/acme/api/v1/industry-news/items")
    assert resp.status_code == 200
    assert resp.json()["pagination"] == {"cursor": None, "has_more": False, "total": 0}
    kwargs = mock.await_args.kwargs
    assert kwargs["categories"] is None
    assert kwargs["source_ids"] is None
    assert kwargs["unread_only"] is False
    assert (kwargs["page"], kwargs["page_size"]) == (1, 50)

    too_big = await tenant_client.get(
        "/t/acme/api/v1/industry-news/items", params={"page_size": 101}
    )
    assert too_big.status_code == 422


@pytest.mark.asyncio
async def test_tenant_filters_endpoint(tenant_client, monkeypatch):
    payload = {"categories": [], "sources": [], "langs": [], "has_sources": False}
    monkeypatch.setattr(
        "app.api.tenant.industry_news.service.list_filter_options",
        AsyncMock(return_value=payload),
    )
    resp = await tenant_client.get("/t/acme/api/v1/industry-news/filters")
    assert resp.status_code == 200
    assert resp.json() == {"data": payload}


@pytest.mark.asyncio
async def test_admin_list_returns_plain_array(admin_client, monkeypatch):
    rows = [{"id": "s1", "code": "pcea", "is_active": True, "error_count": 0}]
    mock = AsyncMock(return_value=rows)
    monkeypatch.setattr("app.api.admin.industry_news_sources.service.list_sources", mock)
    resp = await admin_client.get("/admin/api/v1/industry-news-sources")
    assert resp.status_code == 200
    assert resp.json() == {"data": rows}
    assert mock.await_args.args[1] == "default"


@pytest.mark.asyncio
async def test_admin_patch_requires_boolean_payload(admin_client):
    resp = await admin_client.patch(
        f"/admin/api/v1/industry-news-sources/{SOURCE_UUID}", json={"is_active": "maybe"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_malformed_ids_are_422_not_500(admin_client, tenant_client, monkeypatch):
    """非 UUID 的 id 在路由层被拒绝，不会把 asyncpg DataError 漏成 500。"""
    monkeypatch.setattr(
        "app.api.admin.industry_news_sources.service.set_source_active", AsyncMock()
    )
    monkeypatch.setattr("app.api.tenant.industry_news.service.mark_read", AsyncMock())
    monkeypatch.setattr(
        "app.api.tenant.industry_news.service.list_items", AsyncMock(return_value=([], 0))
    )
    bad_patch = await admin_client.patch(
        "/admin/api/v1/industry-news-sources/src-001", json={"is_active": False}
    )
    bad_read = await tenant_client.post("/t/acme/api/v1/industry-news/items/missing/read")
    bad_filter = await tenant_client.get(
        "/t/acme/api/v1/industry-news/items", params={"source_id[]": "abc"}
    )
    assert bad_patch.status_code == 422
    assert bad_read.status_code == 422
    assert bad_filter.status_code == 422
    assert bad_read.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_mark_read_idempotent_and_404(tenant_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.tenant.industry_news.service.mark_read",
        AsyncMock(return_value={"item_id": "i1", "is_read": True}),
    )
    ok = await tenant_client.post(f"/t/acme/api/v1/industry-news/items/{ITEM_UUID}/read")
    assert ok.status_code == 200
    assert ok.json() == {"data": {"item_id": "i1", "is_read": True}}

    from app.core.errors import AppError

    monkeypatch.setattr(
        "app.api.tenant.industry_news.service.mark_read",
        AsyncMock(
            side_effect=AppError(code="NOT_FOUND", message="动态不存在或无权访问", status_code=404)
        ),
    )
    missing = await tenant_client.post(f"/t/acme/api/v1/industry-news/items/{ITEM_UUID}/read")
    assert missing.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,status",
    [
        ({"triggered": True}, 202),
        ({"triggered": False, "reason": "in_progress"}, 202),
        ({"triggered": False, "reason": "no_sources"}, 202),
    ],
)
async def test_admin_fetch_returns_202(admin_client, monkeypatch, payload, status):
    monkeypatch.setattr(
        "app.api.admin.industry_news_sources.trigger_fetch",
        AsyncMock(return_value=payload),
    )
    resp = await admin_client.post("/admin/api/v1/industry-news-sources/fetch")
    assert resp.status_code == status
    assert resp.json() == {"data": payload}


@pytest.mark.asyncio
async def test_admin_patch_other_instance_404(admin_client, monkeypatch):
    from app.core.errors import AppError

    monkeypatch.setattr(
        "app.api.admin.industry_news_sources.service.set_source_active",
        AsyncMock(
            side_effect=AppError(
                code="NOT_FOUND", message="动态源不存在或无权访问", status_code=404
            )
        ),
    )
    resp = await admin_client.patch(
        f"/admin/api/v1/industry-news-sources/{SOURCE_UUID}",
        json={"is_active": False},
    )
    assert resp.status_code == 404
