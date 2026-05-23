"""验证 fan_out 模块已移除 visibility_status 逻辑。"""

import importlib
import inspect
import textwrap

import pytest

from app.workers import fan_out


class TestFanOutNoVisibility:
    def test_module_has_no_hide_function(self):
        assert not hasattr(fan_out, "hide_tenant_companies_for_cancelled_keyword")

    def test_run_fan_out_source_no_visibility(self):
        source = inspect.getsource(fan_out.run_fan_out_for_tenant_keyword)
        assert "visibility_status" not in source

    def test_on_conflict_updates_only_data_status(self):
        source = inspect.getsource(fan_out.run_fan_out_for_tenant_keyword)
        assert "data_status" in source
        assert "updated_at" in source
        assert "SET visibility_status" not in source
