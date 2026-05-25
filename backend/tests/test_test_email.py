"""测试邮箱功能测试 — 服务层 + 路由"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.errors import AppError
from app.main import create_app
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.tenant_team_service import TenantTeamService


# ── U2: 服务层 update_test_email / get_test_email ──


def _mock_conn(scalar_return=...):
    conn = AsyncMock()
    if scalar_return is not ...:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=scalar_return)
        conn.execute = AsyncMock(return_value=result)
    return conn


class TestUpdateTestEmail:

    @pytest.mark.asyncio
    async def test_success(self):
        conn = _mock_conn(scalar_return=None)
        svc = TenantTeamService()
        await svc.update_test_email(conn, "u-001", "test@example.com")
        conn.execute.assert_called_once()
        sql_text = str(conn.execute.call_args[0][0])
        assert "test_email" in sql_text

    @pytest.mark.asyncio
    async def test_invalid_email_raises_422(self):
        conn = _mock_conn(scalar_return=None)
        svc = TenantTeamService()
        with pytest.raises(AppError) as exc_info:
            await svc.update_test_email(conn, "u-001", "not-an-email")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_email_raises_422(self):
        conn = _mock_conn(scalar_return=None)
        svc = TenantTeamService()
        with pytest.raises(AppError) as exc_info:
            await svc.update_test_email(conn, "u-001", "")
        assert exc_info.value.status_code == 422


class TestGetTestEmail:

    @pytest.mark.asyncio
    async def test_returns_email(self):
        conn = _mock_conn("test@example.com")
        svc = TenantTeamService()
        result = await svc.get_test_email(conn, "u-001")
        assert result == "test@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_set(self):
        conn = _mock_conn(None)
        svc = TenantTeamService()
        result = await svc.get_test_email(conn, "u-001")
        assert result is None


# ── U3: 路由 PATCH /auth/me/test-email ──


def _fake_tenant_context():
    conn = AsyncMock()
    conn.execute = AsyncMock()
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


class TestUpdateTestEmailRoute:

    @pytest.mark.asyncio
    async def test_success(self, client):
        resp = await client.patch(
            "/t/test-tenant/api/v1/auth/me/test-email",
            json={"test_email": "a@b.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["test_email"] == "a@b.com"

    @pytest.mark.asyncio
    async def test_invalid_email_returns_422(self, client):
        resp = await client.patch(
            "/t/test-tenant/api/v1/auth/me/test-email",
            json={"test_email": "bad"},
        )
        assert resp.status_code == 422
