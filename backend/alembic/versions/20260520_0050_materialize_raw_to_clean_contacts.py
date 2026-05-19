"""从 waimaotong_raw_contacts 物化到 waimaotong_clean_contacts。

根因：raw → clean contacts 的物化步骤从未执行，导致 v3_company_contacts
始终返回空（clean_contacts 表对 WMT 导入的公司无数据）。

策略：
1. raw_contacts JOIN raw_companies（取 sys_company_id）→ INSERT INTO clean_contacts
2. ON CONFLICT 跳过已存在的记录（手动创建的联系人不会被覆盖）
3. 从新物化的 clean_contacts 补建 tenant_contacts
4. 重算 contacts_count

revision: 20260520_0050
down_revision: 20260520_0049
"""

from alembic import op

revision = "20260520_0050"
down_revision = "20260520_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. raw_contacts → clean_contacts 物化
    r1 = conn.exec_driver_sql("""
        INSERT INTO waimaotong_clean_contacts
          (sys_company_id, name, position, department, email, email_status,
           phone, mobile, linkedin, whatsapp, source, confidence, created_at)
        SELECT
          wr.sys_company_id,
          rc.name,
          rc.position,
          rc.department,
          rc.email,
          rc.email_status,
          rc.phone,
          rc.mobile,
          rc.linkedin,
          rc.whatsapp,
          rc.source,
          rc.confidence,
          rc.created_at
        FROM waimaotong_raw_contacts rc
        JOIN waimaotong_raw_companies wr ON wr.id = rc.raw_company_id
        WHERE wr.sys_company_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)
    print(f"[0050] raw → clean contacts 物化: {r1.rowcount} 条")

    # 2. clean_contacts → tenant_contacts 补建
    r2 = conn.exec_driver_sql("""
        INSERT INTO tenant_contacts
          (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
        SELECT
          tc.tenant_id,
          wcc.id,
          tc.clean_company_id,
          'available',
          true
        FROM tenant_companies tc
        JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
        JOIN waimaotong_clean_contacts wcc ON wcc.sys_company_id = wc.sys_company_id
        WHERE tc.visibility_status = 'visible'
          AND wcc.email IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM tenant_contacts existing
            WHERE existing.tenant_id = tc.tenant_id
              AND existing.clean_contact_id = wcc.id
          )
        ON CONFLICT (tenant_id, clean_contact_id) DO NOTHING
    """)
    print(f"[0050] clean → tenant_contacts 补建: {r2.rowcount} 条")

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
    print(f"[0050] 重算 contacts_count: {r3.rowcount} 家公司")

    # 4. 有联系人的公司 data_status → ready
    r4 = conn.exec_driver_sql("""
        UPDATE tenant_companies tc
        SET data_status = 'ready', updated_at = now()
        WHERE tc.visibility_status = 'visible'
          AND tc.data_status != 'ready'
          AND EXISTS (
            SELECT 1 FROM tenant_contacts
            WHERE tenant_id = tc.tenant_id
              AND clean_company_id = tc.clean_company_id
          )
    """)
    print(f"[0050] data_status → ready: {r4.rowcount} 条")


def downgrade() -> None:
    pass
