from alembic import op

revision = "20260429_0008"
down_revision = "20260429_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE competitor_companies
            ADD COLUMN IF NOT EXISTS source_id       varchar(255),
            ADD COLUMN IF NOT EXISTS company_name_en varchar(500),
            ADD COLUMN IF NOT EXISTS esdate          varchar(50),
            ADD COLUMN IF NOT EXISTS legalperson     varchar(255),
            ADD COLUMN IF NOT EXISTS reg_capital     varchar(255),
            ADD COLUMN IF NOT EXISTS paid_capital    varchar(255),
            ADD COLUMN IF NOT EXISTS reg_address     text,
            ADD COLUMN IF NOT EXISTS contact_address text,
            ADD COLUMN IF NOT EXISTS employee_scale  varchar(100),
            ADD COLUMN IF NOT EXISTS uncid           varchar(100),
            ADD COLUMN IF NOT EXISTS updated_at      timestamptz NOT NULL DEFAULT now();

        CREATE UNIQUE INDEX IF NOT EXISTS uq_competitor_companies_source
            ON competitor_companies (tenant_id, source_type, source_id)
            WHERE source_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS competitor_contacts (
            id           uuid PRIMARY KEY,
            competitor_id uuid NOT NULL REFERENCES competitor_companies(id) ON DELETE CASCADE,
            tenant_id    uuid NOT NULL REFERENCES tenants(id),
            name         varchar(255),
            phone        varchar(100),
            position     varchar(255),
            email        varchar(500),
            raw_data     jsonb NOT NULL DEFAULT '{}',
            created_at   timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_competitor_contacts_competitor
            ON competitor_contacts (competitor_id);
        CREATE INDEX IF NOT EXISTS idx_competitor_contacts_tenant
            ON competitor_contacts (tenant_id);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_competitor_contacts_phone
            ON competitor_contacts (competitor_id, phone)
            WHERE phone IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS competitor_contacts CASCADE;
        DROP INDEX IF EXISTS uq_competitor_companies_source;
        ALTER TABLE competitor_companies
            DROP COLUMN IF EXISTS updated_at,
            DROP COLUMN IF EXISTS uncid,
            DROP COLUMN IF EXISTS employee_scale,
            DROP COLUMN IF EXISTS contact_address,
            DROP COLUMN IF EXISTS reg_address,
            DROP COLUMN IF EXISTS paid_capital,
            DROP COLUMN IF EXISTS reg_capital,
            DROP COLUMN IF EXISTS legalperson,
            DROP COLUMN IF EXISTS esdate,
            DROP COLUMN IF EXISTS company_name_en,
            DROP COLUMN IF EXISTS source_id;
        """
    )
