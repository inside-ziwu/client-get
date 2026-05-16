"""评分维度新格式：7 维绝对分制（替换旧的权重制）。

迁移内容：
1. 在 platform_scoring_templates 中插入 PCB 行业默认模板（新格式）。
   若 slug='pcb_default' 已存在则跳过（幂等）。
2. 对所有现有 scoring_templates，若维度仍是旧格式（含 weight 字段）
   则将其替换为新格式的 PCB 7 维模板。
3. 同步更新对应的 scoring_template_versions 最新版本。

新格式数据结构:
  维度: {key, name, hint?, conditions: [{label, condition, value?, min?, max?, score}]}
  等级: {S: 90, A: 70, B: 50, C: 30, D: 0}

revision: 20260507_0030
down_revision: 20260507_0029
"""

import json
from alembic import op
from sqlalchemy import text

revision = "20260507_0030"
down_revision = "20260507_0021"
branch_labels = None
depends_on = None

# PCB 行业 7 维评分模板（新绝对分制）
PCB_DIMENSIONS = [
    {
        "key": "factory_type",
        "name": "工厂性质",
        "hint": "",
        "conditions": [
            {"label": "生产制造", "condition": "factory_type_in", "value": ["manufacturer"], "score": 10},
            {"label": "ODM",     "condition": "factory_type_in", "value": ["odm"],          "score": 8},
            {"label": "OEM",     "condition": "factory_type_in", "value": ["oem"],          "score": 6},
            {"label": "其他",    "condition": "default",                                     "score": 0},
        ],
    },
    {
        "key": "employee_scale",
        "name": "工厂规模",
        "hint": "",
        "conditions": [
            {"label": "中型（51–499 人）",    "condition": "employee_num_range", "min": 51,   "max": 499,  "score": 20},
            {"label": "大型（500–1999 人）",  "condition": "employee_num_range", "min": 500,  "max": 1999, "score": 16},
            {"label": "小型（10–49 人）",     "condition": "employee_num_range", "min": 10,   "max": 49,   "score": 16},
            {"label": "超大型（2000 人以上）","condition": "employee_num_range", "min": 2000,              "score": 0},
        ],
    },
    {
        "key": "trade_amount",
        "name": "进出口额",
        "hint": "近三年 · USD",
        "conditions": [
            {"label": "10–50 万",    "condition": "trade_amount_3y_usd_range", "min": 100000,   "max": 500000,   "score": 20},
            {"label": "50–3000 万",  "condition": "trade_amount_3y_usd_range", "min": 500000,   "max": 30000000, "score": 16},
            {"label": "10 万以下",   "condition": "trade_amount_3y_usd_range",                  "max": 100000,   "score": 12},
            {"label": "3000 万以上", "condition": "trade_amount_3y_usd_range", "min": 30000000,                  "score": 0},
        ],
    },
    {
        "key": "trade_count",
        "name": "进出口次数",
        "hint": "近三年",
        "conditions": [
            {"label": "36–360 次",  "condition": "trade_count_range", "min": 36,  "max": 360, "score": 10},
            {"label": "360 次以上", "condition": "trade_count_range", "min": 360,             "score": 8},
            {"label": "6–36 次",    "condition": "trade_count_range", "min": 6,   "max": 36,  "score": 6},
            {"label": "其他",       "condition": "default",                                    "score": 0},
        ],
    },
    {
        "key": "contact_quality",
        "name": "联系人",
        "hint": "",
        "conditions": [
            {"label": "有采购联系人", "condition": "has_contact", "score": 10},
            {"label": "无采购联系人", "condition": "default",     "score": 8},
        ],
    },
    {
        "key": "data_source",
        "name": "数据来源",
        "hint": "",
        "conditions": [
            {"label": "A — 返推买家（腾道）", "condition": "source_table_contains", "value": "tendata_raw_companies",    "score": 10},
            {"label": "B — 外贸通直采",       "condition": "source_table_contains", "value": "waimaotong_raw_companies", "score": 8},
            {"label": "C — 其它网上采集",     "condition": "default",                                                     "score": 6},
        ],
    },
    {
        "key": "pcb_supplier",
        "name": "PCB 供应商",
        "hint": "",
        "conditions": [
            {"label": "A — 有中国 PCB 供应商", "condition": "has_china_pcb_supplier", "score": 20},
            {"label": "B — 无中国 PCB 供应商", "condition": "default",                "score": 10},
        ],
    },
]

PCB_GRADE_THRESHOLDS = {"S": 90, "A": 70, "B": 50, "C": 30, "D": 0}


def upgrade() -> None:
    conn = op.get_bind()

    # 1. 插入/更新 platform_scoring_template（PCB 行业，按 industry='PCB' 查找）
    dims_json = json.dumps(PCB_DIMENSIONS, ensure_ascii=False)
    grade_json = json.dumps(PCB_GRADE_THRESHOLDS, ensure_ascii=False)

    # 检查是否已有 PCB 模板
    existing = conn.execute(
        text("SELECT id FROM platform_scoring_templates WHERE industry = 'PCB' LIMIT 1")
    ).mappings().first()

    if existing:
        platform_id = str(existing["id"])
        conn.execute(
            text(
                """
                UPDATE platform_scoring_templates
                SET name             = 'PCB 行业默认模板',
                    description      = '针对 PCB 制造商设计的 7 维评分规则，适用于外贸通 + 腾道数据。',
                    dimensions       = CAST(:dims AS jsonb),
                    grade_thresholds = CAST(:grade AS jsonb),
                    updated_at       = now()
                WHERE id = :id
                """
            ),
            {"dims": dims_json, "grade": grade_json, "id": platform_id},
        )
    else:
        platform_result = conn.execute(
            text(
                """
                INSERT INTO platform_scoring_templates
                  (id, name, industry, description, dimensions, grade_thresholds, is_active)
                VALUES
                  (gen_random_uuid(),
                   'PCB 行业默认模板',
                   'PCB',
                   '针对 PCB 制造商设计的 7 维评分规则，适用于外贸通 + 腾道数据。',
                   CAST(:dims AS jsonb),
                   CAST(:grade AS jsonb),
                   true)
                RETURNING id
                """
            ),
            {"dims": dims_json, "grade": grade_json},
        )
        platform_row = platform_result.mappings().first()
        platform_id = str(platform_row["id"]) if platform_row else None

    if platform_id:
        # 同步 platform_scoring_template_versions
        conn.execute(
            text(
                """
                INSERT INTO platform_scoring_template_versions
                  (id, template_id, version, dimensions, grade_thresholds, change_reason)
                SELECT gen_random_uuid(), :template_id, version + 1,
                       CAST(:dims AS jsonb), CAST(:grade AS jsonb), '0030: 7维绝对分制新格式'
                FROM platform_scoring_templates
                WHERE id = :template_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"template_id": platform_id, "dims": dims_json, "grade": grade_json},
        )
        conn.execute(
            text(
                """
                UPDATE platform_scoring_templates
                SET version = version + 1
                WHERE id = :template_id
                """
            ),
            {"template_id": platform_id},
        )

    # 2. 对所有仍使用旧格式（含 weight 字段）的 scoring_templates 做迁移
    # 旧格式特征：dimensions 非空且第一个元素含 "weight" 键
    old_templates = conn.execute(
        text(
            """
            SELECT id, tenant_id, version
            FROM scoring_templates
            WHERE jsonb_array_length(dimensions) > 0
              AND (dimensions -> 0) ? 'weight'
            """
        )
    ).mappings().all()

    for tmpl in old_templates:
        new_version = int(tmpl["version"]) + 1
        conn.execute(
            text(
                """
                UPDATE scoring_templates
                SET dimensions        = CAST(:dims AS jsonb),
                    grade_thresholds  = CAST(:grade AS jsonb),
                    version           = :version,
                    updated_at        = now()
                WHERE id = :id
                """
            ),
            {
                "id": str(tmpl["id"]),
                "dims": dims_json,
                "grade": grade_json,
                "version": new_version,
            },
        )
        # 同步 scoring_template_versions
        conn.execute(
            text(
                """
                INSERT INTO scoring_template_versions
                  (id, tenant_id, template_id, version, dimensions, grade_thresholds, change_reason)
                VALUES
                  (gen_random_uuid(), :tenant_id, :template_id, :version,
                   CAST(:dims AS jsonb), CAST(:grade AS jsonb), '0030: 7维绝对分制新格式')
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "tenant_id": str(tmpl["tenant_id"]),
                "template_id": str(tmpl["id"]),
                "version": new_version,
                "dims": dims_json,
                "grade": grade_json,
            },
        )


def downgrade() -> None:
    # 不可逆（旧格式数据已覆盖），仅删除 platform 模板
    op.get_bind().execute(
        text("DELETE FROM platform_scoring_templates WHERE name = 'PCB 行业默认模板'")
    )
