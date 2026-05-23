"""发送计划状态检查测试 — update/delete 状态约束"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import AppError
from app.services.tenant_messaging_service import TenantMessagingService

TENANT_ID = "t-001"
USER_ID = "u-001"
PLAN_ID = "plan-001"


def _plan_dict(status="draft"):
    now = datetime(2026, 5, 23, 10, 0, 0).isoformat()
    return {
        "id": PLAN_ID,
        "name": "测试",
        "description": "",
        "status": status,
        "recipient_source": "csv",
        "recipient_config": None,
        "send_strategy": None,
        "sender_name": "Test",
        "sender_email": "test@test.com",
        "domain_id": None,
        "total_recipients": 0,
        "sent_count": 0,
        "scheduled_at": None,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
        "steps_count": 0,
    }


class TestUpdateSendingPlanStatusCheck:
    """U6: update_sending_plan 非 draft 拒绝"""

    @pytest.mark.asyncio
    async def test_running_rejects_update(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("running")):
            with pytest.raises(AppError) as exc_info:
                await svc.update_sending_plan(
                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID, payload={"name": "新名称"}
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_scheduled_rejects_update(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("scheduled")):
            with pytest.raises(AppError) as exc_info:
                await svc.update_sending_plan(
                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID, payload={"name": "新名称"}
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_completed_rejects_update(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("completed")):
            with pytest.raises(AppError) as exc_info:
                await svc.update_sending_plan(
                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID, payload={"name": "新名称"}
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_draft_allows_update(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                result = await svc.update_sending_plan(
                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID, payload={"name": "新名称"}
                )
                assert result is not None


class TestDeleteSendingPlanStatusCheck:
    """U7: delete_sending_plan 状态约束"""

    @pytest.mark.asyncio
    async def test_draft_allows_delete(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                await svc.delete_sending_plan(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID)

    @pytest.mark.asyncio
    async def test_completed_allows_delete(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("completed")):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                await svc.delete_sending_plan(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID)

    @pytest.mark.asyncio
    async def test_cancelled_allows_delete(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("cancelled")):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                await svc.delete_sending_plan(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID)

    @pytest.mark.asyncio
    async def test_running_rejects_delete(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("running")):
            with pytest.raises(AppError) as exc_info:
                await svc.delete_sending_plan(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_scheduled_rejects_delete(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("scheduled")):
            with pytest.raises(AppError) as exc_info:
                await svc.delete_sending_plan(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_paused_rejects_delete(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("paused")):
            with pytest.raises(AppError) as exc_info:
                await svc.delete_sending_plan(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID)
            assert exc_info.value.status_code == 403
