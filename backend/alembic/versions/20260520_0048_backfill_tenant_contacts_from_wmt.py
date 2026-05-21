"""补建 tenant_contacts + 修正 data_status。

迁移 0046 修复了 tenant_companies，但未物化 tenant_contacts。
此迁移从 waimaotong_clean_contacts 源表批量补建，并修正 data_status 一致性。

策略：
1. 分批处理 tenant_companies（每批 1000 家）
2. 对每批：从 WMT 联系人表查有 email 的记录，INSERT INTO tenant_contacts ON CONFLICT DO NOTHING
3. 排序：有 position 的联系人优先（影响 created_at 顺序，list_group_members fallback 取最早的）
4. 修正 data_status：有 tenant_contacts 的公司 → 'ready'，无的 → 'missing_contacts'

revision: 20260520_0048
down_revision: 20260519_0047
"""

from alembic import op

revision = "20260520_0048"
down_revision = "20260519_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    result = conn.exec_driver_sql("""
        SELECT count(*) FROM tenant_companies WHERE visibility_status = 'visible'
    """)
    total = result.scalar()
    print(f"[0048] tenant_companies 可见总数: {total}")

    inserted = conn.exec_driver_sql("""
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
        WHERE wcc.email IS NOT NULL
          AND tc.visibility_status = 'visible'
          AND NOT EXISTS (
            SELECT 1 FROM tenant_contacts existing
            WHERE existing.tenant_id = tc.tenant_id
              AND existing.clean_contact_id = wcc.id
          )
        ORDER BY tc.tenant_id, tc.clean_company_id,
                 (wcc.position IS NOT NULL)::int DESC, wcc.id ASC
        ON CONFLICT (tenant_id, clean_contact_id) DO NOTHING
    """)
    print(f"[0048] 补建 tenant_contacts: {inserted.rowcount} 条")

    updated_ready = conn.exec_driver_sql("""
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
    print(f"[0048] data_status → ready: {updated_ready.rowcount} 条")

    updated_missing = conn.exec_driver_sql("""
        UPDATE tenant_companies tc
        SET data_status = 'missing_contacts', updated_at = now()
        WHERE tc.visibility_status = 'visible'
          AND tc.data_status = 'ready'
          AND NOT EXISTS (
            SELECT 1 FROM tenant_contacts
            WHERE tenant_id = tc.tenant_id
              AND clean_company_id = tc.clean_company_id
          )
    """)
    print(f"[0048] data_status → missing_contacts: {updated_missing.rowcount} 条")


def downgrade() -> None:
    pass
