from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.ids import new_uuid
from app.services.tenant_contact_utils import ensure_contacts_from_wmt
from tests.helpers import make_engine
from tests.wmt_helpers import (
    create_wmt_company_with_contacts,
    create_wmt_contact,
)


async def _tenant(conn) -> str:
    tenant_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"id": tenant_id, "slug": f"ensure-{uuid4().hex[:8]}"},
    )
    return tenant_id


async def _count_tenant_contacts(conn, tenant_id: str, tenant_company_id: int) -> int:
    r = await conn.execute(
        text(
            """
            SELECT count(*) FROM tenant_contacts tc
            JOIN tenant_companies tco ON tco.clean_company_id = tc.clean_company_id
              AND tco.tenant_id = tc.tenant_id
            WHERE tc.tenant_id = :tenant_id AND tco.id = :tenant_company_id
            """
        ),
        {"tenant_id": tenant_id, "tenant_company_id": tenant_company_id},
    )
    return r.scalar_one()


async def _get_data_status(conn, tenant_id: str, tenant_company_id: int) -> str:
    r = await conn.execute(
        text(
            "SELECT data_status FROM tenant_companies WHERE tenant_id = :tenant_id AND id = :id"
        ),
        {"tenant_id": tenant_id, "id": tenant_company_id},
    )
    return r.scalar_one()


async def test_materialize_updates_data_status_to_ready() -> None:
    """4.4: 物化后 data_status 从 missing_contacts → ready"""
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=2, data_status="missing_contacts"
            )

            assert await _get_data_status(conn, tenant_id, setup["tenant_company_id"]) == "missing_contacts"

            created = await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])
            assert created == 2

            assert await _get_data_status(conn, tenant_id, setup["tenant_company_id"]) == "ready"
    finally:
        await engine.dispose()


async def test_full_materialization_no_limit() -> None:
    """4.5: WMT 有 15 个有 email 的联系人时全部物化"""
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=15
            )

            created = await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            assert created == 15
            assert await _count_tenant_contacts(conn, tenant_id, setup["tenant_company_id"]) == 15
    finally:
        await engine.dispose()


async def test_idempotent_no_duplicates() -> None:
    """4.7: 重复调用不产生重复数据"""
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=3
            )

            first = await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])
            second = await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            assert first == 3
            assert second == 0
            assert await _count_tenant_contacts(conn, tenant_id, setup["tenant_company_id"]) == 3
    finally:
        await engine.dispose()


async def test_skip_when_contacts_exist() -> None:
    """4.8: 已有 tenant_contacts 时跳过"""
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id, contact_count=3
            )

            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])
            # 向 WMT 源表添加新联系人
            await create_wmt_contact(
                conn, setup["sys_company_id"],
                email="new-contact@example.com",
            )

            created = await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            assert created == 0
            # 仍然是 3 个，新联系人不会被追加
            assert await _count_tenant_contacts(conn, tenant_id, setup["tenant_company_id"]) == 3
    finally:
        await engine.dispose()


async def test_position_ordering() -> None:
    """4.10: 有 position 的联系人 created_at 早于无 position 的"""
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id,
                contact_count=4,
                positions=["CEO", None, "CTO", None],
            )

            await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            r = await conn.execute(
                text(
                    """
                    SELECT tc.id, shc.position, tc.created_at
                    FROM tenant_contacts tc
                    JOIN waimaotong_clean_contacts shc ON shc.id = tc.clean_contact_id
                    JOIN tenant_companies tco ON tco.clean_company_id = tc.clean_company_id
                      AND tco.tenant_id = tc.tenant_id
                    WHERE tc.tenant_id = :tenant_id AND tco.id = :tenant_company_id
                    ORDER BY tc.created_at ASC
                    """
                ),
                {"tenant_id": tenant_id, "tenant_company_id": setup["tenant_company_id"]},
            )
            rows = r.mappings().all()
            assert len(rows) == 4
            # 前两个应该有 position
            assert rows[0]["position"] is not None
            assert rows[1]["position"] is not None
            # 后两个无 position
            assert rows[2]["position"] is None
            assert rows[3]["position"] is None
    finally:
        await engine.dispose()


async def test_no_email_contacts_not_materialized() -> None:
    """补充: 无 email 的 WMT 联系人不被物化"""
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            setup = await create_wmt_company_with_contacts(
                conn, tenant_id,
                contact_count=3,
                emails=[None, "has-email@example.com", None],
            )

            created = await ensure_contacts_from_wmt(conn, tenant_id, setup["tenant_company_id"])

            assert created == 1
            assert await _count_tenant_contacts(conn, tenant_id, setup["tenant_company_id"]) == 1
    finally:
        await engine.dispose()
