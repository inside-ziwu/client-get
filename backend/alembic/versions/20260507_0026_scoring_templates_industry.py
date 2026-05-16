"""C6：scoring_templates 新增 industry 字段，支持按行业分组展示评分模板。

迁移内容：
1. ALTER TABLE scoring_templates ADD COLUMN IF NOT EXISTS industry text NOT NULL DEFAULT 'PCB'

revision: 20260507_0026
down_revision: 20260507_0025
"""

from alembic import op

revision = "20260507_0026"
down_revision = "20260507_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- C6：评分模板新增行业字段，方便按行业分组管理
        ALTER TABLE scoring_templates
            ADD COLUMN IF NOT EXISTS industry text NOT NULL DEFAULT 'PCB';

        -- 创建索引便于按行业检索
        CREATE INDEX IF NOT EXISTS idx_scoring_templates_industry
            ON scoring_templates(industry);
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP INDEX IF EXISTS idx_scoring_templates_industry;

        ALTER TABLE scoring_templates
            DROP COLUMN IF EXISTS industry;
        """
    )
