"""认证中间件 instance_id 隔离测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.security.jwt import create_access_token


@pytest.fixture
def app():
    from app.main import create_app

    application = create_app()
    yield application
    application.dependency_overrides.clear()


class TestPlatformUserIidValidation:
    @pytest.mark.asyncio
    async def test_matching_iid_passes(self, app):
        from app.db.pools import get_connection
        from app.security.dependencies import get_current_platform_user

        settings = get_settings()
        token = create_access_token({"sub": "u1", "kind": "platform", "roles": ["platform_admin"]})

        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "id": "u1",
            "email": "admin@test.com",
            "name": "Admin",
            "status": "active",
            "instance_id": settings.instance_id,
        }
        mock_conn.execute.return_value = mock_result
        app.dependency_overrides[get_connection] = lambda: mock_conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_mismatched_iid_returns_403(self, app):
        from app.db.pools import get_connection

        # 手动创建一个 iid 不匹配的 token（模拟跨实例 token）
        from jose import jwt as jose_jwt

        settings = get_settings()
        payload = {
            "sub": "u1",
            "kind": "platform",
            "roles": ["platform_admin"],
            "iid": "other_instance",
            "iat": 1000000000,
            "exp": 9999999999,
        }
        token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_conn = AsyncMock()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_iid_returns_403(self, app):
        from app.db.pools import get_connection

        from jose import jwt as jose_jwt

        settings = get_settings()
        payload = {
            "sub": "u1",
            "kind": "platform",
            "roles": ["platform_admin"],
            "iat": 1000000000,
            "exp": 9999999999,
        }
        token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_conn = AsyncMock()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 403


class TestTenantUserIidValidation:
    @pytest.mark.asyncio
    async def test_mismatched_iid_raises_forbidden(self):
        from fastapi.security import HTTPAuthorizationCredentials
        from jose import jwt as jose_jwt
        from app.core.errors import AppError
        from app.security.dependencies import get_current_tenant_user

        settings = get_settings()
        payload = {
            "sub": "u1",
            "kind": "tenant",
            "tid": "t1",
            "slug": "demo",
            "roles": ["admin"],
            "iid": "other_instance",
            "iat": 1000000000,
            "exp": 9999999999,
        }
        token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(AppError) as exc_info:
            await get_current_tenant_user(slug="demo", credentials=creds, conn=AsyncMock())
        assert exc_info.value.status_code == 403


class TestServiceTokenIidValidation:
    @pytest.mark.asyncio
    async def test_mismatched_service_iid_returns_403(self, app):
        from app.db.pools import get_connection

        from jose import jwt as jose_jwt

        settings = get_settings()
        payload = {
            "sub": "svc",
            "kind": "service",
            "service_name": "sending-worker",
            "scopes": ["sending:claim"],
            "iid": "other_instance",
            "iat": 1000000000,
            "exp": 9999999999,
        }
        token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_conn = AsyncMock()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/internal/api/v1/sending/due-emails/claim",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Service-Name": "sending-worker",
                },
                json={},
            )
        assert response.status_code == 403
