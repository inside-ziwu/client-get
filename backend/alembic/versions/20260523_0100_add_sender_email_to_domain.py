"""domain_warmup_status 新增 sender_email 字段。

一域名一邮箱，存储完整邮箱格式（如 sales@example.com），可空。

revision: 20260523_0100
down_revision: 20260523_0055
"""

from alembic import op

revision = "20260523_0100"
down_revision = "20260523_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE domain_warmup_status ADD COLUMN IF NOT EXISTS sender_email VARCHAR(255);"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE domain_warmup_status DROP COLUMN IF EXISTS sender_email;"
    )
