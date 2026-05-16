"""email_events 表补充查询索引（D-041 投递监控优化）。

说明：
email_events 表已在 0001 canonical schema 中建立，本迁移只补充
按 event_type + occurred_at 排序的复合索引，用于投递监控统计查询加速。

现有索引：
  idx_email_events_provider_unique  — 幂等去重
  idx_email_events_email            — 按 email_id 查询

新增索引：
  idx_email_events_type_time        — 按事件类型 + 时间范围统计（EmailMonitor 页面所需）

revision: 20260507_0021
down_revision: 20260507_0020
"""

from alembic import op

revision = "20260507_0021"
# 合并两条分支：链 A (0027) + 链 B (0020)，统一为单头
down_revision = ("20260507_0027", "20260507_0020")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 投递监控统计查询加速索引：按事件类型 + 发生时间倒序
        CREATE INDEX IF NOT EXISTS idx_email_events_type_time
            ON email_events(event_type, occurred_at DESC);

        -- 租户级别统计索引
        CREATE INDEX IF NOT EXISTS idx_email_events_tenant_type
            ON email_events(tenant_id, event_type, occurred_at DESC);
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP INDEX IF EXISTS idx_email_events_tenant_type;
        DROP INDEX IF EXISTS idx_email_events_type_time;
        """
    )
