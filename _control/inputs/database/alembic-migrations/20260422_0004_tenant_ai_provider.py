from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260422_0004"
down_revision = "20260422_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "tenant_ai_provider_configs" not in tables:
        op.execute(
            """
            CREATE TABLE tenant_ai_provider_configs (
              id uuid PRIMARY KEY,
              tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
              provider varchar(40) NOT NULL CHECK (provider IN ('openrouter')),
              api_key_encrypted text NOT NULL,
              encryption_key_version int NOT NULL DEFAULT 1,
              configured_by_user_id uuid REFERENCES users(id),
              configured_by_platform_user_id uuid REFERENCES platform_users(id),
              last_rotated_at timestamptz NOT NULL DEFAULT now(),
              balance_status varchar(30) NOT NULL CHECK (balance_status IN ('available','insufficient_balance','unknown','invalid_api_key','provider_error')),
              balance_source varchar(20) CHECK (balance_source IN ('credits','key')),
              balance_amount numeric(12,4),
              balance_currency varchar(10) NOT NULL DEFAULT 'USD',
              total_credits numeric(12,4),
              total_usage numeric(12,4),
              key_limit numeric(12,4),
              key_limit_remaining numeric(12,4),
              balance_checked_at timestamptz,
              last_error_code varchar(100),
              last_error_message text,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              UNIQUE (tenant_id, provider)
            );
            CREATE INDEX IF NOT EXISTS idx_tenant_ai_provider_configs_tenant ON tenant_ai_provider_configs(tenant_id);
            CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_ai_provider_configs FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
            ALTER TABLE tenant_ai_provider_configs ENABLE ROW LEVEL SECURITY;
            CREATE POLICY tenant_ai_provider_configs_all ON tenant_ai_provider_configs
              FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
            """
        )

    ai_usage_log_columns = {
        column["name"] for column in inspector.get_columns("ai_usage_logs")
    }
    if "status" not in ai_usage_log_columns:
        op.execute(
            """
            ALTER TABLE ai_usage_logs ADD COLUMN status varchar(20);
            UPDATE ai_usage_logs
            SET status = CASE
              WHEN settlement_status = 'settlement_failed' THEN 'failed'
              WHEN settlement_status IN ('authorized', 'provider_called') THEN 'pending'
              ELSE 'completed'
            END;
            ALTER TABLE ai_usage_logs ALTER COLUMN status SET NOT NULL;
            """
        )

    op.execute(
        """
        ALTER TABLE ai_usage_logs DROP CONSTRAINT IF EXISTS ai_usage_logs_settlement_status_check;
        ALTER TABLE ai_usage_logs DROP CONSTRAINT IF EXISTS ai_usage_logs_status_check;
        ALTER TABLE ai_usage_logs ADD CONSTRAINT ai_usage_logs_status_check CHECK (status IN ('pending','completed','failed'));
        ALTER TABLE ai_usage_logs DROP COLUMN IF EXISTS authorization_transaction_id;
        ALTER TABLE ai_usage_logs DROP COLUMN IF EXISTS settlement_transaction_id;
        ALTER TABLE ai_usage_logs DROP COLUMN IF EXISTS settlement_status;
        ALTER TABLE ai_usage_logs DROP COLUMN IF EXISTS settled_at;

        DROP TABLE IF EXISTS balance_transactions CASCADE;
        ALTER TABLE tenants DROP COLUMN IF EXISTS balance;

        UPDATE scoring_jobs SET status = 'pending' WHERE status = 'waiting_balance';
        DROP INDEX IF EXISTS idx_scoring_jobs_unique_active;
        ALTER TABLE scoring_jobs DROP CONSTRAINT IF EXISTS scoring_jobs_status_check;
        ALTER TABLE scoring_jobs ADD CONSTRAINT scoring_jobs_status_check CHECK (status IN ('pending','leased','completed','failed'));
        CREATE UNIQUE INDEX idx_scoring_jobs_unique_active
        ON scoring_jobs(tenant_company_id)
        WHERE completed_at IS NULL AND status IN ('pending','leased');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP POLICY IF EXISTS tenant_ai_provider_configs_all ON tenant_ai_provider_configs;
        DROP TABLE IF EXISTS tenant_ai_provider_configs CASCADE;

        ALTER TABLE tenants ADD COLUMN IF NOT EXISTS balance numeric(12,4) NOT NULL DEFAULT 0;
        ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_balance_check;
        ALTER TABLE tenants ADD CONSTRAINT tenants_balance_check CHECK (balance >= 0);

        CREATE TABLE IF NOT EXISTS balance_transactions (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES tenants(id),
          type varchar(30) NOT NULL CHECK (type IN ('recharge','consumption','refund','adjustment','hold','release')),
          amount numeric(12,4) NOT NULL,
          balance_before numeric(12,4) NOT NULL,
          balance_after numeric(12,4) NOT NULL,
          reference_type varchar(60),
          reference_id uuid,
          idempotency_key varchar(200),
          description text,
          operated_by_user_id uuid REFERENCES users(id),
          operated_by_platform_user_id uuid REFERENCES platform_users(id),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS idx_balance_transactions_tenant ON balance_transactions(tenant_id, created_at DESC);
        ALTER TABLE balance_transactions ENABLE ROW LEVEL SECURITY;

        ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS authorization_transaction_id uuid REFERENCES balance_transactions(id);
        ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS settlement_transaction_id uuid REFERENCES balance_transactions(id);
        ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS settlement_status varchar(30);
        ALTER TABLE ai_usage_logs ADD COLUMN IF NOT EXISTS settled_at timestamptz;
        UPDATE ai_usage_logs
        SET settlement_status = CASE
          WHEN status = 'failed' THEN 'settlement_failed'
          WHEN status = 'pending' THEN 'authorized'
          ELSE 'settled_exact'
        END;
        ALTER TABLE ai_usage_logs DROP CONSTRAINT IF EXISTS ai_usage_logs_status_check;
        ALTER TABLE ai_usage_logs DROP COLUMN IF EXISTS status;
        ALTER TABLE ai_usage_logs ADD CONSTRAINT ai_usage_logs_settlement_status_check
          CHECK (settlement_status IN ('authorized','provider_called','settled_exact','settled_charge','settled_release','released_full','settlement_failed'));

        DROP INDEX IF EXISTS idx_scoring_jobs_unique_active;
        ALTER TABLE scoring_jobs DROP CONSTRAINT IF EXISTS scoring_jobs_status_check;
        ALTER TABLE scoring_jobs ADD CONSTRAINT scoring_jobs_status_check CHECK (status IN ('pending','leased','waiting_balance','completed','failed'));
        CREATE UNIQUE INDEX idx_scoring_jobs_unique_active
        ON scoring_jobs(tenant_company_id)
        WHERE completed_at IS NULL AND status IN ('pending','leased','waiting_balance');
        """
    )
