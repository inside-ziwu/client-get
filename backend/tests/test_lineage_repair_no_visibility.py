"""验证 wmt_lineage_repair 已移除 visibility_status 逻辑。"""

from app.workers import wmt_lineage_repair


class TestLineageRepairNoVisibility:
    def test_fan_out_sql_no_visibility(self):
        sql = str(wmt_lineage_repair._SQL_FAN_OUT_FULL_POOL)
        assert "visibility_status" not in sql

    def test_stale_sql_is_delete(self):
        sql = str(wmt_lineage_repair._SQL_DELETE_STALE_RELATIONS)
        assert "DELETE" in sql.upper()
        assert "UPDATE" not in sql.upper()

    def test_active_join_count_no_visibility(self):
        sql = str(wmt_lineage_repair._SQL_ACTIVE_RELATION_COUNT)
        assert "visibility_status" not in sql

    def test_no_old_sql_names(self):
        assert not hasattr(wmt_lineage_repair, "_SQL_HIDE_STALE_RELATIONS")
        assert not hasattr(wmt_lineage_repair, "_SQL_VISIBLE_JOIN_COUNT")
