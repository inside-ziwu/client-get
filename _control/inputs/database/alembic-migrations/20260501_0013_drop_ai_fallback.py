"""Drop AI model fallback configuration.

AI scene resolution now depends only on ai_scene_defaults.scene -> model_id.

revision: 20260501_0013
"""

from alembic import op

revision = "20260501_0013"
down_revision = "20260501_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE ai_models DROP COLUMN IF EXISTS model_type;")
    op.get_bind().exec_driver_sql("ALTER TABLE ai_scene_defaults DROP COLUMN IF EXISTS fallback_model_ids;")


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE ai_models
        ADD COLUMN IF NOT EXISTS model_type varchar(40) NOT NULL DEFAULT 'general'
        CHECK (model_type IN ('scoring','email_generation','intelligence_summary','data_analysis','general'));
        """
    )
    op.get_bind().exec_driver_sql(
        "ALTER TABLE ai_scene_defaults ADD COLUMN IF NOT EXISTS fallback_model_ids jsonb NOT NULL DEFAULT '[]';"
    )
