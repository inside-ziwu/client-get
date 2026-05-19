"""修复迁移 0045 因 name+country 精确匹配不足导致的 tenant_companies 数据丢失。

策略：
1. 从 clean_companies 出发，逐级匹配 waimaotong_clean_companies：
   a. domain 匹配（最可靠）
   b. company_name + country_iso3 精确匹配
   c. company_name 单独匹配（country 缺失时）
2. 未匹配的 clean_companies → 新建 waimaotong_clean_companies 条目（source_id='recovered'）
3. 为所有匹配/新建的 wmt 公司创建 tenant_companies 条目
4. ON CONFLICT DO NOTHING 避免与现有数据冲突

revision: 20260519_0046
down_revision: 20260519_0045
"""

from alembic import op

revision = "20260519_0046"
down_revision = "20260519_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.exec_driver_sql("""
        CREATE TEMP TABLE _cc_wmt_map (
            cc_id bigint PRIMARY KEY,
            wmt_id bigint NOT NULL
        );
    """)

    # ── 第 1 轮：domain 匹配 ──
    conn.exec_driver_sql("""
        INSERT INTO _cc_wmt_map (cc_id, wmt_id)
        SELECT DISTINCT ON (cc.id)
            cc.id,
            wc.id
        FROM clean_companies cc
        JOIN waimaotong_clean_companies wc
            ON wc.domain IS NOT NULL
            AND wc.domain != ''
            AND wc.domain = regexp_replace(cc.website, '^https?://(www\.)?', '')
        WHERE cc.website IS NOT NULL AND cc.website != ''
        ORDER BY cc.id, wc.id;
    """)

    r1 = conn.exec_driver_sql("SELECT count(*) FROM _cc_wmt_map;")
    print(f"[0046] 第 1 轮 domain 匹配: {r1.scalar()} 条")

    # ── 第 2 轮：company_name + country_iso3 精确匹配 ──
    conn.exec_driver_sql("""
        INSERT INTO _cc_wmt_map (cc_id, wmt_id)
        SELECT DISTINCT ON (cc.id)
            cc.id,
            wc.id
        FROM clean_companies cc
        JOIN waimaotong_clean_companies wc
            ON wc.company_name = cc.name
            AND wc.country_iso3 = cc.country_iso3
        WHERE NOT EXISTS (SELECT 1 FROM _cc_wmt_map m WHERE m.cc_id = cc.id)
            AND cc.name IS NOT NULL AND cc.name != ''
            AND cc.country_iso3 IS NOT NULL AND cc.country_iso3 != ''
        ORDER BY cc.id, wc.id;
    """)

    r2 = conn.exec_driver_sql("SELECT count(*) FROM _cc_wmt_map;")
    print(f"[0046] 第 2 轮 name+country 匹配后累计: {r2.scalar()} 条")

    # ── 第 3 轮：company_name 单独匹配 ──
    conn.exec_driver_sql("""
        INSERT INTO _cc_wmt_map (cc_id, wmt_id)
        SELECT DISTINCT ON (cc.id)
            cc.id,
            wc.id
        FROM clean_companies cc
        JOIN waimaotong_clean_companies wc
            ON wc.company_name = cc.name
        WHERE NOT EXISTS (SELECT 1 FROM _cc_wmt_map m WHERE m.cc_id = cc.id)
            AND cc.name IS NOT NULL AND cc.name != ''
        ORDER BY cc.id, wc.id;
    """)

    r3 = conn.exec_driver_sql("SELECT count(*) FROM _cc_wmt_map;")
    print(f"[0046] 第 3 轮 name-only 匹配后累计: {r3.scalar()} 条")

    # ── 第 4 轮：未匹配的 → 逐条新建 wmt 条目 ──
    conn.exec_driver_sql("""
        DO $$
        DECLARE
            r RECORD;
            new_wmt_id bigint;
        BEGIN
            FOR r IN
                SELECT cc.id AS cc_id,
                       cc.name,
                       cc.country_iso3,
                       cc.website,
                       cc.industry_desc,
                       cc.employee_num,
                       cc.product_tags
                FROM clean_companies cc
                WHERE NOT EXISTS (SELECT 1 FROM _cc_wmt_map m WHERE m.cc_id = cc.id)
            LOOP
                INSERT INTO waimaotong_clean_companies
                    (company_name, country_iso3, website, industry, employee_size,
                     product_tags, source_id)
                VALUES
                    (r.name, r.country_iso3, r.website, r.industry_desc, r.employee_num,
                     to_jsonb(COALESCE(r.product_tags, '{}'::text[])), 'recovered')
                RETURNING id INTO new_wmt_id;

                INSERT INTO _cc_wmt_map (cc_id, wmt_id) VALUES (r.cc_id, new_wmt_id);
            END LOOP;
        END $$;
    """)

    r4 = conn.exec_driver_sql("SELECT count(*) FROM _cc_wmt_map;")
    total_cc = conn.exec_driver_sql("SELECT count(*) FROM clean_companies;")
    print(f"[0046] 第 4 轮新建后累计: {r4.scalar()} 条 (clean_companies 总数: {total_cc.scalar()})")

    # ── 第 5 步：为所有映射创建 tenant_companies 条目 ──
    conn.exec_driver_sql("""
        INSERT INTO tenant_companies
            (tenant_id, clean_company_id, business_status, data_status, visibility_status)
        SELECT
            t.id,
            m.wmt_id,
            'new',
            'ready',
            'visible'
        FROM _cc_wmt_map m
        CROSS JOIN tenants t
        ON CONFLICT (tenant_id, clean_company_id) DO NOTHING;
    """)

    result = conn.exec_driver_sql("""
        SELECT count(*) FROM tenant_companies WHERE visibility_status = 'visible';
    """)
    print(f"[0046] 修复完成，tenant_companies 可见总数: {result.scalar()}")

    conn.exec_driver_sql("DROP TABLE IF EXISTS _cc_wmt_map;")


def downgrade() -> None:
    pass
