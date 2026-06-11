"""公司列表查询索引优化。

1. 新建完整函数索引 idx_lxc_entname_eng_lower_full（替代旧 partial index）
2. 补建 waimaotong_raw_companies.sys_company_id B-Tree 索引
3. 删除旧 partial index idx_lx_clean_entname_eng_lower

旧 partial index 带 WHERE entname_eng IS NOT NULL 条件，
PostgreSQL 查询规划器在 LEFT JOIN ON 场景下无法推断该条件被满足，
导致公司列表查询全表扫描（3.6s）。替换为无 WHERE 条件的完整索引后，
规划器可以正常使用 Index Scan。

执行顺序：先建新索引，再删旧索引，避免中间无索引可用的性能窗口。

revision: 20260611_0001
down_revision: 20260610_0001
"""

from alembic import op

revision = "20260611_0001"
down_revision = "20260610_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_lxc_entname_eng_lower_full
            ON lixiaoyun_api_clean_companies (lower(trim(entname_eng)));
    """)

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_wmt_raw_sys_company_id
            ON waimaotong_raw_companies (sys_company_id);
    """)

    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_lx_clean_entname_eng_lower;"
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_lxc_entname_eng_lower_full;"
    )

    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_wmt_raw_sys_company_id;"
    )

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_lx_clean_entname_eng_lower
            ON lixiaoyun_api_clean_companies (lower(trim(entname_eng)))
            WHERE entname_eng IS NOT NULL AND entname_eng != '';
    """)
