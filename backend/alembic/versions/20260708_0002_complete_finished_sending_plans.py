"""回填已完成的发送计划状态。

revision: 20260708_0002
down_revision: 20260708_0001
"""

from alembic import op

revision = "20260708_0002"
down_revision = "20260708_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        UPDATE sending_plans sp
        SET status = 'completed',
            completed_at = COALESCE(sp.completed_at, now()),
            updated_at = now()
        WHERE sp.status = 'running'
          AND EXISTS (
            SELECT 1
            FROM sequence_enrollments se
            WHERE se.plan_id = sp.id
          )
          AND NOT EXISTS (
            SELECT 1
            FROM sequence_enrollments se
            WHERE se.plan_id = sp.id
              AND se.status IN ('active', 'paused')
          );
        """
    )


def downgrade() -> None:
    pass
