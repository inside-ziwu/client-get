"""source_competitor 字段透传测试 — 列表 + 详情"""

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

import pytest

from app.services.tenant_query_service import TenantQueryService

TENANT_ID = "t-001"


def _make_mapping(row_dict):
    """构造支持 [] 取值的 mapping 对象"""
    m = MagicMock()
    m.__getitem__ = lambda self, key: row_dict[key]
    m.__contains__ = lambda self, key: key in row_dict
    return m


def _list_row(**overrides):
    """companies_page 查询返回的单行数据"""
    base = {
        "id": 1,
        "tc_id": 10,
        "company_name": "Test Co",
        "english_name": "Test Co EN",
        "country_iso3": "USA",
        "website": "https://test.com",
        "domain": "test.com",
        "industry": "Electronics",
        "sub_industry": "PCB",
        "employee_size": "50-100",
        "contacts_count": 5,
        "product_tags": ["tag1"],
        "grade": "A",
        "wmt_score": 85.0,
        "founded_year": 2010,
        "phone": "+1234",
        "trade_amount_3y_usd": 100000.0,
        "trade_count": 10,
        "description": "A test company",
        "data_source_tags": ["wmt"],
        "company_size": "medium",
        "business_status": "active",
        "data_status": "complete",
        "model_score": 90.0,
        "score": 88.0,
        "note": None,
        "tags": [],
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 2),
        "source_competitor": None,
    }
    base.update(overrides)
    return base


def _detail_row(**overrides):
    """v3_company_detail 查询返回的单行数据"""
    base = _list_row()
    base.update({
        "full_address": "123 Test St",
        "score_details": {"quality": 9},
        "company_type_analysis": "manufacturer",
        "email_priority": "high",
        "sales_approach": "direct",
        "match_reasons": "keyword match",
        "potential_needs": "PCB boards",
        "recommended_products": "FR-4",
        "risk_factors": None,
        "main_business": "PCB manufacturing",
        "trade_summary": "Active trader",
        "score_adjustment": None,
        "tenant_created_at": datetime(2026, 1, 1),
        "tenant_updated_at": datetime(2026, 1, 2),
    })
    base.update(overrides)
    return base


class TestCompaniesPageSourceCompetitor:
    """U1: companies_page 的 source_competitor 字段透传"""

    @pytest.mark.asyncio
    async def test_normal_value(self):
        """raw 有 source_competitor 值时，响应中返回对应字符串"""
        svc = TenantQueryService()
        conn = AsyncMock()

        row = _list_row(source_competitor="深圳市信安电路有限公司")
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        data_result.mappings.return_value.all.return_value = [_make_mapping(row)]

        conn.execute = AsyncMock(side_effect=[count_result, data_result])

        rows, total = await svc.companies_page(
            conn, tenant_id=TENANT_ID, limit=10
        )

        assert total == 1
        assert len(rows) == 1
        assert rows[0]["source_competitor"] == "深圳市信安电路有限公司"

    @pytest.mark.asyncio
    async def test_null_value(self):
        """raw 匹配但 source_competitor 为 null 时，返回 null"""
        svc = TenantQueryService()
        conn = AsyncMock()

        row = _list_row(source_competitor=None)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        data_result.mappings.return_value.all.return_value = [_make_mapping(row)]

        conn.execute = AsyncMock(side_effect=[count_result, data_result])

        rows, total = await svc.companies_page(
            conn, tenant_id=TENANT_ID, limit=10
        )

        assert rows[0]["source_competitor"] is None

    @pytest.mark.asyncio
    async def test_no_match(self):
        """clean 无对应 raw（LEFT JOIN）时，source_competitor 返回 null"""
        svc = TenantQueryService()
        conn = AsyncMock()

        row = _list_row(source_competitor=None)
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        data_result = MagicMock()
        data_result.mappings.return_value.all.return_value = [_make_mapping(row)]

        conn.execute = AsyncMock(side_effect=[count_result, data_result])

        rows, total = await svc.companies_page(
            conn, tenant_id=TENANT_ID, limit=10
        )

        assert rows[0]["source_competitor"] is None


class TestCompanyDetailSourceCompetitor:
    """U2: v3_company_detail 的 source_competitor 字段透传"""

    @pytest.mark.asyncio
    async def test_normal_value(self):
        """详情响应包含 source_competitor 字符串"""
        svc = TenantQueryService()
        conn = AsyncMock()

        row = _detail_row(source_competitor="东莞市华创电子有限公司")
        result = MagicMock()
        result.mappings.return_value.first.return_value = _make_mapping(row)

        conn.execute = AsyncMock(return_value=result)

        detail = await svc.v3_company_detail(conn, TENANT_ID, "1")

        assert detail["source_competitor"] == "东莞市华创电子有限公司"

    @pytest.mark.asyncio
    async def test_null_value(self):
        """source_competitor 为 null 时返回 null"""
        svc = TenantQueryService()
        conn = AsyncMock()

        row = _detail_row(source_competitor=None)
        result = MagicMock()
        result.mappings.return_value.first.return_value = _make_mapping(row)

        conn.execute = AsyncMock(return_value=result)

        detail = await svc.v3_company_detail(conn, TENANT_ID, "1")

        assert detail["source_competitor"] is None
