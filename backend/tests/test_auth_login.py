from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.pools import get_connection
from app.main import create_app


@pytest.fixture
def app():
    application = create_app()
    application.dependency_overrides[get_connection] = lambda: AsyncMock()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestLoginRoute:
    @pytest.mark.asyncio
    async def test_login_sets_refresh_cookie(self, client):
        with patch(
            "app.services.auth_service.AuthService.platform_login",
            new_callable=AsyncMock,
            return_value=("access-token-value", "refresh-token-value"),
        ):
            resp = await client.post(
                "/admin/api/v1/auth/login",
                json={"email": "admin@test.com", "password": "test-password-123"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["access_token"] == "access-token-value"
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "httponly" in set_cookie.lower()
        assert "path=/admin/api/v1/auth" in set_cookie.lower()


def _active_platform_user():
    """返回一个活跃的 platform_user mock 行"""
    return {
        "id": "aaaaaaaa-1111-2222-3333-444444444444",
        "email": "admin@test.com",
        "password_hash": "$2b$12$dummy",
        "name": "Admin",
        "status": "active",
        "failed_login_count": 0,
        "locked_until": None,
    }


def _active_tenant_user():
    """返回一个活跃的 tenant user mock 行"""
    return {
        "id": "bbbbbbbb-1111-2222-3333-444444444444",
        "email": "user@test.com",
        "password_hash": "$2b$12$dummy",
        "name": "User",
        "status": "active",
        "must_change_pwd": False,
        "failed_login_count": 0,
        "locked_until": None,
        "tenant_id": "cccccccc-1111-2222-3333-444444444444",
        "slug": "test-tenant",
        "tenant_status": "active",
    }


class TestPlatformLoginInstanceFilter:
    """U9: platform_login 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_sql_includes_instance_id_param(self):
        """platform_login 的 SQL execute 调用参数包含 instance_id"""
        from app.services.auth_service import AuthService

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = _active_platform_user()

        mock_conn = AsyncMock()
        mock_conn.execute.return_value = mock_result

        svc = AuthService()
        with patch("app.services.auth_service.verify_password", return_value=True), \
             patch("app.services.auth_service.get_engine"):
            await svc.platform_login(mock_conn, "admin@test.com", "password123")

        # 第一次 execute 调用是 SELECT 查询
        first_call = mock_conn.execute.call_args_list[0]
        params = first_call[0][1]  # 位置参数的第二个是参数字典
        assert "instance_id" in params

    @pytest.mark.asyncio
    async def test_instance_id_mismatch_returns_none(self):
        """管理员存在但 instance_id 不匹配 → conn.execute 返回 None → 401"""
        from app.core.errors import AppError
        from app.services.auth_service import AuthService

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None  # instance_id 不匹配，查无结果

        mock_conn = AsyncMock()
        mock_conn.execute.return_value = mock_result

        svc = AuthService()
        with pytest.raises(AppError) as exc_info:
            await svc.platform_login(mock_conn, "admin@test.com", "password123")
        assert exc_info.value.status_code == 401


class TestTenantLoginInstanceFilter:
    """U10: tenant_login 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_sql_includes_instance_id_param(self):
        """tenant_login 的 SQL execute 调用参数包含 instance_id"""
        from app.services.auth_service import AuthService

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = _active_tenant_user()

        mock_role_result = MagicMock()
        mock_role_result.all.return_value = [("admin",)]

        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = [mock_result, mock_role_result]

        svc = AuthService()
        with patch("app.services.auth_service.verify_password", return_value=True), \
             patch("app.services.auth_service.get_engine"):
            await svc.tenant_login(mock_conn, "test-tenant", "user@test.com", "password123")

        # 第一次 execute 调用是 SELECT 查询
        first_call = mock_conn.execute.call_args_list[0]
        params = first_call[0][1]
        assert "instance_id" in params
