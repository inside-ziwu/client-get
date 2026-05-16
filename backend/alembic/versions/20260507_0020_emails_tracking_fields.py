"""D-041 邮件追踪字段：向 emails 表添加开信追踪、退信类型、垃圾举报、退订等字段。

迁移内容：
1. emails 表加 first_opened_at  — 首次打开时间（COALESCE 逻辑用）
2. emails 表加 open_count       — 累计打开次数（webhook 每次 open 事件 +1）
3. emails 表加 soft_bounce      — 软退信标志（bounce_type='soft'）
4. emails 表加 invalid_email    — 无效邮箱标志
5. emails 表加 report_spam      — 被举报垃圾邮件标志
6. emails 表加 unsubscribed     — 退订标志（区别于 status 字段用于聚合统计）
7. 加相关索引（统计查询加速）

revision: 20260507_0020
down_revision: 20260507_0029
"""

from alembic import op

revision = "20260507_0020"
down_revision = "20260507_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 1. 首次打开时间：webhook open 事件时用 COALESCE 回写（第一次打开才写入）
        ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS first_opened_at timestamptz;

        -- 2. 累计打开次数：每次 open webhook 都递增
        ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS open_count int NOT NULL DEFAULT 0;

        -- 3. 软退信标志：bounce_type='soft' 时置 true
        ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS soft_bounce bool NOT NULL DEFAULT false;

        -- 4. 无效邮箱标志：bounce_type='invalid' 或类似时置 true
        ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS invalid_email bool NOT NULL DEFAULT false;

        -- 5. 举报垃圾邮件标志：spam/complained 事件时置 true
        ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS report_spam bool NOT NULL DEFAULT false;

        -- 6. 退订标志：unsubscribe 事件时置 true（用于监控统计，与 status 字段联合使用）
        ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS unsubscribed bool NOT NULL DEFAULT false;

        -- 7. 统计查询加速索引
        CREATE INDEX IF NOT EXISTS idx_emails_open_tracking
            ON emails(tenant_id, first_opened_at)
            WHERE first_opened_at IS NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_emails_delivery_flags
            ON emails(tenant_id, soft_bounce, report_spam, unsubscribed)
            WHERE soft_bounce OR report_spam OR unsubscribed;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP INDEX IF EXISTS idx_emails_delivery_flags;
        DROP INDEX IF EXISTS idx_emails_open_tracking;

        ALTER TABLE emails DROP COLUMN IF EXISTS unsubscribed;
        ALTER TABLE emails DROP COLUMN IF EXISTS report_spam;
        ALTER TABLE emails DROP COLUMN IF EXISTS invalid_email;
        ALTER TABLE emails DROP COLUMN IF EXISTS soft_bounce;
        ALTER TABLE emails DROP COLUMN IF EXISTS open_count;
        ALTER TABLE emails DROP COLUMN IF EXISTS first_opened_at;
        """
    )
