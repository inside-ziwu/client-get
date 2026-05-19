"""waimaotong_clean_companies 增加 keyword_master_ids 字段 + 相关索引。

- keyword_master_ids: 物化血缘字段，存储该 wmt 公司关联的所有 keyword_master id
- GIN 索引: 支持 @> 数组包含查询（fan_out 按关键词筛选公司）
- expression index: 支持 lower(trim()) 规范化匹配

revision: 20260519_0047
down_revision: 20260519_0046
"""

from alembic import op

revision = "20260519_0047"
down_revision = "20260519_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            ADD COLUMN IF NOT EXISTS keyword_master_ids UUID[] NOT NULL DEFAULT '{}';
    """)

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_wmt_clean_keyword_master_ids
            ON waimaotong_clean_companies USING gin(keyword_master_ids);
    """)

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_wmt_raw_source_competitor_lower
            ON waimaotong_raw_companies (lower(trim(source_competitor)))
            WHERE source_competitor IS NOT NULL AND source_competitor != '';
    """)

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_lx_clean_entname_eng_lower
            ON lixiaoyun_api_clean_companies (lower(trim(entname_eng)))
            WHERE entname_eng IS NOT NULL AND entname_eng != '';
    """)


def downgrade() -> None:
    conn = op.get_bind()

    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_lx_clean_entname_eng_lower;")
    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_wmt_raw_source_competitor_lower;")
    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_wmt_clean_keyword_master_ids;")
    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            DROP COLUMN IF EXISTS keyword_master_ids;
    """)
