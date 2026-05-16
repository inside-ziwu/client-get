from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260421_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "03_database" / "schema.sql"
    op.get_bind().exec_driver_sql(schema_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS service_idempotency_keys CASCADE;
        DROP TABLE IF EXISTS audit_logs CASCADE;
        DROP TABLE IF EXISTS notifications CASCADE;
        DROP TABLE IF EXISTS intelligence_article_publications CASCADE;
        DROP TABLE IF EXISTS intelligence_subscriptions CASCADE;
        DROP TABLE IF EXISTS intelligence_articles CASCADE;
        DROP TABLE IF EXISTS intelligence_sources CASCADE;
        DROP TABLE IF EXISTS email_events CASCADE;
        DROP TABLE IF EXISTS emails CASCADE;
        DROP TABLE IF EXISTS email_send_locks CASCADE;
        DROP TABLE IF EXISTS sequence_enrollments CASCADE;
        DROP TABLE IF EXISTS sequence_steps CASCADE;
        DROP TABLE IF EXISTS sending_plan_recipients CASCADE;
        DROP TABLE IF EXISTS sending_plans CASCADE;
        DROP TABLE IF EXISTS email_templates CASCADE;
        DROP TABLE IF EXISTS domain_daily_usage CASCADE;
        DROP TABLE IF EXISTS domain_warmup_history CASCADE;
        DROP TABLE IF EXISTS domain_warmup_status CASCADE;
        DROP TABLE IF EXISTS group_members CASCADE;
        DROP TABLE IF EXISTS groups CASCADE;
        DROP TABLE IF EXISTS tenant_contacts CASCADE;
        DROP TABLE IF EXISTS competitor_companies CASCADE;
        DROP TABLE IF EXISTS company_blacklist CASCADE;
        DROP TABLE IF EXISTS contact_rules CASCADE;
        DROP TABLE IF EXISTS company_scores CASCADE;
        DROP TABLE IF EXISTS scoring_template_versions CASCADE;
        DROP TABLE IF EXISTS scoring_templates CASCADE;
        DROP TABLE IF EXISTS tenant_companies CASCADE;
        DROP TABLE IF EXISTS collection_task_keywords CASCADE;
        DROP TABLE IF EXISTS collection_tasks CASCADE;
        DROP TABLE IF EXISTS collection_keywords CASCADE;
        DROP TABLE IF EXISTS shared_contacts CASCADE;
        DROP TABLE IF EXISTS company_sources CASCADE;
        DROP TABLE IF EXISTS shared_companies CASCADE;
        DROP TABLE IF EXISTS ai_usage_logs CASCADE;
        DROP TABLE IF EXISTS balance_transactions CASCADE;
        DROP TABLE IF EXISTS ai_scene_defaults CASCADE;
        DROP TABLE IF EXISTS ai_models CASCADE;
        DROP TABLE IF EXISTS warmup_rule_levels CASCADE;
        DROP TABLE IF EXISTS warmup_rules CASCADE;
        DROP TABLE IF EXISTS platform_email_templates CASCADE;
        DROP TABLE IF EXISTS platform_scoring_template_versions CASCADE;
        DROP TABLE IF EXISTS platform_scoring_templates CASCADE;
        DROP TABLE IF EXISTS data_source_credentials CASCADE;
        DROP TABLE IF EXISTS data_sources CASCADE;
        DROP TABLE IF EXISTS user_roles CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS tenants CASCADE;
        DROP TABLE IF EXISTS platform_users CASCADE;
        DROP TYPE IF EXISTS user_role CASCADE;
        DROP FUNCTION IF EXISTS current_tenant_id();
        DROP FUNCTION IF EXISTS trigger_set_updated_at();
        """
    )
