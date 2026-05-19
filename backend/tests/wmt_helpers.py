"""WMT 表测试 helper。

业务 SQL 查 waimaotong_clean_companies / waimaotong_clean_contacts，
旧测试 helper 写 clean_companies / clean_contacts（不同的表）。
本模块提供正确写入 waimaotong 表的工具函数。
"""

from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.ids import new_uuid


async def create_wmt_company(
    conn: AsyncConnection,
    *,
    company_name: str | None = None,
    country_iso3: str = "USA",
    domain: str | None = None,
    website: str | None = None,
) -> dict:
    """创建 waimaotong_clean_companies 记录，返回 {id, sys_company_id}。"""
    slug = uuid4().hex[:8]
    name = company_name or f"WMT Company {slug}"
    result = await conn.execute(
        text(
            """
            INSERT INTO waimaotong_clean_companies
              (company_name, country_iso3, domain, website)
            VALUES (:name, :country, :domain, :website)
            RETURNING id, sys_company_id
            """
        ),
        {
            "name": name,
            "country": country_iso3,
            "domain": domain or f"{slug}.example.com",
            "website": website or f"https://{slug}.example.com",
        },
    )
    row = result.mappings().one()
    return {"id": row["id"], "sys_company_id": row["sys_company_id"]}


async def create_wmt_contact(
    conn: AsyncConnection,
    sys_company_id: int,
    *,
    name: str | None = None,
    email: str | None = None,
    position: str | None = None,
) -> int:
    """创建 waimaotong_clean_contacts 记录，返回 contact id。"""
    slug = uuid4().hex[:8]
    result = await conn.execute(
        text(
            """
            INSERT INTO waimaotong_clean_contacts
              (sys_company_id, name, email, position)
            VALUES (:sys_company_id, :name, :email, :position)
            RETURNING id
            """
        ),
        {
            "sys_company_id": sys_company_id,
            "name": name or f"Contact {slug}",
            "email": email,
            "position": position,
        },
    )
    return result.scalar_one()


async def create_tenant_company(
    conn: AsyncConnection,
    tenant_id: str,
    wmt_company_id: int,
    *,
    data_status: str = "missing_contacts",
    business_status: str = "new",
) -> int:
    """创建 tenant_companies 记录（关联到 waimaotong_clean_companies），返回 tenant_company_id。"""
    result = await conn.execute(
        text(
            """
            INSERT INTO tenant_companies
              (tenant_id, clean_company_id, business_status, data_status, visibility_status)
            VALUES
              (:tenant_id, :clean_company_id, :business_status, :data_status, 'visible')
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "clean_company_id": wmt_company_id,
            "data_status": data_status,
            "business_status": business_status,
        },
    )
    return result.scalar_one()


async def create_wmt_company_with_contacts(
    conn: AsyncConnection,
    tenant_id: str,
    *,
    contact_count: int = 1,
    emails: list[str] | None = None,
    positions: list[str | None] | None = None,
    data_status: str = "missing_contacts",
) -> dict:
    """一站式创建: wmt_company + N 个 wmt_contacts + tenant_company（不创建 tenant_contacts）。

    返回 {wmt_company_id, sys_company_id, tenant_company_id, wmt_contact_ids}。
    """
    wmt = await create_wmt_company(conn)

    contact_ids = []
    for i in range(contact_count):
        email = emails[i] if emails and i < len(emails) else f"contact-{i}-{uuid4().hex[:6]}@example.com"
        position = positions[i] if positions and i < len(positions) else None
        cid = await create_wmt_contact(
            conn,
            wmt["sys_company_id"],
            email=email,
            position=position,
        )
        contact_ids.append(cid)

    tc_id = await create_tenant_company(conn, tenant_id, wmt["id"], data_status=data_status)

    return {
        "wmt_company_id": wmt["id"],
        "sys_company_id": wmt["sys_company_id"],
        "tenant_company_id": tc_id,
        "wmt_contact_ids": contact_ids,
    }
