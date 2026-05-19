from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.ids import new_uuid
from app.services.tenant_ops_service import TenantOpsService
from tests.helpers import make_engine


async def _tenant(conn) -> str:
    tenant_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"tenant_id": tenant_id, "slug": f"create-co-{uuid4().hex[:8]}"},
    )
    return tenant_id


async def _user(conn, tenant_id: str) -> str:
    user_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
            VALUES (:user_id, :tenant_id, :email, 'hash', '测试用户', 'active', false)
            """
        ),
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": f"create-co-{uuid4().hex[:8]}@example.com",
        },
    )
    return user_id


@pytest.mark.asyncio
async def test_create_company_with_all_new_fields():
    engine = make_engine()
    svc = TenantOpsService()
    async with engine.begin() as conn:
        tenant_id = await _tenant(conn)
        user_id = await _user(conn, tenant_id)

        payload = {
            "name": f"全字段公司-{uuid4().hex[:6]}",
            "english_name": "Full Fields Co",
            "country": "CHN",
            "domain": f"full-{uuid4().hex[:6]}.com",
            "website": "https://example.com",
            "industry": "电子制造",
            "product_tags": ["PCB", "FPC"],
            "phone": "+86-21-12345678",
            "employee_size": "51-200",
            "founded_year": 2010,
            "full_address": "上海市浦东新区张江路100号",
            "description": "一家电子制造企业",
        }

        result = await svc.create_company(
            conn, tenant_id=tenant_id, user_id=user_id, payload=payload
        )
        clean_id = result["id"]

        row = await conn.execute(
            text(
                "SELECT phone, employee_size, founded_year, full_address, description "
                "FROM waimaotong_clean_companies WHERE id = :id"
            ),
            {"id": clean_id},
        )
        r = row.mappings().one()
        assert r["phone"] == "+86-21-12345678"
        assert r["employee_size"] == "51-200"
        assert r["founded_year"] == 2010
        assert r["full_address"] == "上海市浦东新区张江路100号"
        assert r["description"] == "一家电子制造企业"

        await conn.rollback()


@pytest.mark.asyncio
async def test_create_company_minimal_payload():
    engine = make_engine()
    svc = TenantOpsService()
    async with engine.begin() as conn:
        tenant_id = await _tenant(conn)
        user_id = await _user(conn, tenant_id)

        payload = {"name": f"最小公司-{uuid4().hex[:6]}"}

        result = await svc.create_company(
            conn, tenant_id=tenant_id, user_id=user_id, payload=payload
        )
        clean_id = result["id"]

        row = await conn.execute(
            text(
                "SELECT phone, employee_size, founded_year, full_address, description "
                "FROM waimaotong_clean_companies WHERE id = :id"
            ),
            {"id": clean_id},
        )
        r = row.mappings().one()
        assert r["phone"] is None
        assert r["employee_size"] is None
        assert r["founded_year"] is None
        assert r["full_address"] is None
        assert r["description"] is None

        await conn.rollback()


@pytest.mark.asyncio
async def test_founded_year_string_conversion():
    engine = make_engine()
    svc = TenantOpsService()
    async with engine.begin() as conn:
        tenant_id = await _tenant(conn)
        user_id = await _user(conn, tenant_id)

        payload = {
            "name": f"字符串年份-{uuid4().hex[:6]}",
            "founded_year": "2015",
        }

        result = await svc.create_company(
            conn, tenant_id=tenant_id, user_id=user_id, payload=payload
        )
        clean_id = result["id"]

        row = await conn.execute(
            text("SELECT founded_year FROM waimaotong_clean_companies WHERE id = :id"),
            {"id": clean_id},
        )
        assert row.scalar_one() == 2015

        await conn.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_value", [None, "", "abc", "二零一零"])
async def test_founded_year_invalid_values(bad_value):
    engine = make_engine()
    svc = TenantOpsService()
    async with engine.begin() as conn:
        tenant_id = await _tenant(conn)
        user_id = await _user(conn, tenant_id)

        payload = {
            "name": f"无效年份-{uuid4().hex[:6]}",
            "founded_year": bad_value,
        }

        result = await svc.create_company(
            conn, tenant_id=tenant_id, user_id=user_id, payload=payload
        )
        clean_id = result["id"]

        row = await conn.execute(
            text("SELECT founded_year FROM waimaotong_clean_companies WHERE id = :id"),
            {"id": clean_id},
        )
        assert row.scalar_one() is None

        await conn.rollback()
