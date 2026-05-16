"""Drop input_price and output_price from ai_models.

Per-model pricing fields were removed from requirements.
The put_ai_pricing endpoint is already a no-op (see admin_config_service.py).

revision: 20260501_0011
"""

from alembic import op

revision = "20260501_0011"
down_revision = "20260501_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE ai_models DROP COLUMN IF EXISTS input_price;")
    op.get_bind().exec_driver_sql("ALTER TABLE ai_models DROP COLUMN IF EXISTS output_price;")


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS input_price numeric(12,6) NOT NULL DEFAULT 0;"
    )
    op.get_bind().exec_driver_sql(
        "ALTER TABLE ai_models ADD COLUMN IF NOT EXISTS output_price numeric(12,6) NOT NULL DEFAULT 0;"
    )
