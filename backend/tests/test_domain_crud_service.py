"""域名 CRUD 服务层测试 — sender_email 写入、编辑、删除"""

from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.services.admin_config_service import AdminConfigService

TENANT_ID = "t-001"
DOMAIN_ID = "d-001"
USER_ID = "u-001"


def _domain_dict(**overrides):
    base = {
        "id": DOMAIN_ID,
        "tenant_id": TENANT_ID,
        "domain": "example.com",
        "verification_status": "verified",
        "dns_verified_at": None,
        "dns_last_checked_at": None,
        "warmup_rule_id": "rule-001",
        "warmup_level": 1,
        "daily_limit": 50,
        "total_sent": 0,
        "bounce_rate": None,
        "complaint_rate": None,
        "open_rate": None,
        "level_changed_at": None,
        "sender_email": None,
        "created_at": "2026-05-23T10:00:00",
        "updated_at": "2026-05-23T10:00:00",
    }
    base.update(overrides)
    return base


def _mock_mappings_first(row_dict):
    """构造 conn.execute 返回 mappings().first() 的 mock"""
    mapping = MagicMock()
    mapping.__getitem__ = lambda self, key: row_dict[key]
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    return result


def _mock_mappings_scalar(value):
    """构造 conn.execute 返回 scalar_one() 的 mock"""
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


class TestCreateDomainSenderEmail:
    """U3: create_tenant_domain 支持 sender_email"""

    @pytest.mark.asyncio
    async def test_create_domain_with_sender_email(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        level_row = {"daily_limit": 50}
        conn.execute = AsyncMock(side_effect=[
            _mock_mappings_first(level_row),
            MagicMock(),
            MagicMock(),
        ])

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict(sender_email="sales@example.com")):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                result = await svc.create_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    payload={
                        "domain": "example.com",
                        "warmup_rule_id": "rule-001",
                        "warmup_level": 1,
                        "sender_email": "sales@example.com",
                    },
                    platform_user_id=USER_ID,
                )

        insert_call = conn.execute.call_args_list[1]
        insert_params = insert_call[0][1]
        assert insert_params["sender_email"] == "sales@example.com"
        assert result["sender_email"] == "sales@example.com"

    @pytest.mark.asyncio
    async def test_create_domain_without_sender_email(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        level_row = {"daily_limit": 50}
        conn.execute = AsyncMock(side_effect=[
            _mock_mappings_first(level_row),
            MagicMock(),
            MagicMock(),
        ])

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict()):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                result = await svc.create_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    payload={
                        "domain": "example.com",
                        "warmup_rule_id": "rule-001",
                        "warmup_level": 1,
                    },
                    platform_user_id=USER_ID,
                )

        insert_call = conn.execute.call_args_list[1]
        insert_params = insert_call[0][1]
        assert insert_params["sender_email"] is None


class TestUpdateTenantDomain:
    """U4: update_tenant_domain 服务方法"""

    @pytest.mark.asyncio
    async def test_update_sender_email(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict(sender_email="new@example.com")):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                result = await svc.update_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    payload={"sender_email": "new@example.com"},
                    platform_user_id=USER_ID,
                )

        assert result["sender_email"] == "new@example.com"
        conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_update_warmup_triggers_daily_limit_recalc(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        level_row = {"daily_limit": 200}
        conn.execute = AsyncMock(side_effect=[
            _mock_mappings_first(level_row),
            MagicMock(),
            MagicMock(),
        ])

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict(warmup_level=3, daily_limit=200)):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                result = await svc.update_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    payload={"warmup_rule_id": "rule-001", "warmup_level": 3},
                    platform_user_id=USER_ID,
                )

        assert conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_update_ignores_domain_field(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict()):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                result = await svc.update_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    payload={"domain": "hacked.com", "sender_email": "a@b.com"},
                    platform_user_id=USER_ID,
                )

        for c in conn.execute.call_args_list:
            sql_str = str(c[0][0])
            assert "hacked.com" not in sql_str

    @pytest.mark.asyncio
    async def test_update_invalid_warmup_returns_422(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        no_result = MagicMock()
        no_result.mappings.return_value.first.return_value = None
        conn.execute = AsyncMock(return_value=no_result)

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict()):
            with pytest.raises(AppError) as exc_info:
                await svc.update_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    payload={"warmup_rule_id": "bad-rule", "warmup_level": 99},
                    platform_user_id=USER_ID,
                )
            assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_update_nonexistent_domain_returns_404(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, side_effect=AppError(code="NOT_FOUND", message="租户域名不存在", status_code=404)):
            with pytest.raises(AppError) as exc_info:
                await svc.update_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id="nonexistent",
                    payload={"sender_email": "a@b.com"},
                    platform_user_id=USER_ID,
                )
            assert exc_info.value.status_code == 404


class TestDeleteTenantDomain:
    """U5: delete_tenant_domain 服务方法"""

    @pytest.mark.asyncio
    async def test_delete_domain_success(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        conn.execute = AsyncMock(side_effect=[
            _mock_mappings_scalar(0),
            _mock_mappings_scalar(0),
            MagicMock(),
        ])

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict()):
            with patch.object(svc, "audit") as mock_audit:
                mock_audit.write = AsyncMock()
                await svc.delete_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    platform_user_id=USER_ID,
                )

        assert conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_domain_with_daily_usage_returns_409(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        conn.execute = AsyncMock(side_effect=[
            _mock_mappings_scalar(5),
        ])

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict()):
            with pytest.raises(AppError) as exc_info:
                await svc.delete_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    platform_user_id=USER_ID,
                )
            assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_domain_with_sending_plans_returns_409(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        conn.execute = AsyncMock(side_effect=[
            _mock_mappings_scalar(0),
            _mock_mappings_scalar(2),
        ])

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, return_value=_domain_dict()):
            with pytest.raises(AppError) as exc_info:
                await svc.delete_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    platform_user_id=USER_ID,
                )
            assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_nonexistent_domain_returns_404(self):
        svc = AdminConfigService()
        conn = AsyncMock()

        with patch.object(svc, "get_tenant_domain", new_callable=AsyncMock, side_effect=AppError(code="NOT_FOUND", message="租户域名不存在", status_code=404)):
            with pytest.raises(AppError) as exc_info:
                await svc.delete_tenant_domain(
                    conn,
                    tenant_id=TENANT_ID,
                    domain_id="nonexistent",
                    platform_user_id=USER_ID,
                )
            assert exc_info.value.status_code == 404
