"""邮件模板同步：去重并创建 partial unique index。

revision: 20260522_0052
down_revision: 20260521_0051
"""

from alembic import op

revision = "20260522_0052"
down_revision = "20260521_0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        DELETE FROM email_templates
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY tenant_id, platform_template_id
                           ORDER BY created_at
                       ) AS rn
                FROM email_templates
                WHERE deleted_at IS NULL
                  AND platform_template_id IS NOT NULL
            ) t
            WHERE t.rn > 1
        );
    """)
    conn.exec_driver_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_email_templates_tenant_platform_active
        ON email_templates (tenant_id, platform_template_id)
        WHERE deleted_at IS NULL AND platform_template_id IS NOT NULL;
    """)


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        DROP INDEX IF EXISTS ix_email_templates_tenant_platform_active;
    """)
