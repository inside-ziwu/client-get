"""Internal API 实例隔离测试（U28-U29）

U28: claim_due_emails 端点 → 底层 TenantMessagingService 已通过 get_settings().instance_id 过滤
U29: list_collection_credentials 端点 → InternalOpsService 查询加 instance_id 过滤
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.internal_ops_service import InternalOpsService

INSTANCE_ID = "test-instance"


def _mock_settings():
    s = MagicMock()
    s.instance_id = INSTANCE_ID
    return s


def _extract_params(call):
    """从 conn.execute 调用中提取参数字典"""
    if len(call.args) > 1:
        return call.args[1]
    return call.kwargs


def _extract_sql(call):
    """从 conn.execute 调用中提取 SQL 字符串"""
    return str(call.args[0].text if hasattr(call.args[0], "text") else call.args[0])


# ── U28: claim_due_emails ─────────────────────────────────────────────────────


class TestClaimDueEmailsInstanceIsolation:
    """U28: claim_due_emails 底层查询通过 instance_id 过滤"""

    def test_claim_due_emails_source_has_instance_id_filter(self):
        """验证 TenantMessagingService.claim_due_emails 源码中包含 instance_id 过滤"""
        from app.services.tenant_messaging_service import TenantMessagingService

        source = inspect.getsource(TenantMessagingService.claim_due_emails)
        assert "instance_id" in source, "claim_due_emails 查询缺少 instance_id 过滤"

    def test_claim_due_emails_delegates_to_messaging_service(self):
        """验证 InternalOpsService.claim_due_emails 直接委托给 TenantMessagingService"""
        source = inspect.getsource(InternalOpsService.claim_due_emails)
        assert "self.messaging.claim_due_emails" in source

    @pytest.mark.asyncio
    async def test_claim_due_emails_passes_payload(self):
        """验证端点正确将 payload 透传给底层 service"""
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


# ── U29: list_collection_credentials ─────────────────────────────────────────


class TestCollectionCredentialsInstanceIsolation:
    """U29: list_collection_credentials 查询按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_credentials_contains_instance_id(self):
        """验证查询参数中包含 instance_id"""
        with patch("app.services.internal_ops_service.get_settings", return_value=_mock_settings()):
            svc = InternalOpsService()
            conn = AsyncMock()
            result_mock = MagicMock()
            result_mock.mappings.return_value.all.return_value = []
            conn.execute = AsyncMock(return_value=result_mock)

            await svc.list_collection_credentials(conn, "waimao_tong")

            conn.execute.assert_called_once()
            params = _extract_params(conn.execute.call_args)
            assert params["instance_id"] == INSTANCE_ID
            assert params["source_type"] == "waimao_tong"

    @pytest.mark.asyncio
    async def test_list_credentials_sql_contains_instance_id_filter(self):
        """验证 SQL 中包含 instance_id 过滤条件"""
        with patch("app.services.internal_ops_service.get_settings", return_value=_mock_settings()):
            svc = InternalOpsService()
            conn = AsyncMock()
            result_mock = MagicMock()
            result_mock.mappings.return_value.all.return_value = []
            conn.execute = AsyncMock(return_value=result_mock)

            await svc.list_collection_credentials(conn, "tengdao")

            sql = _extract_sql(conn.execute.call_args)
            assert "instance_id" in sql

    @pytest.mark.asyncio
    async def test_list_credentials_returns_decrypted_secrets(self):
        """验证返回值中 credentials_encrypted 被解密为 secret"""
        row = MagicMock()
        row.__getitem__ = lambda self, key: {
            "id": "cred-001",
            "account_no": "acc-01",
            "username": "user01",
            "credentials_encrypted": "encrypted-data",
            "rotation_order": 1,
            "daily_quota": 100,
            "current_day_used": 5,
            "is_active": True,
        }[key]

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]

        with patch("app.services.internal_ops_service.get_settings", return_value=_mock_settings()):
            with patch("app.services.internal_ops_service.decrypt_secret", return_value="plain-secret"):
                svc = InternalOpsService()
                conn = AsyncMock()
                conn.execute = AsyncMock(return_value=result_mock)

                items = await svc.list_collection_credentials(conn, "waimao_tong")

        assert len(items) == 1
        assert items[0]["secret"] == "plain-secret"
        assert items[0]["id"] == "cred-001"
