"""租户管理 API instance_id 隔离测试（U14-U16）"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest

from app.core.errors import AppError
from app.services.tenant_service import TenantService

INSTANCE_ID = "test-instance"


def _mock_settings():
    s = MagicMock()
    s.instance_id = INSTANCE_ID
    return s


def _mock_mappings_all(rows: list[dict]):
    """构造 conn.execute 返回 mappings().all() 的 mock"""
    mappings = []
    for row in rows:
        m = MagicMock()
        m.__getitem__ = lambda self, key: row[key]  # noqa: B023
        m.get = lambda key, default=None, _r=row: _r.get(key, default)
        mappings.append(m)
    result = MagicMock()
    result.mappings.return_value.all.return_value = mappings
    return result


def _mock_mappings_first(row_dict):
    """构造 conn.execute 返回 mappings().first() 的 mock"""
    if row_dict is None:
        result = MagicMock()
        result.mappings.return_value.first.return_value = None
        result.first.return_value = None
        return result
    mapping = MagicMock()
    mapping.__getitem__ = lambda self, key: row_dict[key]
    mapping.get = lambda key, default=None, _r=row_dict: _r.get(key, default)
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    result.first.return_value = None  # slug 查重返回 None
    return result


def _tenant_row(**overrides):
    now = datetime.now()
    base = {
        "id": "t-001",
        "name": "测试租户",
        "slug": "test",
        "industry": "electronics",
        "status": "active",
        "needs_onboarding": False,
        "contact_name": "张三",
        "contact_phone": "13800138000",
        "contact_email": "test@example.com",
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _patch_settings():
    with patch("app.services.tenant_service.get_settings", return_value=_mock_settings()):
        yield


class TestListTenantsInstanceId:
    """U14: list_tenants 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_list_tenants_sql_contains_instance_id(self):
        svc = TenantService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_all([_tenant_row()]))

        await svc.list_tenants(conn)

        conn.execute.assert_called_once()
        _, kwargs = conn.execute.call_args
        # 验证参数字典包含 instance_id
        assert kwargs is not None or conn.execute.call_args.args[1] is not None
        params = conn.execute.call_args.args[1] if len(conn.execute.call_args.args) > 1 else kwargs
        assert params["instance_id"] == INSTANCE_ID


class TestGetTenantInstanceId:
    """U15: get_tenant 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_get_tenant_sql_contains_instance_id(self):
        svc = TenantService()
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=_mock_mappings_first(_tenant_row()))

        await svc.get_tenant(conn, "t-001")

        conn.execute.assert_called_once()
        params = conn.execute.call_args.args[1]
        assert params["instance_id"] == INSTANCE_ID
        assert params["tenant_id"] == "t-001"


class TestUpdateTenantInstanceId:
    """U15: update_tenant 按 instance_id 过滤"""

    @pytest.mark.asyncio
    async def test_update_tenant_sql_contains_instance_id(self):
        svc = TenantService()
        conn = AsyncMock()

        # get_tenant 调用（update_tenant 内部先调用 get_tenant 做校验）
        get_result = _mock_mappings_first(_tenant_row())
        # update 执行结果
        update_result = MagicMock()
        # get_tenant 再次调用（update_tenant 结尾返回最新数据）
        get_result_after = _mock_mappings_first(_tenant_row(name="新名称"))

        conn.execute = AsyncMock(side_effect=[get_result, update_result, get_result_after])

        await svc.update_tenant(conn, tenant_id="t-001", payload={"name": "新名称"})

        # 第二个 execute 调用是 UPDATE 语句
        update_call = conn.execute.call_args_list[1]
        params = update_call.args[1]
        assert params["instance_id"] == INSTANCE_ID
        assert params["tenant_id"] == "t-001"


class TestCreateTenantInstanceId:
    """U16: create_tenant INSERT 和 slug 查重包含 instance_id"""

    @pytest.mark.asyncio
    async def test_create_tenant_insert_contains_instance_id(self):
        svc = TenantService()
        conn = AsyncMock()

        # slug 查重（返回 None 表示不存在）
        slug_check = MagicMock()
        slug_check.first.return_value = None
        # INSERT tenants
        insert_tenant = MagicMock()
        # INSERT users
        insert_user = MagicMock()
        # INSERT user_roles
        insert_role = MagicMock()
        # _copy_platform_scoring_template: SELECT 返回 None
        scoring_select = _mock_mappings_first(None)
        # INSERT scoring_templates（默认模板）
        insert_scoring = MagicMock()
        # INSERT scoring_template_versions
        insert_version = MagicMock()
        # _copy_platform_email_templates: SELECT 返回空
        email_select = _mock_mappings_all([])
        # INSERT contact_rules
        insert_contact = MagicMock()
        # get_tenant（返回创建后的租户）
        get_tenant_result = _mock_mappings_first(_tenant_row())

        conn.execute = AsyncMock(
            side_effect=[
                slug_check,
                insert_tenant,
                insert_user,
                insert_role,
                scoring_select,
                insert_scoring,
                insert_version,
                email_select,
                insert_contact,
                get_tenant_result,
            ]
        )

        with patch("app.services.tenant_service.hash_password", return_value="hashed"):
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload={
                    "name": "新租户",
                    "slug": "new-tenant",
                    "industry": "electronics",
                    "admin_email": "admin@test.com",
                    "admin_password": "pass123",
                    "admin_name": "管理员",
                },
            )

        # 第 1 个调用：slug 查重
        slug_call = conn.execute.call_args_list[0]
        slug_params = slug_call.args[1]
        assert slug_params["instance_id"] == INSTANCE_ID
        assert slug_params["slug"] == "new-tenant"

        # 第 2 个调用：INSERT tenants
        insert_call = conn.execute.call_args_list[1]
        insert_params = insert_call.args[1]
        assert insert_params["instance_id"] == INSTANCE_ID

    @pytest.mark.asyncio
    async def test_create_tenant_slug_check_contains_instance_id(self):
        """slug 查重查询参数单独验证"""
        svc = TenantService()
        conn = AsyncMock()

        # slug 查重返回已存在
        slug_check = MagicMock()
        slug_check.first.return_value = MagicMock()  # 非 None 表示存在

        conn.execute = AsyncMock(return_value=slug_check)

        with pytest.raises(AppError) as exc_info:
            await svc.create_tenant(
                conn,
                platform_user_id="pu-001",
                payload={
                    "name": "重复租户",
                    "slug": "dup-slug",
                    "industry": "electronics",
                    "admin_email": "admin@test.com",
                    "admin_password": "pass123",
                    "admin_name": "管理员",
                },
            )

        assert exc_info.value.code == "CONFLICT"

        # 只有第一次 slug 查重被调用
        slug_call = conn.execute.call_args_list[0]
        slug_params = slug_call.args[1]
        assert slug_params["instance_id"] == INSTANCE_ID
        assert slug_params["slug"] == "dup-slug"
