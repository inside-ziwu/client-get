"""Align tenant business status semantics.

revision: 20260510_0038
down_revision: 20260510_0037
"""

from alembic import op

revision = "20260510_0038"
down_revision = "20260510_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE tenant_companies
        SET business_status = 'new'
        WHERE business_status = 'archived';

        ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_business_status_check;
        ALTER TABLE tenant_companies
          ADD CONSTRAINT tenant_companies_business_status_check
          CHECK (business_status IN ('new','in_group','in_plan','contacted'));

        -- V3 rebuilt tenant company/contact identities as bigint. Old sending runtime rows
        -- cannot be mapped safely from UUID references, so clear runtime state before
        -- aligning the association columns.
        DELETE FROM email_send_locks;
        DELETE FROM email_events;
        DELETE FROM emails;
        DELETE FROM sequence_enrollments;
        DELETE FROM sending_plan_recipients;

        ALTER TABLE emails DROP CONSTRAINT IF EXISTS emails_tenant_contact_id_fkey;
        ALTER TABLE sending_plan_recipients DROP CONSTRAINT IF EXISTS sending_plan_recipients_tenant_company_id_fkey;
        ALTER TABLE sending_plan_recipients DROP CONSTRAINT IF EXISTS sending_plan_recipients_tenant_contact_id_fkey;
        ALTER TABLE sequence_enrollments DROP CONSTRAINT IF EXISTS sequence_enrollments_tenant_contact_id_fkey;

        ALTER TABLE sending_plan_recipients
          ALTER COLUMN tenant_company_id TYPE bigint USING NULL,
          ALTER COLUMN tenant_contact_id TYPE bigint USING NULL;
        ALTER TABLE sequence_enrollments
          ALTER COLUMN tenant_contact_id TYPE bigint USING NULL;
        ALTER TABLE emails
          ALTER COLUMN tenant_contact_id TYPE bigint USING NULL;

        ALTER TABLE sending_plan_recipients
          ADD CONSTRAINT sending_plan_recipients_tenant_company_id_fkey
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id) ON DELETE CASCADE,
          ADD CONSTRAINT sending_plan_recipients_tenant_contact_id_fkey
            FOREIGN KEY (tenant_contact_id) REFERENCES tenant_contacts(id) ON DELETE CASCADE;
        ALTER TABLE sequence_enrollments
          ADD CONSTRAINT sequence_enrollments_tenant_contact_id_fkey
            FOREIGN KEY (tenant_contact_id) REFERENCES tenant_contacts(id) ON DELETE CASCADE;
        ALTER TABLE emails
          ADD CONSTRAINT emails_tenant_contact_id_fkey
            FOREIGN KEY (tenant_contact_id) REFERENCES tenant_contacts(id) ON DELETE CASCADE;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_business_status_check;
        ALTER TABLE tenant_companies
          ADD CONSTRAINT tenant_companies_business_status_check
          CHECK (business_status IN ('new','in_group','in_plan','contacted','archived'));

        DELETE FROM email_send_locks;
        DELETE FROM email_events;
        DELETE FROM emails;
        DELETE FROM sequence_enrollments;
        DELETE FROM sending_plan_recipients;

        ALTER TABLE emails DROP CONSTRAINT IF EXISTS emails_tenant_contact_id_fkey;
        ALTER TABLE sending_plan_recipients DROP CONSTRAINT IF EXISTS sending_plan_recipients_tenant_company_id_fkey;
        ALTER TABLE sending_plan_recipients DROP CONSTRAINT IF EXISTS sending_plan_recipients_tenant_contact_id_fkey;
        ALTER TABLE sequence_enrollments DROP CONSTRAINT IF EXISTS sequence_enrollments_tenant_contact_id_fkey;

        ALTER TABLE sending_plan_recipients
          ALTER COLUMN tenant_company_id TYPE uuid USING NULL,
          ALTER COLUMN tenant_contact_id TYPE uuid USING NULL;
        ALTER TABLE sequence_enrollments
          ALTER COLUMN tenant_contact_id TYPE uuid USING NULL;
        ALTER TABLE emails
          ALTER COLUMN tenant_contact_id TYPE uuid USING NULL;
        """
    )
