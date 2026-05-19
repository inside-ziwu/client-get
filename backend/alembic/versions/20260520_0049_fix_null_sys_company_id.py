"""修复手动创建的公司 sys_company_id 为 NULL 的问题。

根因：create_company INSERT 未设 sys_company_id，
导致 v3_company_contacts 查询 `wcc.sys_company_id = NULL` 永远返回空。

策略：
1. 为 sys_company_id IS NULL 的 waimaotong_clean_companies 补设 sys_company_id = source_id
2. 通过 tenant_contacts 关联，修正对应 waimaotong_clean_contacts 的 sys_company_id
3. 修正 contacts_count

revision: 20260520_0049
down_revision: 20260520_0048
"""

from alembic import op

revision = "20260520_0049"
down_revision = "20260520_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. 为 sys_company_id IS NULL 的公司补设值（用 source_id，保证唯一）
    r1 = conn.exec_driver_sql("""
        UPDATE waimaotong_clean_companies
        SET sys_company_id = COALESCE(source_id, 'gen-' || id::text)
        WHERE sys_company_id IS NULL
    """)
    print(f"[0049] 补设 sys_company_id: {r1.rowcount} 家公司")

    # 2. 修正 waimaotong_clean_contacts.sys_company_id
    #    通过 tenant_contacts → tenant_companies → waimaotong_clean_companies 关联
    r2 = conn.exec_driver_sql("""
        UPDATE waimaotong_clean_contacts wcc
        SET sys_company_id = wc.sys_company_id
        FROM tenant_contacts tc
        JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
        WHERE tc.clean_contact_id = wcc.id
          AND (wcc.sys_company_id IS NULL OR wcc.sys_company_id != wc.sys_company_id)
    """)
    print(f"[0049] 修正联系人 sys_company_id: {r2.rowcount} 条")

    # 3. 重算 contacts_count
    r3 = conn.exec_driver_sql("""
        UPDATE waimaotong_clean_companies wc
        SET contacts_count = sub.cnt
        FROM (
            SELECT wcc.sys_company_id, count(*) AS cnt
            FROM waimaotong_clean_contacts wcc
            WHERE wcc.email IS NOT NULL AND wcc.sys_company_id IS NOT NULL
            GROUP BY wcc.sys_company_id
        ) sub
        WHERE wc.sys_company_id = sub.sys_company_id
          AND COALESCE(wc.contacts_count, 0) != sub.cnt
    """)
    print(f"[0049] 修正 contacts_count: {r3.rowcount} 家公司")


def downgrade() -> None:
    pass
