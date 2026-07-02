#!/usr/bin/env python3
"""Instance B 初始化脚本

为新实例初始化平台管理员和基础配置数据。
所有 INSERT 使用 ON CONFLICT DO NOTHING 实现幂等。

必须环境变量：
  INIT_ADMIN_EMAIL       — 管理员邮箱
  INIT_ADMIN_PASSWORD    — 管理员密码（将被哈希存储）
  CLIENTGET_INSTANCE_ID  — 实例 ID（不允许为空或 'default'）
  CLIENTGET_DEV_DATABASE_URL 或 DATABASE_URL — 数据库连接
"""

import os
import sys

from sqlalchemy import create_engine, text

from app.core.ids import new_uuid
from app.security.passwords import hash_password


def _require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        print(f"错误：环境变量 {key} 未设置或为空", file=sys.stderr)
        sys.exit(1)
    return value


def _build_sync_database_url() -> str:
    """从环境变量构建同步数据库连接 URL"""
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raw = os.environ.get("CLIENTGET_DEV_DATABASE_URL", "").strip()
    if not raw:
        print("错误：DATABASE_URL 或 CLIENTGET_DEV_DATABASE_URL 未设置", file=sys.stderr)
        sys.exit(1)
    # 统一转换为 psycopg 同步驱动
    clean = raw.split("://", 1)[-1]
    return f"postgresql+psycopg://{clean}"


def main() -> None:
    admin_email = _require_env("INIT_ADMIN_EMAIL")
    admin_password = _require_env("INIT_ADMIN_PASSWORD")
    instance_id = _require_env("CLIENTGET_INSTANCE_ID")

    if instance_id == "default":
        print("错误：CLIENTGET_INSTANCE_ID 不能为 'default'，请使用有意义的实例标识", file=sys.stderr)
        sys.exit(1)

    db_url = _build_sync_database_url()
    engine = create_engine(db_url, future=True)

    password_hash = hash_password(admin_password)

    # ── 预生成 ID ──────────────────────────────────────────────────────────
    admin_id = str(new_uuid())
    warmup_rule_id = str(new_uuid())
    scoring_template_id = str(new_uuid())
    scoring_version_id = str(new_uuid())
    email_template_id = str(new_uuid())
    ai_model_id = str(new_uuid())

    with engine.begin() as conn:
        # ── 1. 平台管理员 ──────────────────────────────────────────────────
        existing = conn.execute(
            text("SELECT id, instance_id FROM platform_users WHERE email = :email"),
            {"email": admin_email},
        ).first()
        if existing is not None:
            print(
                f"错误：邮箱 {admin_email} 已被 instance_id={existing[1]} 的用户 {existing[0]} 使用，"
                f"无法为实例 {instance_id} 创建管理员",
                file=sys.stderr,
            )
            sys.exit(1)
        conn.execute(
            text(
                """
                INSERT INTO platform_users (id, email, password_hash, name, status, instance_id)
                VALUES (:id, :email, :password_hash, :name, 'active', :instance_id)
                """
            ),
            {
                "id": admin_id,
                "email": admin_email,
                "password_hash": password_hash,
                "name": "Platform Admin",
                "instance_id": instance_id,
            },
        )
        print(f"[1/7] platform_users: {admin_email} (instance_id={instance_id})")

        # ── 2. data_sources ────────────────────────────────────────────────
        conn.execute(
            text(
                """
                INSERT INTO data_sources (id, source_type, name, alias_code, purpose, config, landing_rules, instance_id)
                VALUES
                  (:id1, 'waimao_tong', '外贸通', 'A01', '关键词直接搜索海外公司', '{}'::jsonb, '{}'::jsonb, :instance_id),
                  (:id2, 'tengdao', '腾道', 'B01', '海关采购商数据搜索', '{}'::jsonb, '{}'::jsonb, :instance_id),
                  (:id3, 'lixiaoyun', '励销云', 'C01', '同行反查精准客户', '{}'::jsonb, '{}'::jsonb, :instance_id)
                ON CONFLICT (instance_id, source_type) DO NOTHING
                """
            ),
            {
                "id1": str(new_uuid()),
                "id2": str(new_uuid()),
                "id3": str(new_uuid()),
                "instance_id": instance_id,
            },
        )
        print("[2/7] data_sources: waimao_tong, tengdao, lixiaoyun")

        # ── 3. warmup_rules + warmup_rule_levels ───────────────────────────
        conn.execute(
            text(
                """
                INSERT INTO warmup_rules (id, name, is_active, min_observation_emails, bounce_alert_rate, config, instance_id)
                VALUES (:id, '默认预热规则', true, 20, 0.05, '{}'::jsonb, :instance_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"id": warmup_rule_id, "instance_id": instance_id},
        )
        for level, daily_limit in ((1, 50), (2, 100), (3, 200), (4, 500), (5, 1000), (6, 4000)):
            conn.execute(
                text(
                    """
                    INSERT INTO warmup_rule_levels
                      (id, rule_id, level, daily_limit, min_stay_days, min_delivery_rate, max_bounce_rate, max_complaint_rate)
                    VALUES
                      (:id, :rule_id, :level, :daily_limit, 1, 0.95, 0.02, 0.001)
                    ON CONFLICT (rule_id, level) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "rule_id": warmup_rule_id,
                    "level": level,
                    "daily_limit": daily_limit,
                },
            )
        print("[3/7] warmup_rules + warmup_rule_levels")

        # ── 4. platform_scoring_templates + versions ───────────────────────
        conn.execute(
            text(
                """
                INSERT INTO platform_scoring_templates
                  (id, industry, name, description, is_active, dimensions, grade_thresholds, version, instance_id)
                VALUES
                  (
                    :id, 'PCB', 'PCB 默认评分模板', '平台默认种子模板', true,
                    :dimensions,
                    :grade_thresholds,
                    1, :instance_id
                  )
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": scoring_template_id,
                "dimensions": '[{"id":"company_type","name":"工厂性质","type":"rule","weight":20,"rules":[{"condition":"manufacturer","score":100},{"condition":"default","score":40}]},{"id":"company_size","name":"公司规模","type":"rule","weight":20,"rules":[{"condition":"employee_count_gte","value":200,"score":100},{"condition":"default","score":30}]},{"id":"product_match","name":"产品匹配度","type":"llm","weight":20,"prompt_template":"根据公司资料判断与 PCB 行业的匹配度，返回 score 和 reasoning。","expected_json_schema":{"score":"number","reasoning":"string"}}]',
                "grade_thresholds": '{"S":90,"A":80,"B":60,"C":40,"D":0}',
                "instance_id": instance_id,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO platform_scoring_template_versions
                  (id, template_id, version, dimensions, grade_thresholds, change_reason)
                VALUES (:id, :template_id, 1, :dimensions, :grade_thresholds, 'seed')
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": scoring_version_id,
                "template_id": scoring_template_id,
                "dimensions": '[{"id":"company_type","name":"工厂性质","type":"rule","weight":20,"rules":[{"condition":"manufacturer","score":100},{"condition":"default","score":40}]},{"id":"company_size","name":"公司规模","type":"rule","weight":20,"rules":[{"condition":"employee_count_gte","value":200,"score":100},{"condition":"default","score":30}]},{"id":"product_match","name":"产品匹配度","type":"llm","weight":20,"prompt_template":"根据公司资料判断与 PCB 行业的匹配度，返回 score 和 reasoning。","expected_json_schema":{"score":"number","reasoning":"string"}}]',
                "grade_thresholds": '{"S":90,"A":80,"B":60,"C":40,"D":0}',
            },
        )
        print("[4/7] platform_scoring_templates + versions")

        # ── 5. platform_email_templates ────────────────────────────────────
        conn.execute(
            text(
                """
                INSERT INTO platform_email_templates
                  (id, industry, name, description, category, subject, body_html, body_text, variables, is_active, instance_id)
                VALUES
                  (
                    :id, 'PCB', 'PCB 首封开发信', '平台默认开发信模板',
                    'cold_outreach',
                    'Hello {{公司名称}}',
                    '<p>Hello {{公司名称}},</p><p>We are interested in cooperation.</p>',
                    'Hello {{公司名称}}, we are interested in cooperation.',
                    '["company_name","contact_name","tenant_company_name"]'::jsonb,
                    true, :instance_id
                  )
                ON CONFLICT DO NOTHING
                """
            ),
            {"id": email_template_id, "instance_id": instance_id},
        )
        print("[5/7] platform_email_templates")

        # ── 6. ai_models ──────────────────────────────────────────────────
        conn.execute(
            text(
                """
                INSERT INTO ai_models
                  (id, provider, model_id, display_name, model_type, input_price, output_price, is_active, config, instance_id)
                VALUES
                  (:id, 'openrouter', 'openai/gpt-4.1-mini', 'GPT-4.1 Mini', 'general', 0.0005, 0.0015, true, '{}'::jsonb, :instance_id)
                ON CONFLICT (instance_id, provider, model_id) DO NOTHING
                """
            ),
            {"id": ai_model_id, "instance_id": instance_id},
        )
        print("[6/7] ai_models")

        # ── 7. ai_scene_defaults ───────────────────────────────────────────
        scenes = ["scoring", "email_generation", "intelligence_summary", "data_analysis"]
        for scene in scenes:
            conn.execute(
                text(
                    """
                    INSERT INTO ai_scene_defaults (id, scene, model_id, fallback_model_ids, config, instance_id)
                    VALUES (:id, :scene, :model_id, '[]'::jsonb, '{}'::jsonb, :instance_id)
                    ON CONFLICT (instance_id, scene) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "scene": scene,
                    "model_id": ai_model_id,
                    "instance_id": instance_id,
                },
            )
        print("[7/7] ai_scene_defaults")

    engine.dispose()
    print(f"\n初始化完成：instance_id={instance_id}, admin_email={admin_email}")


if __name__ == "__main__":
    main()
