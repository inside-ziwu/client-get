"""全池 tenant_companies 修复 SQL 口径测试。"""

from app.workers import wmt_lineage_repair


class TestFullPoolFanOut:
    """验证 PCB 租户共享客户池，仅排除手工私有行。"""

    def test_full_pool_sql_shape(self):
        sql = str(wmt_lineage_repair._SQL_FAN_OUT_FULL_POOL)

        assert "JOIN waimaotong_clean_companies wc" in sql
        assert "t.status = 'active'" in sql
        assert "lower(trim(t.industry)) = ANY" in sql
        assert "t.instance_id = :instance_id" in sql
        assert "wc.source_id IS NULL OR wc.source_id NOT LIKE 'manual-%'" in sql
        assert "data_source_tags" not in sql
        assert "keyword_master_ids" not in sql
        assert "tenant_keyword" not in sql
        assert "RETURNING" not in sql
        assert "ON CONFLICT (tenant_id, clean_company_id) DO UPDATE" in sql

    def test_stale_cleanup_is_instance_scoped(self):
        sql = str(wmt_lineage_repair._SQL_DELETE_STALE_RELATIONS)

        assert "USING tenants t" in sql
        assert "t.id = tc.tenant_id" in sql
        assert "t.instance_id = :instance_id" in sql
        assert "RETURNING" not in sql

    def test_active_relation_count_is_instance_scoped(self):
        sql = str(wmt_lineage_repair._SQL_ACTIVE_RELATION_COUNT)
        assert "JOIN tenants t" in sql
        assert "t.instance_id = :instance_id" in sql

    def test_old_keyword_lineage_sql_is_removed(self):
        for name in (
            "_SQL_NORMALIZE_KEYWORD_MASTER_IDS",
            "_SQL_BACKFILL_CLEAN_PATH",
            "_SQL_BACKFILL_RAW_FALLBACK",
            "_SQL_FAN_OUT_ACTIVE_KEYWORDS",
            "_SQL_FAN_OUT_INDUSTRY",
            "_SQL_UNRESOLVED_COUNT",
        ):
            assert not hasattr(wmt_lineage_repair, name)

    def test_industry_aliases_are_lowercase(self):
        assert wmt_lineage_repair._PCB_INDUSTRY_ALIASES
        assert all(alias == alias.lower() for alias in wmt_lineage_repair._PCB_INDUSTRY_ALIASES)
