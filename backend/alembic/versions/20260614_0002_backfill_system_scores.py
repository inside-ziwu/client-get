"""存量数据回填系统评分。

用纯 SQL 批量操作（避免逐行 Python 循环导致公网延迟问题）。
在数据库端创建临时评分函数，批量 UPDATE/INSERT 后删除。

revision: 20260614_0002
down_revision: 20260614_0001
"""

from alembic import op
from sqlalchemy import text

revision = "20260614_0002"
down_revision = "20260614_0001"
branch_labels = None
depends_on = None

# 评分函数：接受 dimensions jsonb 和公司数据，返回 (total_score, grade)
_CREATE_SCORING_FN = """
CREATE OR REPLACE FUNCTION _tmp_score_company(
    p_dims jsonb,
    p_thresholds jsonb,
    p_employee_size text,
    p_trade_amount numeric,
    p_trade_count integer,
    p_contacts_count integer,
    p_data_source_tags jsonb,
    p_source_tags text[],
    p_company_type_analysis text
) RETURNS TABLE(total_score integer, grade char(1), dim_scores jsonb) AS $$
DECLARE
    dim jsonb;
    cond jsonb;
    ctype text;
    dim_score integer;
    running_total integer := 0;
    scores jsonb := '[]'::jsonb;
    emp_num integer;
    emp_raw text;
    matched boolean;
BEGIN
    FOR dim IN SELECT * FROM jsonb_array_elements(p_dims)
    LOOP
        -- 跳过 LLM 维度
        IF dim->>'type' = 'llm' THEN
            scores := scores || jsonb_build_object('key', COALESCE(dim->>'key', dim->>'id', ''), 'score', 0, 'skipped', 'llm');
            CONTINUE;
        END IF;

        dim_score := 0;
        matched := false;

        FOR cond IN SELECT * FROM jsonb_array_elements(COALESCE(dim->'conditions', dim->'rules', '[]'::jsonb))
        LOOP
            ctype := COALESCE(cond->>'condition', '');

            IF ctype = 'default' THEN
                dim_score := COALESCE((cond->>'score')::integer, 0);
                matched := true;
                EXIT;

            ELSIF ctype = 'factory_type_in' THEN
                IF p_company_type_analysis IS NOT NULL AND EXISTS (
                    SELECT 1 FROM jsonb_array_elements_text(COALESCE(cond->'value', '[]'::jsonb)) v
                    WHERE lower(p_company_type_analysis) LIKE '%%' || lower(v) || '%%'
                ) THEN
                    dim_score := COALESCE((cond->>'score')::integer, 0);
                    matched := true;
                    EXIT;
                END IF;

            ELSIF ctype = 'employee_num_range' THEN
                emp_raw := lower(replace(replace(replace(COALESCE(p_employee_size, ''), ',', ''), '+', ''), '~', ''));
                BEGIN
                    IF emp_raw LIKE '%%k%%' THEN
                        emp_num := (replace(emp_raw, 'k', '')::numeric * 1000)::integer;
                    ELSIF emp_raw LIKE '%% to %%' THEN
                        emp_num := ((split_part(emp_raw, ' to ', 1)::integer + split_part(emp_raw, ' to ', 2)::integer) / 2);
                    ELSE
                        emp_num := emp_raw::numeric::integer;
                    END IF;
                EXCEPTION WHEN OTHERS THEN
                    emp_num := NULL;
                END;
                IF emp_num IS NOT NULL
                   AND (cond->>'min' IS NULL OR emp_num >= (cond->>'min')::integer)
                   AND (cond->>'max' IS NULL OR emp_num <= (cond->>'max')::integer) THEN
                    dim_score := COALESCE((cond->>'score')::integer, 0);
                    matched := true;
                    EXIT;
                END IF;

            ELSIF ctype = 'trade_amount_3y_usd_range' THEN
                IF p_trade_amount IS NOT NULL
                   AND (cond->>'min' IS NULL OR p_trade_amount >= (cond->>'min')::numeric)
                   AND (cond->>'max' IS NULL OR p_trade_amount <= (cond->>'max')::numeric) THEN
                    dim_score := COALESCE((cond->>'score')::integer, 0);
                    matched := true;
                    EXIT;
                END IF;

            ELSIF ctype = 'trade_count_range' THEN
                IF p_trade_count IS NOT NULL
                   AND (cond->>'min' IS NULL OR p_trade_count >= (cond->>'min')::integer)
                   AND (cond->>'max' IS NULL OR p_trade_count <= (cond->>'max')::integer) THEN
                    dim_score := COALESCE((cond->>'score')::integer, 0);
                    matched := true;
                    EXIT;
                END IF;

            ELSIF ctype = 'has_contact' THEN
                IF COALESCE(p_contacts_count, 0) > 0 THEN
                    dim_score := COALESCE((cond->>'score')::integer, 0);
                    matched := true;
                    EXIT;
                END IF;

            ELSIF ctype = 'source_table_contains' THEN
                DECLARE
                    target text;
                    tag_val text;
                BEGIN
                    IF cond->>'value' = 'tendata_raw_companies' THEN target := '腾道';
                    ELSIF cond->>'value' = 'waimaotong_raw_companies' THEN target := '外贸通';
                    ELSE target := COALESCE(cond->>'value', '');
                    END IF;
                    -- 检查 data_source_tags (jsonb) 和 source_tags (text[])
                    IF p_data_source_tags IS NOT NULL AND EXISTS (
                        SELECT 1 FROM jsonb_array_elements_text(p_data_source_tags) t WHERE t LIKE '%%' || target || '%%'
                    ) THEN
                        dim_score := COALESCE((cond->>'score')::integer, 0);
                        matched := true;
                        EXIT;
                    END IF;
                    IF p_source_tags IS NOT NULL AND EXISTS (
                        SELECT 1 FROM unnest(p_source_tags) t WHERE t LIKE '%%' || target || '%%'
                    ) THEN
                        dim_score := COALESCE((cond->>'score')::integer, 0);
                        matched := true;
                        EXIT;
                    END IF;
                END;

            -- has_china_pcb_supplier 和未知类型：得分 0
            END IF;
        END LOOP;

        running_total := running_total + dim_score;
        scores := scores || jsonb_build_object('key', COALESCE(dim->>'key', dim->>'id', ''), 'score', dim_score);
    END LOOP;

    -- 按阈值映射等级
    total_score := running_total;
    IF running_total >= COALESCE((p_thresholds->>'S')::integer, 90) THEN grade := 'S';
    ELSIF running_total >= COALESCE((p_thresholds->>'A')::integer, 70) THEN grade := 'A';
    ELSIF running_total >= COALESCE((p_thresholds->>'B')::integer, 50) THEN grade := 'B';
    ELSIF running_total >= COALESCE((p_thresholds->>'C')::integer, 30) THEN grade := 'C';
    ELSE grade := 'D';
    END IF;
    dim_scores := scores;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    conn = op.get_bind()

    # 创建临时评分函数
    conn.exec_driver_sql(_CREATE_SCORING_FN)

    # ── 第 1 步：平台级回填 ──
    result = conn.exec_driver_sql("""
        UPDATE waimaotong_clean_companies wc
        SET system_grade = scored.grade,
            system_score = scored.total_score
        FROM (
            SELECT c.id, s.total_score, s.grade
            FROM waimaotong_clean_companies c,
                 (SELECT dimensions, grade_thresholds FROM platform_scoring_templates WHERE is_active = true ORDER BY updated_at DESC LIMIT 1) tmpl,
                 LATERAL _tmp_score_company(
                     tmpl.dimensions, tmpl.grade_thresholds,
                     c.employee_size, c.trade_amount_3y_usd, c.trade_count,
                     c.contacts_count, c.data_source_tags, c.source_tags,
                     c.company_type_analysis
                 ) s
            WHERE c.system_grade IS NULL
        ) scored
        WHERE wc.id = scored.id
    """)
    print(f"[0614_0002] 平台级回填完成: {result.rowcount} 条")

    # ── 第 2 步：租户级回填 ──
    tenants = conn.exec_driver_sql("""
        SELECT st.id, st.tenant_id, st.dimensions, st.grade_thresholds
        FROM scoring_templates st
        WHERE st.is_active = true
    """).fetchall()

    for t in tenants:
        template_id = str(t[0])
        tenant_id = str(t[1])
        dims = t[2] if isinstance(t[2], str) else __import__('json').dumps(t[2])
        thresholds = t[3] if isinstance(t[3], str) else __import__('json').dumps(t[3])

        ver = conn.execute(text(
            "SELECT id FROM scoring_template_versions WHERE template_id = CAST(:tmpl AS uuid) AND tenant_id = CAST(:tid AS uuid) ORDER BY version DESC LIMIT 1"
        ), {"tmpl": template_id, "tid": tenant_id}).fetchone()
        version_id = str(ver[0]) if ver else template_id

        result = conn.execute(text("""
            INSERT INTO company_scores
                (id, tenant_id, tenant_company_id, template_id, template_version_id,
                 total_score, grade, dimension_scores, scored_at, created_at)
            SELECT
                gen_random_uuid(),
                CAST(:tenant_id AS uuid),
                tc.id,
                CAST(:template_id AS uuid),
                CAST(:version_id AS uuid),
                s.total_score,
                s.grade,
                s.dim_scores,
                now(),
                now()
            FROM tenant_companies tc
            JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
            CROSS JOIN LATERAL _tmp_score_company(
                CAST(:dims AS jsonb), CAST(:thresholds AS jsonb),
                wc.employee_size, wc.trade_amount_3y_usd, wc.trade_count,
                wc.contacts_count, wc.data_source_tags, wc.source_tags,
                wc.company_type_analysis
            ) s
            WHERE tc.tenant_id = CAST(:tenant_id AS uuid)
            ON CONFLICT (tenant_company_id, template_version_id) WHERE is_retry = false
            DO UPDATE SET total_score = EXCLUDED.total_score, grade = EXCLUDED.grade,
                dimension_scores = EXCLUDED.dimension_scores, scored_at = now()
        """), {"tenant_id": tenant_id, "template_id": template_id, "version_id": version_id,
               "dims": dims, "thresholds": thresholds})

        print(f"[0614_0002] 租户 {tenant_id} 回填完成: {result.rowcount} 条")

    # 清理临时函数
    conn.exec_driver_sql("DROP FUNCTION IF EXISTS _tmp_score_company;")


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DELETE FROM company_scores;")
    conn.exec_driver_sql("UPDATE waimaotong_clean_companies SET system_grade = NULL, system_score = NULL;")
    conn.exec_driver_sql("DROP FUNCTION IF EXISTS _tmp_score_company;")
