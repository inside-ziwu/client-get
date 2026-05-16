from datetime import date

from alembic import op

from app.core.config import get_settings
from app.core.ids import new_uuid
from app.security.passwords import hash_password

# revision identifiers, used by Alembic.
revision = "20260421_0002"
down_revision = "20260421_0001"
branch_labels = None
depends_on = None


def create_partition(prefix: str, table_name: str, partition_date: date) -> None:
    start = partition_date.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    partition_name = f"{prefix}_{start.strftime('%Y_%m')}"
    op.get_bind().exec_driver_sql(
        f"""
        CREATE TABLE IF NOT EXISTS {partition_name}
        PARTITION OF {table_name}
        FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}');
        """
    )


def upgrade() -> None:
    settings = get_settings()
    today = date.today().replace(day=1)
    create_partition("emails_p", "emails", today)
    create_partition("articles_p", "intelligence_articles", today)
    create_partition("audit_logs_p", "audit_logs", today)

    warmup_rule_id = str(new_uuid())
    scoring_template_id = str(new_uuid())
    email_template_id = str(new_uuid())
    ai_model_id = str(new_uuid())
    scoring_scene_default_id = str(new_uuid())
    op.get_bind().exec_driver_sql(
        """
        INSERT INTO data_sources (id, source_type, name, alias_code, purpose, config, landing_rules)
        VALUES
          (gen_random_uuid(), 'waimao_tong', '外贸通', 'A01', '关键词直接搜索海外公司', '{}'::jsonb, '{}'::jsonb),
          (gen_random_uuid(), 'tengdao', '腾道', 'B01', '海关采购商数据搜索', '{}'::jsonb, '{}'::jsonb),
          (gen_random_uuid(), 'lixiaoyun', '励销云', 'C01', '同行反查精准客户', '{}'::jsonb, '{}'::jsonb)
        ON CONFLICT (source_type) DO NOTHING;
        """
    )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO platform_users (id, email, password_hash, name, status)
        VALUES
          ('{new_uuid()}', '{settings.admin_email}', '{hash_password(settings.admin_password)}', 'Platform Admin', 'active')
        ON CONFLICT (email) DO NOTHING;
        """
    )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO warmup_rules (id, name, is_active, min_observation_emails, bounce_alert_rate, config)
        VALUES ('{warmup_rule_id}', '默认预热规则', true, 20, 0.05, '{{}}'::jsonb)
        ON CONFLICT DO NOTHING;
        """
    )
    for level, daily_limit in ((1, 50), (2, 100), (3, 200), (4, 500), (5, 1000), (6, 4000)):
        op.get_bind().exec_driver_sql(
            f"""
            INSERT INTO warmup_rule_levels
              (id, rule_id, level, daily_limit, min_stay_days, min_delivery_rate, max_bounce_rate, max_complaint_rate)
            VALUES
              (gen_random_uuid(), '{warmup_rule_id}', {level}, {daily_limit}, 1, 0.95, 0.02, 0.001)
            ON CONFLICT (rule_id, level) DO NOTHING;
            """
        )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO platform_scoring_templates
          (id, industry, name, description, is_active, dimensions, grade_thresholds, version)
        VALUES
          (
            '{scoring_template_id}',
            'PCB',
            'PCB 默认评分模板',
            '平台默认种子模板',
            true,
            '[{{"id":"company_type","name":"工厂性质","type":"rule","weight":20,"rules":[{{"condition":"manufacturer","score":100}},{{"condition":"default","score":40}}]}},
              {{"id":"company_size","name":"公司规模","type":"rule","weight":20,"rules":[{{"condition":"employee_count_gte","value":200,"score":100}},{{"condition":"default","score":30}}]}},
              {{"id":"product_match","name":"产品匹配度","type":"llm","weight":20,"prompt_template":"根据公司资料判断与 PCB 行业的匹配度，返回 score 和 reasoning。","expected_json_schema":{{"score":"number","reasoning":"string"}}}}]'::jsonb,
            '{{"S":90,"A":80,"B":60,"C":40,"D":0}}'::jsonb,
            1
          )
        ON CONFLICT DO NOTHING;
        """
    )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO platform_scoring_template_versions
          (id, template_id, version, dimensions, grade_thresholds, change_reason)
        VALUES
          (
            '{new_uuid()}',
            '{scoring_template_id}',
            1,
            '[{{"id":"company_type","name":"工厂性质","type":"rule","weight":20,"rules":[{{"condition":"manufacturer","score":100}},{{"condition":"default","score":40}}]}},
              {{"id":"company_size","name":"公司规模","type":"rule","weight":20,"rules":[{{"condition":"employee_count_gte","value":200,"score":100}},{{"condition":"default","score":30}}]}},
              {{"id":"product_match","name":"产品匹配度","type":"llm","weight":20,"prompt_template":"根据公司资料判断与 PCB 行业的匹配度，返回 score 和 reasoning。","expected_json_schema":{{"score":"number","reasoning":"string"}}}}]'::jsonb,
            '{{"S":90,"A":80,"B":60,"C":40,"D":0}}'::jsonb,
            'seed'
          )
        ON CONFLICT DO NOTHING;
        """
    )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO platform_email_templates
          (id, industry, name, description, category, subject, body_html, body_text, variables, is_active)
        VALUES
          (
            '{email_template_id}',
            'PCB',
            'PCB 首封开发信',
            '平台默认开发信模板',
            'cold_outreach',
            'Hello {{公司名称}}',
            '<p>Hello {{公司名称}},</p><p>We are interested in cooperation.</p>',
            'Hello {{公司名称}}, we are interested in cooperation.',
            '["company_name","contact_name","tenant_company_name"]'::jsonb,
            true
          )
        ON CONFLICT DO NOTHING;
        """
    )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO ai_models
          (id, provider, model_id, display_name, model_type, input_price, output_price, is_active, config)
        VALUES
          ('{ai_model_id}', 'openrouter', 'openai/gpt-4.1-mini', 'GPT-4.1 Mini', 'general', 0.0005, 0.0015, true, '{{}}'::jsonb)
        ON CONFLICT (provider, model_id) DO NOTHING;
        """
    )
    op.get_bind().exec_driver_sql(
        f"""
        INSERT INTO ai_scene_defaults (id, scene, model_id, fallback_model_ids, config)
        VALUES
          ('{scoring_scene_default_id}', 'scoring', '{ai_model_id}', '[]'::jsonb, '{{}}'::jsonb),
          ('{new_uuid()}', 'email_generation', '{ai_model_id}', '[]'::jsonb, '{{}}'::jsonb),
          ('{new_uuid()}', 'intelligence_summary', '{ai_model_id}', '[]'::jsonb, '{{}}'::jsonb),
          ('{new_uuid()}', 'data_analysis', '{ai_model_id}', '[]'::jsonb, '{{}}'::jsonb)
        ON CONFLICT (scene) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DELETE FROM ai_scene_defaults;")
    op.get_bind().exec_driver_sql("DELETE FROM ai_models;")
    op.get_bind().exec_driver_sql("DELETE FROM platform_email_templates;")
    op.get_bind().exec_driver_sql("DELETE FROM platform_scoring_template_versions;")
    op.get_bind().exec_driver_sql("DELETE FROM platform_scoring_templates;")
    op.get_bind().exec_driver_sql("DELETE FROM platform_users;")
    op.get_bind().exec_driver_sql("DELETE FROM warmup_rule_levels;")
    op.get_bind().exec_driver_sql("DELETE FROM warmup_rules;")
    op.get_bind().exec_driver_sql("DELETE FROM data_sources;")
