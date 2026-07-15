"""Internal 发送 API 实例隔离测试。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.internal_ops_service import InternalOpsService


class TestClaimDueEmailsInstanceIsolation:
    """claim_due_emails 底层查询通过 instance_id 过滤。"""

    def test_claim_due_emails_source_has_instance_id_filter(self):
        from app.services.tenant_messaging_service import TenantMessagingService

        source = inspect.getsource(TenantMessagingService.claim_due_emails)
        assert "instance_id" in source

    def test_claim_due_emails_delegates_to_messaging_service(self):
        source = inspect.getsource(InternalOpsService.claim_due_emails)
        assert "self.messaging.claim_due_emails" in source

    @pytest.mark.asyncio
    async def test_claim_due_emails_passes_payload(self):
        svc = InternalOpsService()
        svc.messaging = MagicMock()
        svc.messaging.claim_due_emails = AsyncMock(return_value={"items": [], "total": 0})

        conn = AsyncMock()
        payload = {"service_instance": "worker-01", "limit": 10, "domain_id": "d-001"}
        await svc.claim_due_emails(conn, payload)

        svc.messaging.claim_due_emails.assert_called_once_with(
            conn,
            service_instance="worker-01",
            limit=10,
            domain_id="d-001",
        )
