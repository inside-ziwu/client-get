"""tenant 端数据源从 clean_companies/clean_contacts 切换到 waimaotong_clean_companies/waimaotong_clean_contacts。

1. wmt 表索引补建（sys_company_id、domain、company_name+country_iso3）
2. tenant_companies FK 删除 + 关联重建（name+country 匹配）+ 未匹配记录删除
3. tenant_contacts 全表清空 + FK 删除
4. tenant_companies 新索引（不加 FK，避免阻碍 wmt 导入流程）

revision: 20260519_0045
down_revision: 20260519_0044
"""

from alembic import op

revision = "20260519_0045"
down_revision = "20260519_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. wmt 表索引补建
    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_wmt_clean_contacts_sys_company_id
            ON waimaotong_clean_contacts (sys_company_id);

        CREATE INDEX IF NOT EXISTS idx_wmt_clean_companies_domain
            ON waimaotong_clean_companies (domain)
            WHERE domain IS NOT NULL AND domain != '';

        CREATE INDEX IF NOT EXISTS idx_wmt_clean_companies_name_country
            ON waimaotong_clean_companies (company_name, country_iso3);
    """)

    # 2. tenant_companies: 删除旧 FK
    conn.exec_driver_sql("""
        ALTER TABLE tenant_companies
            DROP CONSTRAINT IF EXISTS tenant_companies_clean_company_id_fkey;
    """)

    # 3. 先删除会产生 UNIQUE(tenant_id, clean_company_id) 冲突的重复行
    #    多个 clean_companies 可能映射到同一个 wmt 公司（name+country 相同），
    #    保留 score 最高的那条，其余级联删除。
    conn.exec_driver_sql("""
        WITH mapping AS (
            SELECT
                tc.id AS tc_id,
                tc.tenant_id,
                wc.id AS new_cid,
                ROW_NUMBER() OVER (
                    PARTITION BY tc.tenant_id, wc.id
                    ORDER BY tc.score DESC NULLS LAST, tc.id
                ) AS rn
            FROM tenant_companies tc
            JOIN clean_companies cc ON cc.id = tc.clean_company_id
            JOIN waimaotong_clean_companies wc
                ON wc.company_name = cc.name AND wc.country_iso3 = cc.country_iso3
        )
        DELETE FROM tenant_companies
        WHERE id IN (SELECT tc_id FROM mapping WHERE rn > 1);
    """)

    # 4. tenant_companies: 基于 name+country 匹配 wmt 表重建关联
    conn.exec_driver_sql("""
        UPDATE tenant_companies tc
        SET clean_company_id = wc.id
        FROM clean_companies cc
        JOIN waimaotong_clean_companies wc
            ON wc.company_name = cc.name AND wc.country_iso3 = cc.country_iso3
        WHERE tc.clean_company_id = cc.id;
    """)

    # 5. 删除未匹配的 tenant_companies 记录（D10：不做安全网）
    conn.exec_driver_sql("""
        DELETE FROM tenant_companies
        WHERE clean_company_id NOT IN (
            SELECT id FROM waimaotong_clean_companies
        );
    """)

    # 6. tenant_contacts: 全表清空（D11：不做逐条匹配）
    conn.exec_driver_sql("""
        DELETE FROM tenant_contacts;
    """)

    # 7. tenant_contacts: 删除旧 FK
    conn.exec_driver_sql("""
        ALTER TABLE tenant_contacts
            DROP CONSTRAINT IF EXISTS tenant_contacts_clean_contact_id_fkey,
            DROP CONSTRAINT IF EXISTS tenant_contacts_clean_company_id_fkey;
    """)

    # 8. tenant_companies 新索引（不加 FK 约束）
    conn.exec_driver_sql("""
        CREATE INDEX IF NOT EXISTS idx_tenant_companies_clean_company_id
            ON tenant_companies (clean_company_id);
    """)


def downgrade() -> None:
    conn = op.get_bind()

    # 7. 删除 tenant_companies 新索引
    conn.exec_driver_sql("""
        DROP INDEX IF EXISTS idx_tenant_companies_clean_company_id;
    """)

    # 6. tenant_contacts: 恢复旧 FK（指向 clean 表）
    conn.exec_driver_sql("""
        ALTER TABLE tenant_contacts
            ADD CONSTRAINT tenant_contacts_clean_contact_id_fkey
                FOREIGN KEY (clean_contact_id) REFERENCES clean_contacts(id) ON DELETE CASCADE,
            ADD CONSTRAINT tenant_contacts_clean_company_id_fkey
                FOREIGN KEY (clean_company_id) REFERENCES clean_companies(id) ON DELETE CASCADE;
    """)

    # 2. tenant_companies: 恢复旧 FK（指向 clean 表）
    conn.exec_driver_sql("""
        ALTER TABLE tenant_companies
            ADD CONSTRAINT tenant_companies_clean_company_id_fkey
                FOREIGN KEY (clean_company_id) REFERENCES clean_companies(id) ON DELETE CASCADE;
    """)

    # 1. 删除 wmt 索引
    conn.exec_driver_sql("""
        DROP INDEX IF EXISTS idx_wmt_clean_companies_name_country;
        DROP INDEX IF EXISTS idx_wmt_clean_companies_domain;
        DROP INDEX IF EXISTS idx_wmt_clean_contacts_sys_company_id;
    """)
