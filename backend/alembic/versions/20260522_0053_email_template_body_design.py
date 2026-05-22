"""email_templates 表增加 body_design jsonb 列。

revision: 20260522_0053
down_revision: 20260522_0052
"""

from alembic import op

revision = "20260522_0053"
down_revision = "20260522_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        ALTER TABLE email_templates
        ADD COLUMN IF NOT EXISTS body_design jsonb;
    """)


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        ALTER TABLE email_templates
        DROP COLUMN IF EXISTS body_design;
    """)
