"""新手引导完成:无前置校验(openspec change update-onboarding-remove-keyword-gate)"""

from unittest.mock import AsyncMock

import pytest

from app.services.tenant_settings_service import TenantSettingsService


class TestCompleteOnboarding:
    @pytest.mark.asyncio
    async def test_completes_without_any_keyword(self):
        """未配置关键词也能完成引导:不查询关键词、不抛 422,仅执行 UPDATE"""
        svc = TenantSettingsService()
        conn = AsyncMock()

        await svc.complete_onboarding(conn, tenant_id="t-001")

        assert conn.execute.await_count == 1
        sql = str(conn.execute.call_args.args[0])
        assert "UPDATE tenants" in sql
        assert "needs_onboarding = false" in sql
        assert conn.execute.call_args.args[1] == {"tenant_id": "t-001"}
