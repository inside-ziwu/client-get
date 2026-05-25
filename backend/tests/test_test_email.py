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
