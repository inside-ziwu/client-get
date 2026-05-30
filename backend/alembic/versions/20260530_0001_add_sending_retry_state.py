"""为发送重试增加 enrollment 状态字段。

revision: 20260530_0001
down_revision: 20260529_0005
"""

from alembic import op

revision = "20260530_0001"
down_revision = "20260529_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          ADD COLUMN IF NOT EXISTS send_attempt_count int NOT NULL DEFAULT 0;
        """
    )
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          DROP CONSTRAINT IF EXISTS sequence_enrollments_status_check;
        """
    )
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          ADD CONSTRAINT sequence_enrollments_status_check
          CHECK (status IN (
            'active',
            'completed',
            'replied',
            'bounced',
            'unsubscribed',
            'paused',
            'cancelled',
            'failed'
          ));
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        UPDATE sequence_enrollments
        SET status = 'cancelled'
        WHERE status = 'failed';
        """
    )
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          DROP CONSTRAINT IF EXISTS sequence_enrollments_status_check;
        """
    )
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          ADD CONSTRAINT sequence_enrollments_status_check
          CHECK (status IN (
            'active',
            'completed',
            'replied',
            'bounced',
            'unsubscribed',
            'paused',
            'cancelled'
          ));
        """
    )
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          DROP COLUMN IF EXISTS send_attempt_count;
        """
    )
