from alembic import op

# revision identifiers, used by Alembic.
revision = "20260422_0003"
down_revision = "20260421_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE scoring_jobs (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES tenants(id),
          tenant_company_id uuid NOT NULL REFERENCES tenant_companies(id) ON DELETE CASCADE,
          status varchar(20) NOT NULL CHECK (status IN ('pending','leased','waiting_balance','completed','failed')),
          lease_id uuid,
          lease_owner varchar(100),
          lease_expires_at timestamptz,
          attempt_count int NOT NULL DEFAULT 0,
          last_error text,
          payload jsonb NOT NULL DEFAULT '{}',
          completed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TRIGGER set_updated_at BEFORE UPDATE ON scoring_jobs FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
        CREATE INDEX idx_scoring_jobs_claim ON scoring_jobs(status, lease_expires_at, created_at);
        CREATE UNIQUE INDEX idx_scoring_jobs_unique_active
        ON scoring_jobs(tenant_company_id)
        WHERE completed_at IS NULL AND status IN ('pending','leased','waiting_balance');

        ALTER TABLE scoring_jobs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_scoring_jobs_select ON scoring_jobs
          FOR SELECT USING (tenant_id = current_tenant_id());
        CREATE POLICY tenant_scoring_jobs_write ON scoring_jobs
          FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP POLICY IF EXISTS tenant_scoring_jobs_write ON scoring_jobs;
        DROP POLICY IF EXISTS tenant_scoring_jobs_select ON scoring_jobs;
        DROP TABLE IF EXISTS scoring_jobs CASCADE;
        """
    )
