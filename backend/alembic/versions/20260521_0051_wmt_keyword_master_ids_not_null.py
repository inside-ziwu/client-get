"""修复 WMT keyword_master_ids 默认值与 NULL 历史数据。

revision: 20260521_0051
down_revision: 20260520_0050
"""

from alembic import op

revision = "20260521_0051"
down_revision = "20260520_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            ALTER COLUMN keyword_master_ids SET DEFAULT '{}'::uuid[];
    """)
    conn.exec_driver_sql("""
        UPDATE waimaotong_clean_companies
        SET keyword_master_ids = '{}'::uuid[]
        WHERE keyword_master_ids IS NULL;
    """)
    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            ALTER COLUMN keyword_master_ids SET NOT NULL;
    """)


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            ALTER COLUMN keyword_master_ids DROP NOT NULL,
            ALTER COLUMN keyword_master_ids DROP DEFAULT;
    """)
