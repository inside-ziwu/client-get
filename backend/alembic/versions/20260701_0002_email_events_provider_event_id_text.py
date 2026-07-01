"""放宽 email_events.provider_event_id 长度限制。

EngageLab webhook 的 provider_event_id 由 message_id、事件类型和时间戳拼接而成，
真实 message_id 可能包含较长邮箱地址，超过 varchar(100) 后会导致事件入库失败。

revision: 20260701_0002
down_revision: 20260701_0001
"""

from alembic import op

revision = "20260701_0002"
down_revision = "20260701_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE email_events
          ALTER COLUMN provider_event_id TYPE text;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM email_events
            WHERE provider_event_id IS NOT NULL
              AND length(provider_event_id) > 100
          ) THEN
            RAISE EXCEPTION 'cannot downgrade email_events.provider_event_id to varchar(100): values longer than 100 exist';
          END IF;
        END $$;

        ALTER TABLE email_events
          ALTER COLUMN provider_event_id TYPE varchar(100);
        """
    )
