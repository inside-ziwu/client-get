"""add body_design to platform_email_templates

Revision ID: 20260423_0006
Revises: 20260423_0005
Create Date: 2026-04-23
"""

from alembic import op

revision = "20260423_0006"
down_revision = "20260423_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE platform_email_templates ADD COLUMN IF NOT EXISTS body_design jsonb"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE platform_email_templates DROP COLUMN IF EXISTS body_design"
    )
