"""add task_type and context to collection_tasks

Revision ID: 20260429_0007
Revises: 20260423_0006_email_template_design
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa

revision = "20260429_0007"
down_revision = "20260423_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE collection_tasks
            ADD COLUMN task_type varchar(50) NOT NULL DEFAULT 'competitor_search',
            ADD COLUMN context jsonb NOT NULL DEFAULT '{}';
        """
    )
    op.execute(
        """
        CREATE INDEX idx_collection_tasks_type ON collection_tasks(task_type, status)
        WHERE status = 'pending';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_collection_tasks_type;")
    op.execute(
        """
        ALTER TABLE collection_tasks
            DROP COLUMN IF EXISTS task_type,
            DROP COLUMN IF EXISTS context;
        """
    )
