"""users 表新增 test_email 字段。

每用户独立维护的测试邮箱地址，用于邮件模板测试发送。

revision: 20260525_0100
down_revision: 20260523_0102
"""

from alembic import op

revision = "20260525_0100"
down_revision = "20260523_0102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS test_email VARCHAR(255);"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE users DROP COLUMN IF EXISTS test_email;"
    )
