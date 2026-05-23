"""complete-update 端点测试 — 路由 + service"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.errors import AppError
from app.main import create_app
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
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


class TestCompleteUpdateStatusCheck:
    """U8: complete_update 非 draft 拒绝"""

    @pytest.mark.asyncio
    async def test_running_rejects(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("running")):
            with pytest.raises(AppError) as exc_info:
                await svc.complete_update_sending_plan(
                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID,
                    payload={"plan": {"name": "新"}, "steps": []},
                )
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_scheduled_rejects(self):
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("scheduled")):
            with pytest.raises(AppError) as exc_info:
                await svc.complete_update_sending_plan(
                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID,
                    payload={"plan": {"name": "新"}, "steps": []},
                )
            assert exc_info.value.status_code == 403


class TestCompleteUpdateExecution:
    """U9-U11: complete_update 基本信息+步骤替换+收件人"""

    @pytest.mark.asyncio
    async def test_updates_plan_info(self):
        """U9: 基本信息更新"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")) as mock_get:
            with patch.object(svc, "update_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")) as mock_update:
                with patch.object(svc, "list_plan_steps", new_callable=AsyncMock, return_value=[]):
                    with patch.object(svc, "audit") as mock_audit:
                        mock_audit.write = AsyncMock()
                        await svc.complete_update_sending_plan(
                            conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID,
                            payload={"plan": {"name": "新名称"}, "steps": []},
                        )

                        mock_update.assert_called_once()
                        call_payload = mock_update.call_args.kwargs["payload"]
                        assert call_payload["name"] == "新名称"

    @pytest.mark.asyncio
    async def test_replaces_steps(self):
        """U10: 删除旧步骤并插入新步骤"""
        svc = TenantMessagingService()
        conn = AsyncMock()
        old_step = {"id": "step-old", "step_number": 1}

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")):
            with patch.object(svc, "update_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")):
                with patch.object(svc, "list_plan_steps", new_callable=AsyncMock, return_value=[old_step]):
                    with patch.object(svc, "delete_plan_step", new_callable=AsyncMock) as mock_delete_step:
                        with patch.object(svc, "create_plan_step", new_callable=AsyncMock) as mock_create_step:
                            with patch.object(svc, "audit") as mock_audit:
                                mock_audit.write = AsyncMock()
                                await svc.complete_update_sending_plan(
                                    conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID,
                                    payload={
                                        "plan": {"name": "测试"},
                                        "steps": [{"step_number": 1, "template_id": "t1", "delay_days": 0}],
                                    },
                                )

                                mock_delete_step.assert_called_once_with(conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, step_id="step-old")
                                mock_create_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_recipient_config(self):
        """U11: payload 中的 recipient_config 传递给 update"""
        svc = TenantMessagingService()
        conn = AsyncMock()

        with patch.object(svc, "get_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")):
            with patch.object(svc, "update_sending_plan", new_callable=AsyncMock, return_value=_plan_dict("draft")) as mock_update:
                with patch.object(svc, "list_plan_steps", new_callable=AsyncMock, return_value=[]):
                    with patch.object(svc, "audit") as mock_audit:
                        mock_audit.write = AsyncMock()
                        config = {"source": "group", "group_id": "g1"}
                        await svc.complete_update_sending_plan(
                            conn, tenant_id=TENANT_ID, plan_id=PLAN_ID, user_id=USER_ID,
                            payload={"plan": {"name": "测试", "recipient_config": config}, "steps": []},
                        )

                        call_payload = mock_update.call_args.kwargs["payload"]
                        assert call_payload["recipient_config"] == config


class TestCompleteUpdateRoute:
    """U8: 路由层测试"""

    @pytest.fixture
    def app(self):
        application = create_app()
        ctx = TenantAuthContext(
            tenant_id=TENANT_ID,
            tenant_slug="test-tenant",
            user_id=USER_ID,
            email="test@test.com",
            name="Test",
            roles=["admin"],
            must_change_pwd=False,
            connection=AsyncMock(),
        )
        application.dependency_overrides[get_current_tenant_user] = lambda: ctx
        yield application
        application.dependency_overrides.clear()

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_route_calls_service(self, client):
        with patch(
            "app.api.tenant.messaging.service.complete_update_sending_plan",
            new_callable=AsyncMock,
            return_value=_plan_dict("draft"),
        ) as mock_fn:
            resp = await client.post(
                f"/t/test-tenant/api/v1/sending-plans/{PLAN_ID}/complete-update",
                json={"plan": {"name": "新"}, "steps": []},
            )
            assert resp.status_code == 200
            mock_fn.assert_called_once()
