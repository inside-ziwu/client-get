"""验证 tenant_ops_service 已移除 visibility_status 逻辑。"""

import inspect

from app.services.tenant_ops_service import TenantOpsService


class TestOpsNoVisibility:
    def test_no_visibility_in_module(self):
        source = inspect.getsource(TenantOpsService)
        assert "visibility_status" not in source

    def test_assert_function_renamed(self):
        assert hasattr(TenantOpsService, "_assert_tenant_company_exists")
        assert not hasattr(TenantOpsService, "_assert_visible_tenant_company")

    def test_assert_function_no_visibility_check(self):
        source = inspect.getsource(TenantOpsService._assert_tenant_company_exists)
        assert "visibility_status" not in source
