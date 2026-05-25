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


# ── U4: 服务层 send_test_email ──


from app.services.tenant_messaging_service import TenantMessagingService


def _mock_conn_with_queries(query_results: dict):
    conn = AsyncMock()

    async def _execute(stmt, params=None):
        sql = str(stmt)
        for keyword, result_value in query_results.items():
            if keyword in sql:
                result = MagicMock()
                if isinstance(result_value, dict):
                    mapping = MagicMock()
                    mapping.__getitem__ = lambda self, key, rv=result_value: rv[key]
                    mapping.get = lambda key, default=None, rv=result_value: rv.get(key, default)
                    result.mappings = MagicMock(return_value=MagicMock(first=MagicMock(return_value=mapping)))
                elif result_value is None:
                    result.mappings = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
                    result.scalar_one_or_none = MagicMock(return_value=None)
                else:
                    result.scalar_one_or_none = MagicMock(return_value=result_value)
                return result
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        return result

    conn.execute = AsyncMock(side_effect=_execute)
    return conn


class TestSendTestEmail:

    @pytest.mark.asyncio
    @patch("app.services.tenant_messaging_service.EngageLabClient")
    async def test_success(self, MockEngageLab):
        mock_el = AsyncMock()
        mock_el.send_email = AsyncMock(return_value={"engagelab_message_id": "msg-123"})
        MockEngageLab.return_value = mock_el

        conn = _mock_conn_with_queries({
            "test_email FROM users": "recipient@test.com",
            "FROM email_templates": {
                "id": "tpl-001", "subject": "Hello {{company_name}}",
                "body_html": "<p>Hi {{contact_name}}</p>", "body_text": "Hi {{contact_name}}",
            },
            "FROM domain_warmup_status": {"sender_email": "noreply@example.com"},
        })
        svc = TenantMessagingService()
        result = await svc.send_test_email(conn, "t-001", "u-001", "tpl-001")

        assert result["success"] is True
        assert result["test_email"] == "recipient@test.com"
        mock_el.send_email.assert_called_once()
        call_payload = mock_el.send_email.call_args[0][0]
        assert call_payload["to_email"] == "recipient@test.com"
        assert call_payload["from_email"] == "noreply@example.com"
        assert "示例公司" in call_payload["subject"]

    @pytest.mark.asyncio
    async def test_no_test_email_raises_422(self):
        conn = _mock_conn_with_queries({"test_email FROM users": None})
        svc = TenantMessagingService()
        with pytest.raises(AppError) as exc_info:
            await svc.send_test_email(conn, "t-001", "u-001", "tpl-001")
        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "TEST_EMAIL_NOT_SET"

    @pytest.mark.asyncio
    async def test_no_domain_raises_422(self):
        conn = _mock_conn_with_queries({
            "test_email FROM users": "recipient@test.com",
            "FROM email_templates": {
                "id": "tpl-001", "subject": "Test", "body_html": "<p>Test</p>", "body_text": "Test",
            },
            "FROM domain_warmup_status": None,
        })
        svc = TenantMessagingService()
        with pytest.raises(AppError) as exc_info:
            await svc.send_test_email(conn, "t-001", "u-001", "tpl-001")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_template_not_found_raises_404(self):
        conn = _mock_conn_with_queries({
            "test_email FROM users": "recipient@test.com",
            "FROM email_templates": None,
        })
        svc = TenantMessagingService()
        with pytest.raises(AppError) as exc_info:
            await svc.send_test_email(conn, "t-001", "u-001", "tpl-001")
        assert exc_info.value.status_code == 404
