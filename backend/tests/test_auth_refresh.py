from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.pools import get_connection
from app.main import create_app
from app.security.jwt import create_refresh_token


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


def _make_refresh_cookie(sub="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", kind="platform"):
    return create_refresh_token({"sub": sub, "kind": kind, "roles": ["platform_admin"]})


def _mock_active_user():
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = {"status": "active"}
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result
    return mock_conn


def _mock_disabled_user():
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = {"status": "disabled"}
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = mock_result
    return mock_conn


class TestRefreshEndpoint:
    @pytest.mark.asyncio
    async def test_valid_cookie_returns_new_access_token(self, app, client):
        token = _make_refresh_cookie()
        mock_conn = _mock_active_user()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        resp = await client.post(
            "/admin/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body["data"]

    @pytest.mark.asyncio
    async def test_without_cookie_returns_401(self, client):
        resp = await client.post("/admin/api/v1/auth/refresh")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client):
        from app.core.config import get_settings
        from jose import jwt as jose_jwt

        settings = get_settings()
        payload = {
            "sub": "u1",
            "kind": "platform",
            "type": "refresh",
            "iat": 1000000000,
            "exp": 1000000001,
        }
        expired_token = jose_jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        resp = await client.post(
            "/admin/api/v1/auth/refresh",
            cookies={"refresh_token": expired_token},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_disabled_user_returns_401(self, app, client):
        token = _make_refresh_cookie()
        mock_conn = _mock_disabled_user()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        resp = await client.post(
            "/admin/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )
        assert resp.status_code == 401


class TestRefreshInstanceFilter:
    """U11: refresh 端点校验 iid + instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_matching_iid_refreshes_successfully(self, app, client):
        """refresh_token 的 iid 匹配 → 刷新成功，新 token 包含 iid"""
        from app.security.jwt import decode_access_token

        token = _make_refresh_cookie()  # 使用默认 instance_id="default"
        mock_conn = _mock_active_user()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        resp = await client.post(
            "/admin/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 200
        body = resp.json()
        new_access_token = body["data"]["access_token"]
        decoded = decode_access_token(new_access_token)
        assert decoded["iid"] == "default"

    @pytest.mark.asyncio
    async def test_mismatched_iid_returns_403(self, app, client):
        """refresh_token 的 iid 不匹配 → 返回 403"""
        from app.core.config import get_settings
        from jose import jwt as jose_jwt

        settings = get_settings()
        # 制造一个 iid 与当前实例不匹配的 refresh_token
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "kind": "platform",
            "roles": ["platform_admin"],
            "iid": "other-instance",  # 不匹配当前实例的 "default"
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=7)).timestamp()),
        }
        token = jose_jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        mock_conn = _mock_active_user()
        app.dependency_overrides[get_connection] = lambda: mock_conn

        resp = await client.post(
            "/admin/api/v1/auth/refresh",
            cookies={"refresh_token": token},
        )

        assert resp.status_code == 403


class TestLogoutEndpoint:
    @pytest.mark.asyncio
    async def test_clears_refresh_cookie(self, client):
        resp = await client.post("/admin/api/v1/auth/logout")
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert 'max-age=0' in set_cookie.lower() or '"0"' in set_cookie
