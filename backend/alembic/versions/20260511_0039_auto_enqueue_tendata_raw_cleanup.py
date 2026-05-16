"""Auto-enqueue Tendata raw company cleanup.

revision: 20260511_0039
down_revision: 20260510_0038
"""

from alembic import op

revision = "20260511_0039"
down_revision = "20260510_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enqueue_tendata_raw_company_cleanup()
        RETURNS trigger AS $$
        BEGIN
          INSERT INTO cleanup_queue (raw_table, raw_row_id, status)
          VALUES ('tendata_raw_companies', NEW.id, 'pending')
          ON CONFLICT (raw_table, raw_row_id) DO NOTHING;

          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS tendata_raw_companies_enqueue_cleanup_after_insert
          ON tendata_raw_companies;

        CREATE TRIGGER tendata_raw_companies_enqueue_cleanup_after_insert
        AFTER INSERT ON tendata_raw_companies
        FOR EACH ROW
        EXECUTE FUNCTION enqueue_tendata_raw_company_cleanup();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS tendata_raw_companies_enqueue_cleanup_after_insert
          ON tendata_raw_companies;
        DROP FUNCTION IF EXISTS enqueue_tendata_raw_company_cleanup();
        """
    )
