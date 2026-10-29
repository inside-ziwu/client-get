"""把 emails.engagelab_message_id 扩为 TEXT，并为发送锁补上接单阶段。

revision: 20261028_0001
down_revision: 20260824_0002

依据：2026-10-26/27 第二实例成功接单后，101/107 字符的 EngageLab email_id
写不进 varchar(100)，整笔 mark_email_sent 回滚并被当成失败重试。官方成功
响应的 email_ids 会拼接收件邮箱（deliverlies 文档示例即超过 100）。截断会
破坏 webhook 与对账的等值匹配。

email_send_locks 新增 dispatching / accepted_pending / uncertain，以及
provider_message_id、provider_accepted_at、dispatch_started_at、
quota_usage_date、finalize_not_before。CHECK 名以 schema_snapshot 的 email_send_locks_status_check
为准。status 仍是 varchar(20)：accepted_pending 为 16 字符，不扩列宽。

父表 ALTER COLUMN TYPE 会作用于全部分区；varchar→text 在 PostgreSQL 中为
二进制兼容变更。A、B 共库，锁范围不按单实例估算。

downgrade 在存在超长 ID、新状态或新列事实时拒绝，不截断、不丢事实。
"""

from alembic import op

revision = "20261028_0001"
down_revision = "20260824_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        SET LOCAL lock_timeout = '5s';
        SET LOCAL statement_timeout = '30s';

        ALTER TABLE emails
          ALTER COLUMN engagelab_message_id TYPE text;

        ALTER TABLE email_send_locks
          ADD COLUMN provider_message_id text,
          ADD COLUMN provider_accepted_at timestamptz,
          ADD COLUMN dispatch_started_at timestamptz,
          ADD COLUMN quota_usage_date date,
          ADD COLUMN finalize_not_before timestamptz;

        ALTER TABLE email_send_locks
          DROP CONSTRAINT email_send_locks_status_check;

        ALTER TABLE email_send_locks
          ADD CONSTRAINT email_send_locks_status_check
          CHECK (status IN (
            'locked', 'sent', 'failed', 'released',
            'dispatching', 'accepted_pending', 'uncertain'
          ));

        CREATE INDEX idx_email_send_locks_accepted_pending
          ON email_send_locks (provider_accepted_at, id)
          WHERE status = 'accepted_pending';

        CREATE INDEX idx_email_send_locks_dispatching
          ON email_send_locks (dispatch_started_at)
          WHERE status = 'dispatching';

        CREATE INDEX idx_email_send_locks_unsent_locked
          ON email_send_locks (locked_at)
          WHERE status = 'locked'
            AND quota_usage_date IS NOT NULL
            AND dispatch_started_at IS NULL;

        CREATE INDEX idx_email_send_locks_finalize_due
          ON email_send_locks (finalize_not_before, provider_accepted_at, id)
          WHERE status = 'accepted_pending';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        SET LOCAL lock_timeout = '5s';
        SET LOCAL statement_timeout = '30s';

        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM emails
            WHERE engagelab_message_id IS NOT NULL
              AND length(engagelab_message_id) > 100
          ) THEN
            RAISE EXCEPTION
              'cannot downgrade emails.engagelab_message_id'
              ' to varchar(100): values longer than 100 exist';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM email_send_locks
            WHERE status IN ('dispatching', 'accepted_pending', 'uncertain')
          ) THEN
            RAISE EXCEPTION 'cannot downgrade email_send_locks: dispatch states still present';
          END IF;

          IF EXISTS (
            SELECT 1
            FROM email_send_locks
            WHERE provider_message_id IS NOT NULL
               OR provider_accepted_at IS NOT NULL
               OR dispatch_started_at IS NOT NULL
               OR quota_usage_date IS NOT NULL
               OR finalize_not_before IS NOT NULL
          ) THEN
            RAISE EXCEPTION 'cannot downgrade email_send_locks: dispatch facts still present';
          END IF;
        END $$;

        DROP INDEX idx_email_send_locks_finalize_due;
        DROP INDEX idx_email_send_locks_unsent_locked;
        DROP INDEX idx_email_send_locks_dispatching;
        DROP INDEX idx_email_send_locks_accepted_pending;

        ALTER TABLE email_send_locks
          DROP CONSTRAINT email_send_locks_status_check;

        ALTER TABLE email_send_locks
          DROP COLUMN finalize_not_before,
          DROP COLUMN quota_usage_date,
          DROP COLUMN dispatch_started_at,
          DROP COLUMN provider_accepted_at,
          DROP COLUMN provider_message_id;

        ALTER TABLE email_send_locks
          ADD CONSTRAINT email_send_locks_status_check
          CHECK (status IN ('locked', 'sent', 'failed', 'released'));

        ALTER TABLE emails
          ALTER COLUMN engagelab_message_id TYPE varchar(100);
        """
    )
