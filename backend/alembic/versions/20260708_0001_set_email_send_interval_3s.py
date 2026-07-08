"""发送计划默认发送间隔改为 3 秒。

revision: 20260708_0001
down_revision: 20260625_0100
"""

from alembic import op

revision = "20260708_0001"
down_revision = "20260625_0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sending_plans
          ALTER COLUMN send_strategy SET DEFAULT '{"interval_seconds":[3,3]}'::jsonb;
        """
    )
    conn.exec_driver_sql(
        """
        UPDATE sending_plans
        SET send_strategy = jsonb_set(
              COALESCE(send_strategy, '{}'::jsonb),
              '{interval_seconds}',
              '[3,3]'::jsonb,
              true
            )
        WHERE send_strategy IS NULL
           OR send_strategy->'interval_seconds' IS DISTINCT FROM '[3,3]'::jsonb;
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sending_plans
          ALTER COLUMN send_strategy SET DEFAULT '{"interval_seconds":[1,1]}'::jsonb;
        """
    )
    # 不自动恢复既有计划数据：旧区间可能来自用户显式配置或历史默认，无法可靠区分。
