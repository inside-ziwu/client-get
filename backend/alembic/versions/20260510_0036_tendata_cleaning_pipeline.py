"""Align Tendata cleaning and tenant visibility materialization.

revision: 20260510_0036
down_revision: 20260509_0035
"""

from alembic import op

revision = "20260510_0036"
down_revision = "20260509_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE clean_companies
          ADD COLUMN IF NOT EXISTS aliases text[] DEFAULT '{}',
          ADD COLUMN IF NOT EXISTS latest_tendata_summary_at timestamptz;

        ALTER TABLE tenant_companies
          ADD COLUMN IF NOT EXISTS visibility_status text NOT NULL DEFAULT 'hidden';

        ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_visibility_status_check;
        ALTER TABLE tenant_companies
          ADD CONSTRAINT tenant_companies_visibility_status_check
          CHECK (visibility_status IN ('visible','hidden'));

        UPDATE tenant_companies
        SET business_status = 'new'
        WHERE business_status = 'selected';

        ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_business_status_check;
        ALTER TABLE tenant_companies
          ADD CONSTRAINT tenant_companies_business_status_check
          CHECK (business_status IN ('new','in_group','in_plan','contacted','archived'));

        UPDATE tenant_companies tc
        SET business_status = 'in_group'
        WHERE EXISTS (
          SELECT 1
          FROM group_members gm
          WHERE gm.tenant_company_id::text = tc.id::text
        );

        UPDATE tenant_companies tc
        SET visibility_status = CASE
          WHEN EXISTS (
            SELECT 1
            FROM clean_company_keywords cck
            JOIN tenant_keyword tk
              ON tk.keyword_master_id = cck.keyword_master_id
             AND tk.tenant_id = tc.tenant_id
             AND tk.status = 'active'
            WHERE cck.clean_company_id = tc.clean_company_id
          )
          THEN 'visible'
          ELSE 'hidden'
        END;

        DROP INDEX IF EXISTS idx_tenant_companies_tenant_visibility;
        CREATE INDEX idx_tenant_companies_tenant_visibility
          ON tenant_companies(tenant_id, visibility_status, created_at DESC);

        -- Existing data in these operational tables cannot be safely mapped from uuid to bigint.
        -- The first V3 tenant_companies bigint migration rebuilt tenant company IDs, so unmapped
        -- old operational rows are intentionally removed before adding foreign keys.
        DELETE FROM company_scores;
        DELETE FROM group_members;
        DELETE FROM scoring_jobs;

        ALTER TABLE company_scores DROP CONSTRAINT IF EXISTS company_scores_tenant_company_id_fkey;
        ALTER TABLE group_members DROP CONSTRAINT IF EXISTS group_members_tenant_company_id_fkey;
        ALTER TABLE group_members DROP CONSTRAINT IF EXISTS group_members_tenant_contact_id_fkey;
        ALTER TABLE scoring_jobs DROP CONSTRAINT IF EXISTS scoring_jobs_tenant_company_id_fkey;

        DROP INDEX IF EXISTS idx_company_scores_unique_non_retry;
        DROP INDEX IF EXISTS idx_scoring_jobs_unique_active;

        ALTER TABLE company_scores
          ALTER COLUMN tenant_company_id DROP NOT NULL,
          ALTER COLUMN tenant_company_id TYPE bigint USING NULL;
        ALTER TABLE company_scores
          ALTER COLUMN tenant_company_id SET NOT NULL,
          ADD CONSTRAINT company_scores_tenant_company_id_fkey
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id) ON DELETE CASCADE;
        CREATE UNIQUE INDEX idx_company_scores_unique_non_retry
          ON company_scores(tenant_company_id, template_version_id)
          WHERE is_retry = false;

        ALTER TABLE group_members
          ALTER COLUMN tenant_company_id DROP NOT NULL,
          ALTER COLUMN tenant_company_id TYPE bigint USING NULL,
          ALTER COLUMN tenant_contact_id TYPE bigint USING NULL;
        ALTER TABLE group_members
          ALTER COLUMN tenant_company_id SET NOT NULL,
          ADD CONSTRAINT group_members_tenant_company_id_fkey
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id) ON DELETE CASCADE,
          ADD CONSTRAINT group_members_tenant_contact_id_fkey
            FOREIGN KEY (tenant_contact_id) REFERENCES tenant_contacts(id) ON DELETE SET NULL;

        ALTER TABLE scoring_jobs
          ALTER COLUMN tenant_company_id DROP NOT NULL,
          ALTER COLUMN tenant_company_id TYPE bigint USING NULL;
        ALTER TABLE scoring_jobs
          ALTER COLUMN tenant_company_id SET NOT NULL,
          ADD CONSTRAINT scoring_jobs_tenant_company_id_fkey
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id) ON DELETE CASCADE;
        CREATE UNIQUE INDEX idx_scoring_jobs_unique_active
          ON scoring_jobs(tenant_company_id)
          WHERE completed_at IS NULL AND status IN ('pending','leased');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_tenant_companies_tenant_visibility;
        ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_visibility_status_check;
        ALTER TABLE tenant_companies DROP COLUMN IF EXISTS visibility_status;
        ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_business_status_check;
        ALTER TABLE tenant_companies
          ADD CONSTRAINT tenant_companies_business_status_check
          CHECK (business_status IN ('new','selected','in_plan','contacted','archived'));
        ALTER TABLE clean_companies DROP COLUMN IF EXISTS latest_tendata_summary_at;
        ALTER TABLE clean_companies DROP COLUMN IF EXISTS aliases;
        """
    )
