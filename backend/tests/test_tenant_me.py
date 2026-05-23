"""/me 端点测试 — 返回 tenant_name"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.security.dependencies import TenantAuthContext, get_current_tenant_user


def _fake_tenant_context():
    conn = AsyncMock()
    mapping = MagicMock()
    mapping.__getitem__ = lambda self, key: {"needs_onboarding": False, "name": "信安 PCB"}[key]
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    conn.execute = AsyncMock(return_value=result)

    return TenantAuthContext(
        tenant_id="t-001",
        tenant_slug="test-tenant",
        user_id="u-001",
        email="test@test.com",
        name="Test User",
        roles=["admin"],
        must_change_pwd=False,
        connection=conn,
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


class TestTenantMe:

    @pytest.mark.asyncio
    async def test_me_returns_tenant_name(self, client):
        resp = await client.get("/t/test-tenant/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tenant_name"] == "信安 PCB"
