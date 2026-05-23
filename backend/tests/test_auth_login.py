from unittest.mock import AsyncMock, patch

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
