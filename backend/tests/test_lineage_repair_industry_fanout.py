"""行业 fan-out SQL 与执行顺序测试。"""

import inspect

from app.workers import wmt_lineage_repair


class TestLineageRepairIndustryFanOut:
    """验证关键词采集行业分发符合 OpenSpec 口径。"""

    def test_industry_fan_out_sql_shape(self):
        """行业 fan-out SQL 包含 jsonb、行业归一化、active、分级与幂等逻辑。"""
        sql = str(wmt_lineage_repair._SQL_FAN_OUT_INDUSTRY)
        assert "wc.data_source_tags @>" in sql
        assert """'["外贸通关键词采集"]'::jsonb""" in sql
        assert "lower(trim(t.industry)) = ANY" in sql
        assert "t.status = 'active'" in sql
        assert "missing_contacts" in sql
        assert "insufficient_data" in sql
        assert "ready" in sql
        assert "ON CONFLICT (tenant_id, clean_company_id) DO UPDATE" in sql
        assert "visibility_status" not in sql

    def test_industry_fan_out_runs_before_delete_stale(self):
        """行业 fan-out 必须在清理 stale 关系之前执行。"""
        source = inspect.getsource(wmt_lineage_repair.run_wmt_lineage_repair_on_connection)
        assert source.index("_SQL_FAN_OUT_INDUSTRY") < source.index("_SQL_DELETE_STALE_RELATIONS")

    def test_stats_contains_industry_fan_out(self):
        """执行统计必须返回 industry_fan_out 计数。"""
        source = inspect.getsource(wmt_lineage_repair.run_wmt_lineage_repair_on_connection)
        assert '"industry_fan_out"' in source

    def test_industry_aliases_are_lowercase(self):
        """行业别名必须全小写，匹配时由 lower(trim()) 归一化。"""
        assert wmt_lineage_repair._PCB_INDUSTRY_ALIASES
        assert all(alias == alias.lower() for alias in wmt_lineage_repair._PCB_INDUSTRY_ALIASES)
