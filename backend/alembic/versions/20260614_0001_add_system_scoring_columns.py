"""新增系统评分列 + 完整索引 + 替换刘辉租户废弃模板。

1. waimaotong_clean_companies 新增 system_grade/system_score 列
2. company_scores 新增完整索引（解决 partial index 在 LEFT JOIN 中不被使用的问题）
3. 替换刘辉租户的「电路板 默认评分模板」为平台模板副本

revision: 20260614_0001
down_revision: 20260611_0001
"""

from alembic import op

revision = "20260614_0001"
down_revision = "20260611_0001"
branch_labels = None
depends_on = None

_LIUHUI_TENANT_ID = "019e631f-5c2b-7661-88de-c050193f68b2"
_LIUHUI_TEMPLATE_ID = "019e631f-5c2d-729f-a612-b88438a4d321"
_LIUHUI_VERSION_ID = "019e631f-5c2e-74d4-9af8-60c96d2ed33e"
_PLATFORM_TEMPLATE_ID = "019db5f2-66c6-7a94-a224-a85fad64132e"


def upgrade() -> None:
    conn = op.get_bind()

    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            ADD COLUMN IF NOT EXISTS system_grade char(1),
            ADD COLUMN IF NOT EXISTS system_score integer;
    """)

    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_company_scores_tc_id
            ON company_scores(tenant_company_id);
    """)

    # 替换刘辉租户的废弃模板：用平台模板的 dimensions 覆盖
    row = conn.exec_driver_sql(
        "SELECT dimensions, grade_thresholds, version FROM platform_scoring_templates WHERE id = %s",
        (_PLATFORM_TEMPLATE_ID,),
    ).fetchone()

    if row is not None:
        import json
        dims_json = json.dumps(row[0]) if not isinstance(row[0], str) else row[0]
        thresholds_json = json.dumps(row[1]) if not isinstance(row[1], str) else row[1]
        platform_version = row[2]

        conn.exec_driver_sql(
            """
            UPDATE scoring_templates
            SET source_platform_template_id = %s,
                name = 'PCB 默认评分模板',
                dimensions = CAST(%s AS jsonb),
                grade_thresholds = CAST(%s AS jsonb),
                version = version + 1,
                updated_at = now()
            WHERE id = %s AND tenant_id = %s
            """,
            (_PLATFORM_TEMPLATE_ID, dims_json, thresholds_json,
             _LIUHUI_TEMPLATE_ID, _LIUHUI_TENANT_ID),
        )

        conn.exec_driver_sql(
            """
            UPDATE scoring_template_versions
            SET dimensions = CAST(%s AS jsonb),
                grade_thresholds = CAST(%s AS jsonb),
                change_reason = 'replace deprecated template with platform copy'
            WHERE id = %s
            """,
            (dims_json, thresholds_json, _LIUHUI_VERSION_ID),
        )

        print(f"[0614_0001] 刘辉租户模板已替换为平台模板副本 (platform v{platform_version})")


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_company_scores_tc_id;")
    conn.exec_driver_sql("""
        ALTER TABLE waimaotong_clean_companies
            DROP COLUMN IF EXISTS system_grade,
            DROP COLUMN IF EXISTS system_score;
    """)
