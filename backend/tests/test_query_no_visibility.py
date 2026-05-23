"""验证 tenant_query_service 已移除 visibility_status 逻辑。"""

import inspect

from app.services.tenant_query_service import TenantQueryService


class TestQueryNoVisibility:
    def test_no_visibility_in_module(self):
        import app.services.tenant_query_service as mod
        source = inspect.getsource(mod)
        assert "visibility_status" not in source

    def test_dashboard_no_visibility(self):
        source = inspect.getsource(TenantQueryService.dashboard_overview)
        assert "visibility_status" not in source
