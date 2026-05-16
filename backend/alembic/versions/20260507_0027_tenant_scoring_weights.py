"""C6：创建 tenant_scoring_weights 表，支持租户对评分模板各维度自定义权重。

迁移内容：
1. CREATE TABLE tenant_scoring_weights (id, tenant_id, template_id, dimension, weight, created_at, updated_at)
2. UNIQUE(tenant_id, template_id, dimension)

revision: 20260507_0027
down_revision: 20260507_0026
"""

from alembic import op

revision = "20260507_0027"
down_revision = "20260507_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- C6：租户评分权重自定义表
        CREATE TABLE IF NOT EXISTS tenant_scoring_weights (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            template_id uuid NOT NULL REFERENCES scoring_templates(id) ON DELETE CASCADE,
            dimension   text NOT NULL,
            weight      numeric(5,2) NOT NULL DEFAULT 1.0 CHECK (weight >= 0),
            created_at  timestamptz NOT NULL DEFAULT now(),
            updated_at  timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, template_id, dimension)
        );

        -- 更新时间自动维护触发器
        CREATE TRIGGER set_updated_at
            BEFORE UPDATE ON tenant_scoring_weights
            FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

        -- 按 tenant + template 查询索引
        CREATE INDEX IF NOT EXISTS idx_tenant_scoring_weights_tenant_template
            ON tenant_scoring_weights(tenant_id, template_id);

        -- RLS：租户只能管理自己的权重
        ALTER TABLE tenant_scoring_weights ENABLE ROW LEVEL SECURITY;

        CREATE POLICY tenant_scoring_weights_select ON tenant_scoring_weights
            FOR SELECT USING (tenant_id = current_tenant_id());

        CREATE POLICY tenant_scoring_weights_write ON tenant_scoring_weights
            FOR ALL USING (tenant_id = current_tenant_id())
            WITH CHECK (tenant_id = current_tenant_id());
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP TABLE IF EXISTS tenant_scoring_weights;
        """
    )
