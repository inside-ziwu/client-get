"""为 waimaotong_raw_companies.sys_company_id 增加 btree 索引，加速公司列表 LEFT JOIN。

revision: 20260610_0002
down_revision: 20260610_0001
"""

from alembic import op

revision = "20260610_0002"
down_revision = "20260610_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_wmt_raw_sys_company_id "
        "ON waimaotong_raw_companies USING btree (sys_company_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_wmt_raw_sys_company_id")
