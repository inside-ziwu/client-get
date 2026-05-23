"""删除 email_templates 和 platform_email_templates 的 body_design 列。

迁移到富文本编辑器后该字段已废弃，前端始终传 null。

revision: 20260523_0055
down_revision: 20260523_0054
"""

from alembic import op

revision = "20260523_0055"
down_revision = "20260523_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE email_templates DROP COLUMN IF EXISTS body_design;"
    )
    conn.exec_driver_sql(
        "ALTER TABLE platform_email_templates DROP COLUMN IF EXISTS body_design;"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE email_templates ADD COLUMN IF NOT EXISTS body_design jsonb;"
    )
    conn.exec_driver_sql(
        "ALTER TABLE platform_email_templates ADD COLUMN IF NOT EXISTS body_design jsonb;"
    )
