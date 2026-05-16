"""关键词主表：建立 keyword_master 和 tenant_keyword 表。

迁移内容：
1. 创建 keyword_master 表（全平台去重关键词主库）
2. 创建 tenant_keyword 关联表（租户订阅的关键词列表）

revision: 20260507_0016
down_revision: 20260507_0015
"""

from alembic import op

revision = "20260507_0016"
down_revision = "20260507_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        -- 1. 关键词主表：全平台去重后的关键词规范库
        CREATE TABLE keyword_master (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            keyword             text NOT NULL,
            keyword_normalized  text NOT NULL UNIQUE,
            created_at          timestamptz NOT NULL DEFAULT now()
        );
        CREATE UNIQUE INDEX uq_keyword_master_normalized
            ON keyword_master(keyword_normalized);

        -- 2. 租户-关键词关联表：记录每个租户订阅了哪些关键词
        CREATE TABLE tenant_keyword (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            keyword_master_id   uuid NOT NULL REFERENCES keyword_master(id) ON DELETE CASCADE,
            created_at          timestamptz NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, keyword_master_id)
        );
        CREATE INDEX idx_tenant_keyword_tenant
            ON tenant_keyword(tenant_id);
        CREATE INDEX idx_tenant_keyword_master
            ON tenant_keyword(keyword_master_id);
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP TABLE IF EXISTS tenant_keyword;
        DROP TABLE IF EXISTS keyword_master;
        """
    )
