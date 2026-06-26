"""多实例部署：添加 instance_id 列 + 约束变更。

10 张平台级表新增 instance_id VARCHAR NOT NULL DEFAULT 'default'，
并将原有唯一约束/索引改为含 instance_id 的复合约束。
data_source_credentials 的 FK 从引用 data_sources(source_type)
改为复合 FK (instance_id, source_type)。

revision: 20260625_0100
down_revision: 20260614_0002
"""

from alembic import op

revision = "20260625_0100"
down_revision = "20260614_0002"
branch_labels = None
depends_on = None

# ── 需要添加 instance_id 的表 ──────────────────────────────────────────────
TABLES_WITH_INSTANCE_ID = [
    "platform_users",
    "tenants",
    "warmup_rules",
    "platform_scoring_templates",
    "platform_email_templates",
    "ai_models",
    "ai_scene_defaults",
    "data_sources",
    "data_source_credentials",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. 所有表添加 instance_id 列 ──────────────────────────────────────
    for table in TABLES_WITH_INSTANCE_ID:
        conn.exec_driver_sql(f"""
            ALTER TABLE {table}
              ADD COLUMN IF NOT EXISTS instance_id VARCHAR NOT NULL DEFAULT 'default';
        """)

    # ── 2. 约束变更 ────────────────────────────────────────────────────────

    # tenants: UNIQUE(slug) → UNIQUE(instance_id, slug)
    conn.exec_driver_sql(
        "ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_slug_key;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE tenants
          ADD CONSTRAINT uq_tenants_instance_slug UNIQUE (instance_id, slug);
    """)

    # warmup_rules: partial unique index → UNIQUE(instance_id) WHERE is_active
    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_warmup_rules_active;"
    )
    conn.exec_driver_sql("""
        CREATE UNIQUE INDEX idx_warmup_rules_active
          ON warmup_rules(instance_id) WHERE is_active;
    """)

    # platform_scoring_templates: partial unique index → UNIQUE(instance_id, industry) WHERE is_active
    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_platform_scoring_templates_active;"
    )
    conn.exec_driver_sql("""
        CREATE UNIQUE INDEX idx_platform_scoring_templates_active
          ON platform_scoring_templates(instance_id, industry) WHERE is_active;
    """)

    # ai_scene_defaults: UNIQUE(scene) → UNIQUE(instance_id, scene)
    conn.exec_driver_sql(
        "ALTER TABLE ai_scene_defaults DROP CONSTRAINT IF EXISTS ai_scene_defaults_scene_key;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE ai_scene_defaults
          ADD CONSTRAINT uq_ai_scene_defaults_instance_scene UNIQUE (instance_id, scene);
    """)

    # data_sources: UNIQUE(source_type) → UNIQUE(instance_id, source_type)
    # 注意：data_source_credentials 有 FK 引用 data_sources(source_type)，
    #       必须先删除 FK，再改唯一约束，最后重建复合 FK。
    conn.exec_driver_sql(
        "ALTER TABLE data_source_credentials "
        "DROP CONSTRAINT IF EXISTS data_source_credentials_source_type_fkey;"
    )
    conn.exec_driver_sql(
        "ALTER TABLE data_sources DROP CONSTRAINT IF EXISTS data_sources_source_type_key;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE data_sources
          ADD CONSTRAINT uq_data_sources_instance_source_type UNIQUE (instance_id, source_type);
    """)

    # ai_models: UNIQUE(provider, model_id) → UNIQUE(instance_id, provider, model_id)
    conn.exec_driver_sql(
        "ALTER TABLE ai_models DROP CONSTRAINT IF EXISTS ai_models_provider_model_id_key;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE ai_models
          ADD CONSTRAINT uq_ai_models_instance_provider_model UNIQUE (instance_id, provider, model_id);
    """)

    # ── 3. data_source_credentials FK 重建为复合 FK ───────────────────────
    # data_source_credentials 已在步骤 1 添加了 instance_id，
    # 现在创建复合 FK (instance_id, source_type) → data_sources(instance_id, source_type)
    conn.exec_driver_sql("""
        ALTER TABLE data_source_credentials
          ADD CONSTRAINT data_source_credentials_instance_source_type_fkey
          FOREIGN KEY (instance_id, source_type)
          REFERENCES data_sources(instance_id, source_type);
    """)


def downgrade() -> None:
    conn = op.get_bind()

    # ── 3. 恢复 data_source_credentials FK ────────────────────────────────
    conn.exec_driver_sql(
        "ALTER TABLE data_source_credentials "
        "DROP CONSTRAINT IF EXISTS data_source_credentials_instance_source_type_fkey;"
    )

    # ── 2. 恢复约束（逆序）─────────────────────────────────────────────────

    # ai_models: 恢复 UNIQUE(provider, model_id)
    conn.exec_driver_sql(
        "ALTER TABLE ai_models DROP CONSTRAINT IF EXISTS uq_ai_models_instance_provider_model;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE ai_models
          ADD CONSTRAINT ai_models_provider_model_id_key UNIQUE (provider, model_id);
    """)

    # data_sources: 恢复 UNIQUE(source_type)
    conn.exec_driver_sql(
        "ALTER TABLE data_sources DROP CONSTRAINT IF EXISTS uq_data_sources_instance_source_type;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE data_sources
          ADD CONSTRAINT data_sources_source_type_key UNIQUE (source_type);
    """)

    # 恢复 data_source_credentials FK → data_sources(source_type)
    conn.exec_driver_sql("""
        ALTER TABLE data_source_credentials
          ADD CONSTRAINT data_source_credentials_source_type_fkey
          FOREIGN KEY (source_type) REFERENCES data_sources(source_type);
    """)

    # ai_scene_defaults: 恢复 UNIQUE(scene)
    conn.exec_driver_sql(
        "ALTER TABLE ai_scene_defaults DROP CONSTRAINT IF EXISTS uq_ai_scene_defaults_instance_scene;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE ai_scene_defaults
          ADD CONSTRAINT ai_scene_defaults_scene_key UNIQUE (scene);
    """)

    # platform_scoring_templates: 恢复 partial unique index
    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_platform_scoring_templates_active;"
    )
    conn.exec_driver_sql("""
        CREATE UNIQUE INDEX idx_platform_scoring_templates_active
          ON platform_scoring_templates(industry) WHERE is_active;
    """)

    # warmup_rules: 恢复 partial unique index
    conn.exec_driver_sql(
        "DROP INDEX IF EXISTS idx_warmup_rules_active;"
    )
    conn.exec_driver_sql("""
        CREATE UNIQUE INDEX idx_warmup_rules_active
          ON warmup_rules(is_active) WHERE is_active;
    """)

    # tenants: 恢复 UNIQUE(slug)
    conn.exec_driver_sql(
        "ALTER TABLE tenants DROP CONSTRAINT IF EXISTS uq_tenants_instance_slug;"
    )
    conn.exec_driver_sql("""
        ALTER TABLE tenants
          ADD CONSTRAINT tenants_slug_key UNIQUE (slug);
    """)

    # ── 1. 删除 instance_id 列 ────────────────────────────────────────────
    for table in TABLES_WITH_INSTANCE_ID:
        conn.exec_driver_sql(f"""
            ALTER TABLE {table} DROP COLUMN IF EXISTS instance_id;
        """)
