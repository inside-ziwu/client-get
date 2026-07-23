"""tenant_companies.score_adjustment 幽灵列转正（#61 ②）。

revision: 20260723_0001
down_revision: 20260714_0001

背景：该列（租户人工分数修正，±20，tenant_ops_service 读写）在 0034 重建
tenant_companies 时被抹掉，随后被带外 ALTER TABLE 加回生产/开发库，从未进入
迁移链——按迁移链从零建出的库缺此列，代码 UPDATE 即报错。本迁移把它记回
账本：存量库上 IF NOT EXISTS 为 no-op（零数据变更），空库重放时创建。
列定义（INTEGER NOT NULL DEFAULT 0）逐字取自 2026-07-22 生产快照实查，
生产/开发双库已核对一致（backend/03_database/schema_snapshot.json）。
"""

from alembic import op

revision = "20260723_0001"
down_revision = "20260714_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 列已存在时同样需要瞬时 ACCESS EXCLUSIVE 锁做目录检查，超时快速失败而非阻塞业务
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    conn.exec_driver_sql(
        "ALTER TABLE public.tenant_companies "
        "ADD COLUMN IF NOT EXISTS score_adjustment INTEGER NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    # 列在本迁移之前就存在于所有存量库且承载业务数据（人工分数修正），
    # 回滚账本不应删列删数据；空库场景如需还原请另建前向迁移。
    pass
