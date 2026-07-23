"""清理零使用索引：idx_email_events_type_time、idx_tenant_companies_tags（#61 ⑤ 首批）。

revision: 20260723_0002
down_revision: 20260723_0001

考证（2026-07-23，生产 pg_stat_user_indexes 零扫描 × 全仓查询模式比对）：
- idx_email_events_type_time（20MB）：0021 为「投递监控统计（EmailMonitor 页面）」
  预建，该统计查询从未落地，代码零匹配；表为 webhook 持续写入的活表，
  索引只贡献写放大。
- idx_tenant_companies_tags（GIN，1.1MB）：tags 列只有写入与展示，全仓无
  &&/@>/ANY 过滤查询（#61 ⑤ 点名）。
同表另两个零扫描索引（idx_email_events_email、idx_email_events_tenant_type）
因命中 tenant_hard_delete_service 的低频查询模式，按「任何匹配即保留」原则
本批不动。

风险与回滚：删错的后果是相关查询退化为全表扫（可观测、非事故），downgrade
按生产原定义重建即可（33 万行表分钟级）。
"""

from alembic import op

revision = "20260723_0002"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # DROP INDEX 拿瞬时 ACCESS EXCLUSIVE 锁，繁忙时快速失败而非阻塞业务
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    # 不带 IF EXISTS：生产/开发双库均已核实存在，缺失即状态异常，应报错人工介入
    conn.exec_driver_sql("DROP INDEX public.idx_email_events_type_time")
    conn.exec_driver_sql("DROP INDEX public.idx_tenant_companies_tags")


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    # 定义原样取自 2026-07-23 生产快照（backend/03_database/schema_snapshot.json）
    conn.exec_driver_sql(
        "CREATE INDEX idx_email_events_type_time "
        "ON public.email_events USING btree (event_type, occurred_at DESC)"
    )
    conn.exec_driver_sql(
        "CREATE INDEX idx_tenant_companies_tags "
        "ON public.tenant_companies USING gin (tags)"
    )
