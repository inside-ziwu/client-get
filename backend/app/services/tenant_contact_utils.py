from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def ensure_contacts_from_wmt(
    conn: AsyncConnection,
    tenant_id: str,
    tenant_company_id: int,
) -> int:
    """从 WMT 源表按需物化 tenant_contacts。已有记录时跳过。返回新增数量。"""

    company_result = await conn.execute(
        text(
            """
            SELECT tc.clean_company_id, wc.sys_company_id
            FROM tenant_companies tc
            JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
            WHERE tc.id = :tenant_company_id AND tc.tenant_id = :tenant_id
            """
        ),
        {"tenant_company_id": tenant_company_id, "tenant_id": tenant_id},
    )
    company_row = company_result.mappings().first()
    if not company_row:
        return 0

    existing = await conn.execute(
        text(
            """
            SELECT 1 FROM tenant_contacts
            WHERE tenant_id = :tenant_id AND clean_company_id = :clean_company_id
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "clean_company_id": company_row["clean_company_id"]},
    )
    if existing.first():
        return 0

    wmt_contacts = await conn.execute(
        text(
            """
            SELECT id, name, email, position
            FROM waimaotong_clean_contacts
            WHERE sys_company_id = :sys_company_id AND email IS NOT NULL
            ORDER BY (position IS NOT NULL)::int DESC, id ASC
            """
        ),
        {"sys_company_id": company_row["sys_company_id"]},
    )
    rows = wmt_contacts.mappings().all()
    if not rows:
        return 0

    created = 0
    for row in rows:
        result = await conn.execute(
            text(
                """
                INSERT INTO tenant_contacts
                  (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                VALUES
                  (:tenant_id, :clean_contact_id, :clean_company_id, 'available', true)
                ON CONFLICT (tenant_id, clean_contact_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_contact_id": row["id"],
                "clean_company_id": company_row["clean_company_id"],
            },
        )
        if result.first():
            created += 1

    await conn.execute(
        text(
            """
            UPDATE tenant_companies
            SET data_status = 'ready', updated_at = now()
            WHERE tenant_id = :tenant_id
              AND clean_company_id = :clean_company_id
              AND data_status = 'missing_contacts'
              AND EXISTS (
                SELECT 1 FROM tenant_contacts
                WHERE tenant_id = :tenant_id
                  AND clean_company_id = :clean_company_id
              )
            """
        ),
        {"tenant_id": tenant_id, "clean_company_id": company_row["clean_company_id"]},
    )

    return created
