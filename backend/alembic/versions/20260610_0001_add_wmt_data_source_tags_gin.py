"""为 WMT 清洗公司来源标签增加 GIN 索引。

revision: 20260610_0001
down_revision: 20260530_0001
"""

from alembic import op

revision = "20260610_0001"
down_revision = "20260530_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_wmt_clean_data_source_tags_gin "
        "ON waimaotong_clean_companies USING gin (data_source_tags jsonb_path_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_wmt_clean_data_source_tags_gin")
