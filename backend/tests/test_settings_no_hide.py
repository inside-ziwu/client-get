"""验证 tenant_settings_service 已移除 hide 函数调用。"""

import inspect

from app.services.tenant_settings_service import TenantSettingsService


class TestSettingsNoHide:
    def test_no_hide_import(self):
        import app.services.tenant_settings_service as mod
        source = inspect.getsource(mod)
        assert "hide_tenant_companies_for_cancelled_keyword" not in source

    def test_update_keyword_no_hide(self):
        source = inspect.getsource(TenantSettingsService.update_keyword)
        assert "hide" not in source

    def test_delete_keyword_no_hide(self):
        source = inspect.getsource(TenantSettingsService.delete_keyword)
        assert "hide" not in source
