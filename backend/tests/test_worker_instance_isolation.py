"""Worker 查询和 advisory lock 按 instance_id 隔离测试（U24-U27）"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


# ── U24: sending_worker 查询加 instance_id 过滤 ─────────────────────────────


class TestListRunningDomainIds:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "app.services.tenant_messaging_service.get_settings",
            return_value=_mock_settings(),
        ):
            yield

    @pytest.mark.asyncio
    async def test_sql_contains_instance_id(self):
        from app.services.tenant_messaging_service import TenantMessagingService

        svc = TenantMessagingService()
        conn = AsyncMock()

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        conn.execute.return_value = result_mock

        await svc.list_running_domain_ids(conn)

        call = conn.execute.call_args_list[-1]
        sql = _extract_sql(call)
        params = _extract_params(call)

        assert "instance_id" in sql
        assert params["instance_id"] == INSTANCE_ID
        assert "JOIN tenants" in sql


class TestClaimDueEmails:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "app.services.tenant_messaging_service.get_settings",
            return_value=_mock_settings(),
        ):
            yield

    @pytest.mark.asyncio
    async def test_sql_contains_instance_id(self):
        from app.services.tenant_messaging_service import TenantMessagingService

        svc = TenantMessagingService()
        conn = AsyncMock()

        # claim 主查询返回空
        claim_result = MagicMock()
        claim_result.mappings.return_value.all.return_value = []
        conn.execute.return_value = claim_result

        # 传入 timezone_config 跳过 load_timezone_config 多次 DB 查询
        await svc.claim_due_emails(
            conn,
            service_instance="worker-1",
            limit=10,
            timezone_config={"rules": {}, "default_rule": None, "countries": {}, "holidays": set()},
        )

        # 取主查询调用（第 1 次 execute）
        call = conn.execute.call_args_list[0]
        sql = _extract_sql(call)
        params = _extract_params(call)

        assert "instance_id" in sql
        assert params["instance_id"] == INSTANCE_ID
        assert "JOIN tenants" in sql


class TestRecoverStaleLocks:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "app.services.tenant_messaging_service.get_settings",
            return_value=_mock_settings(),
        ):
            yield

    @pytest.mark.asyncio
    async def test_sql_contains_instance_id(self):
        from app.services.tenant_messaging_service import TenantMessagingService

        svc = TenantMessagingService()
        conn = AsyncMock()

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        conn.execute.return_value = result_mock

        await svc.recover_stale_locks(conn)

        call = conn.execute.call_args_list[0]
        sql = _extract_sql(call)
        params = _extract_params(call)

        assert "instance_id" in sql
        assert params["instance_id"] == INSTANCE_ID


# ── U25: reconciliation_worker 查询加 instance_id 过滤 ──────────────────────


class TestReconcileOnce:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "app.services.email_reconciliation_service.get_settings",
            return_value=_mock_settings(),
        ):
            yield

    @pytest.mark.asyncio
    async def test_sql_contains_instance_id(self):
        from app.services.email_reconciliation_service import (
            EmailReconciliationService,
        )

        svc = EmailReconciliationService()
        conn = AsyncMock()
        client = AsyncMock()

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        conn.execute.return_value = result_mock

        await svc.reconcile_once(conn, client)

        call = conn.execute.call_args_list[0]
        sql = _extract_sql(call)
        params = _extract_params(call)

        assert "instance_id" in sql
        assert params["instance_id"] == INSTANCE_ID
        assert "JOIN tenants" in sql


# ── U26: wmt_lineage_repair fan-out 加 instance_id 过滤 ─────────────────────


class TestWmtLineageRepairFanOut:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "app.workers.wmt_lineage_repair.get_settings",
            return_value=_mock_settings(),
        ):
            yield

    @pytest.mark.asyncio
    async def test_fan_out_keywords_contains_instance_id(self):
        from app.workers.wmt_lineage_repair import _SQL_FAN_OUT_ACTIVE_KEYWORDS

        sql = str(_SQL_FAN_OUT_ACTIVE_KEYWORDS.text)
        assert "instance_id" in sql
        assert "JOIN tenants" in sql

    @pytest.mark.asyncio
    async def test_fan_out_industry_contains_instance_id(self):
        from app.workers.wmt_lineage_repair import _SQL_FAN_OUT_INDUSTRY

        sql = str(_SQL_FAN_OUT_INDUSTRY.text)
        assert "instance_id" in sql

    @pytest.mark.asyncio
    async def test_run_passes_instance_id_params(self):
        from app.workers.wmt_lineage_repair import (
            run_wmt_lineage_repair_on_connection,
        )

        conn = AsyncMock()

        # advisory lock 返回 True
        conn.scalar.return_value = True

        # 每次 execute 返回空结果
        result_mock = MagicMock()
        result_mock.rowcount = 0
        result_mock.mappings.return_value.all.return_value = []
        result_mock.fetchall.return_value = []
        conn.execute.return_value = result_mock

        await run_wmt_lineage_repair_on_connection(conn)

        # 检查 advisory lock 调用包含 instance_id（scalar 第 1 次调用，索引 0）
        lock_call = conn.scalar.call_args_list[0]
        lock_params = lock_call.args[1]
        assert lock_params["instance_id"] == INSTANCE_ID

        # 检查 fan_out 和 industry_fan_out execute 调用包含 instance_id
        fan_out_found = False
        industry_found = False
        for call in conn.execute.call_args_list:
            if len(call.args) > 1 and isinstance(call.args[1], dict):
                params = call.args[1]
                sql = str(call.args[0].text if hasattr(call.args[0], "text") else call.args[0])
                if "tenant_keyword" in sql and "instance_id" in params:
                    assert params["instance_id"] == INSTANCE_ID
                    fan_out_found = True
                if "industry_aliases" in params and "instance_id" in params:
                    assert params["instance_id"] == INSTANCE_ID
                    industry_found = True
        assert fan_out_found, "fan_out 关键词查询应包含 instance_id 参数"
        assert industry_found, "fan_out 行业查询应包含 instance_id 参数"


# ── U27: advisory lock 区分实例级 ──────────────────────────────────────────


class TestAdvisoryLockInstanceScoped:
    @pytest.fixture(autouse=True)
    def _patch_settings(self):
        with patch(
            "app.workers.wmt_lineage_repair.get_settings",
            return_value=_mock_settings(),
        ):
            yield

    @pytest.mark.asyncio
    async def test_advisory_lock_uses_hashtext_instance_id(self):
        from app.workers.wmt_lineage_repair import (
            run_wmt_lineage_repair_on_connection,
        )

        conn = AsyncMock()
        conn.scalar.return_value = False  # lock 未获取，跳过

        result = await run_wmt_lineage_repair_on_connection(conn)

        assert result["skipped"] is True

        # scalar 第 1 次调用（索引 0）是 advisory lock
        lock_call = conn.scalar.call_args_list[0]
        sql = str(lock_call.args[0].text if hasattr(lock_call.args[0], "text") else lock_call.args[0])
        params = lock_call.args[1]

        assert "hashtext" in sql
        assert "instance_id" in sql
        assert params["instance_id"] == INSTANCE_ID
        # key 必须在 bigint 域求和:hashtext 返回 int4,int4+int4 溢出
        # (2026052101 + hashtext('default')=822708183 > int4 上限,生产曾报
        # NumericValueOutOfRangeError: integer out of range)
        assert "CAST(:key AS bigint)" in sql

    @pytest.mark.asyncio
    async def test_tenant_ops_advisory_lock_unchanged(self):
        """确认 tenant_ops_service.py 的 advisory lock 未被修改（保持全局互锁）"""
        import inspect
        import app.services.tenant_ops_service as mod

        source = inspect.getsource(mod)
        # tenant_ops_service 不应该包含 hashtext(instance_id) 的 advisory lock
        assert "hashtext(:instance_id)" not in source
