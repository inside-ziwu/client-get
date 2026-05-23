"""tenant_companies 移除 visibility_status 列。

该列默认 'hidden'，由 fan-out 写 'visible'；现已确认所有查询
不再依赖此列，直接 DROP。4 个 FK 引用表已有 ON DELETE CASCADE，
stale 关系改为 DELETE 而非 UPDATE hidden。

revision: 20260523_0101
down_revision: 20260523_0100
"""

from alembic import op

revision = "20260523_0101"
down_revision = "20260523_0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE tenant_companies DROP COLUMN IF EXISTS visibility_status;"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE tenant_companies ADD COLUMN IF NOT EXISTS visibility_status VARCHAR(20) DEFAULT 'visible';"
    )
