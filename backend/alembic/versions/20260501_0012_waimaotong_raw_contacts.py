"""Create waimaotong_raw_contacts table.

revision: 20260501_0012
"""

from alembic import op

revision = "20260501_0012"
down_revision = "20260501_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE waimaotong_raw_contacts (
          id                bigserial PRIMARY KEY,
          source_contact_id text,
          source_company_id text NOT NULL,
          name              text,
          title             text,
          email             text NOT NULL,
          phone             text,
          task_id           uuid,
          raw_payload       jsonb,
          created_at        timestamptz DEFAULT now(),
          last_seen_at      timestamptz DEFAULT now()
        );
        """
    )
    op.get_bind().exec_driver_sql(
        "CREATE INDEX idx_wmt_raw_contacts_company ON waimaotong_raw_contacts(source_company_id);"
    )
    op.get_bind().exec_driver_sql(
        "CREATE INDEX idx_wmt_raw_contacts_email_lower ON waimaotong_raw_contacts(lower(email));"
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS waimaotong_raw_contacts;")
