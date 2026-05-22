"""删除未使用的表：crawl_progress、waimaotong_raw_companies_bak、waimaotong_raw_contacts_bak。

revision: 20260523_0054
down_revision: 20260522_0053
"""

from alembic import op

revision = "20260523_0054"
down_revision = "20260522_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP TABLE IF EXISTS crawl_progress CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS waimaotong_raw_companies_bak CASCADE;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS waimaotong_raw_contacts_bak CASCADE;")


def downgrade() -> None:
    # 这些表已确认无代码引用，不提供回滚重建
    pass
