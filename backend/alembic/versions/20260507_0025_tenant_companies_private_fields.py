"""C4：tenant_companies 私有操作字段——调分、调分时间、操作人、调分原因。

迁移内容：
1. 新增 score_adjustment int NOT NULL DEFAULT 0 CHECK (±20)
2. 新增 score_adjusted_at timestamptz
3. 新增 score_adjusted_by uuid REFERENCES users(id) ON DELETE SET NULL
4. 新增 score_adjust_reason text

revision: 20260507_0025
down_revision: 20260507_0017
"""

from alembic import op

revision = "20260507_0025"
down_revision = "20260507_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- C4：添加私有评分调整字段
        ALTER TABLE tenant_companies
            ADD COLUMN IF NOT EXISTS score_adjustment int NOT NULL DEFAULT 0
                CHECK (score_adjustment >= -20 AND score_adjustment <= 20),
            ADD COLUMN IF NOT EXISTS score_adjusted_at timestamptz,
            ADD COLUMN IF NOT EXISTS score_adjusted_by uuid
                REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS score_adjust_reason text;

        -- 创建索引便于快速查询有过手动调分的记录
        CREATE INDEX IF NOT EXISTS idx_tenant_companies_score_adjustment
            ON tenant_companies(tenant_id, score_adjustment)
            WHERE score_adjustment != 0;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 回滚：删除索引和列
        DROP INDEX IF EXISTS idx_tenant_companies_score_adjustment;

        ALTER TABLE tenant_companies
            DROP COLUMN IF EXISTS score_adjust_reason,
            DROP COLUMN IF EXISTS score_adjusted_by,
            DROP COLUMN IF EXISTS score_adjusted_at,
            DROP COLUMN IF EXISTS score_adjustment;
        """
    )
