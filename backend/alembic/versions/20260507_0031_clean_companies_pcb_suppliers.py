"""clean_companies 新增 pcb_suppliers 列（保留原始供应商列表）。

迁移内容：
1. ALTER TABLE clean_companies ADD COLUMN pcb_suppliers text[] DEFAULT '{}'
2. 用现有 has_china_pcb_supplier 无法回填（布尔→列表无法还原），新列默认空数组即可。
   后续 cleanup_service 写新数据时会正确填充。

revision: 20260507_0031
down_revision: 20260507_0030
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "20260507_0031"
down_revision = "20260507_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clean_companies",
        sa.Column(
            "pcb_suppliers",
            ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("clean_companies", "pcb_suppliers")
