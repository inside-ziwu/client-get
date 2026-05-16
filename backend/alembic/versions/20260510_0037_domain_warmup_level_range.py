"""Allow domain warmup levels to follow active warmup rules.

revision: 20260510_0037
down_revision: 20260510_0036
"""

from alembic import op

revision = "20260510_0037"
down_revision = "20260510_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE domain_warmup_status
          DROP CONSTRAINT IF EXISTS domain_warmup_status_warmup_level_check;

        ALTER TABLE domain_warmup_status
          ADD CONSTRAINT domain_warmup_status_warmup_level_check
          CHECK (warmup_level >= 1);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE domain_warmup_status
          DROP CONSTRAINT IF EXISTS domain_warmup_status_warmup_level_check;

        ALTER TABLE domain_warmup_status
          ADD CONSTRAINT domain_warmup_status_warmup_level_check
          CHECK (warmup_level BETWEEN 1 AND 6);
        """
    )
