"""调整励销云每日 stage1 采集上限为 1000。

revision: 20260507_0032
down_revision: 20260507_0031
"""

from alembic import op

revision = "20260507_0032"
down_revision = "20260507_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE collection_keywords
          ALTER COLUMN daily_stage1_limit SET DEFAULT 1000;

        UPDATE collection_keywords
        SET daily_stage1_limit = 1000,
            updated_at = now()
        WHERE daily_stage1_limit IS NULL
           OR daily_stage1_limit = 30;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE collection_keywords
          ALTER COLUMN daily_stage1_limit SET DEFAULT 30;

        UPDATE collection_keywords
        SET daily_stage1_limit = 30,
            updated_at = now()
        WHERE daily_stage1_limit = 1000;
        """
    )
