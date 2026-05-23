"""域名 CRUD 路由层测试 — PATCH/DELETE 端点"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.errors import AppError
from app.main import create_app
from app.security.dependencies import PlatformAuthContext, get_current_platform_user


def _fake_platform_context():
    return PlatformAuthContext(
        platform_user_id="pu-001",
        email="admin@test.com",
        name="Admin",
        roles=["admin"],
        connection=AsyncMock(),
    )


@pytest.fixture
def app():
    application = create_app()
    ctx = _fake_platform_context()
    application.dependency_overrides[get_current_platform_user] = lambda: ctx
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestPatchDomainRoute:

    @pytest.mark.asyncio
    async def test_patch_domain_success(self, client):
        mock_domain = {"id": "d-001", "sender_email": "new@test.com"}
        with patch(
            "app.api.admin.config.service.update_tenant_domain",
            new_callable=AsyncMock,
            return_value=mock_domain,
        ):
            resp = await client.patch(
                "/admin/api/v1/tenants/t-001/domains/d-001",
                json={"sender_email": "new@test.com"},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["sender_email"] == "new@test.com"

    @pytest.mark.asyncio
    async def test_patch_domain_not_found(self, client):
        with patch(
            "app.api.admin.config.service.update_tenant_domain",
            new_callable=AsyncMock,
            side_effect=AppError(code="NOT_FOUND", message="租户域名不存在", status_code=404),
        ):
            resp = await client.patch(
                "/admin/api/v1/tenants/t-001/domains/d-999",
                json={"sender_email": "a@b.com"},
            )
            assert resp.status_code == 404


class TestDeleteDomainRoute:

    @pytest.mark.asyncio
    async def test_delete_domain_success(self, client):
        with patch(
            "app.api.admin.config.service.delete_tenant_domain",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.delete("/admin/api/v1/tenants/t-001/domains/d-001")
            assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_domain_conflict(self, client):
        with patch(
            "app.api.admin.config.service.delete_tenant_domain",
            new_callable=AsyncMock,
            side_effect=AppError(code="CONFLICT", message="该域名存在关联数据，无法删除", status_code=409),
        ):
            resp = await client.delete("/admin/api/v1/tenants/t-001/domains/d-001")
            assert resp.status_code == 409
