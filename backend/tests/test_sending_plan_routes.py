"""发送计划路由层测试"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.security.dependencies import TenantAuthContext, get_current_tenant_user


def _fake_tenant_context():
    return TenantAuthContext(
        tenant_id="t-001",
        tenant_slug="test-tenant",
        user_id="u-001",
        email="test@test.com",
        name="Test",
        roles=["admin"],
        must_change_pwd=False,
        connection=AsyncMock(),
    )


@pytest.fixture
def app():
    application = create_app()
    ctx = _fake_tenant_context()
    application.dependency_overrides[get_current_tenant_user] = lambda: ctx
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListSendingPlansRoute:
    """U5: 路由层筛选分页参数透传"""

    @pytest.mark.asyncio
    async def test_passes_query_params_to_service(self, client):
        with patch(
            "app.api.tenant.messaging.service.list_sending_plans",
            new_callable=AsyncMock,
            return_value={"items": [], "total": 0},
        ) as mock_list:
            resp = await client.get(
                "/t/test-tenant/api/v1/sending-plans",
                params={
                    "status": "draft",
                    "keyword": "巴西",
                    "date_from": "2026-05-01",
                    "date_to": "2026-05-23",
                    "page": "1",
                    "page_size": "20",
                },
            )

            assert resp.status_code == 200
            mock_list.assert_called_once()
            call_kwargs = mock_list.call_args
            assert call_kwargs.kwargs["status"] == "draft"
            assert call_kwargs.kwargs["keyword"] == "巴西"
            assert call_kwargs.kwargs["date_from"] == "2026-05-01"
            assert call_kwargs.kwargs["date_to"] == "2026-05-23"
            assert call_kwargs.kwargs["page"] == 1
            assert call_kwargs.kwargs["page_size"] == 20

    @pytest.mark.asyncio
    async def test_no_params_still_works(self, client):
        with patch(
            "app.api.tenant.messaging.service.list_sending_plans",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get("/t/test-tenant/api/v1/sending-plans")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_paginated_response_format(self, client):
        with patch(
            "app.api.tenant.messaging.service.list_sending_plans",
            new_callable=AsyncMock,
            return_value={"items": [{"id": "p1", "name": "test"}], "total": 15},
        ):
            resp = await client.get(
                "/t/test-tenant/api/v1/sending-plans",
                params={"page": "1", "page_size": "10"},
            )
            body = resp.json()
            assert body["pagination"]["total"] == 15
            assert len(body["data"]) == 1
