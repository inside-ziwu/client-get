"""清理发送策略中未使用的旧字段默认值。

revision: 20260529_0002
down_revision: 20260529_0001
"""

from alembic import op

revision = "20260529_0002"
down_revision = "20260529_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sending_plans
          ALTER COLUMN send_strategy SET DEFAULT '{"interval_seconds":[30,120]}'::jsonb;
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sending_plans
          ALTER COLUMN send_strategy SET DEFAULT '{"timezone_aware":true,"preferred_hours":[9,17],"daily_limit":100,"interval_seconds":[30,120]}'::jsonb;
        """
    )
