"""tenant 公司列表筛选 SQL 回归测试。"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.tenant_query_service import TenantQueryService

TENANT_ID = "t-001"


def _make_mapping(row_dict):
    """构造支持 [] 取值的 mapping 对象。"""
    mapping = MagicMock()
    mapping.__getitem__ = lambda self, key: row_dict[key]
    mapping.__contains__ = lambda self, key: key in row_dict
    return mapping


def _list_row(**overrides):
    """companies_page 查询返回的单行数据。"""
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
        "data_source_tags": ["外贸通关键词采集"],
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
        "source_competitor_cn": None,
        "system_grade": None,
        "system_score": None,
        "score_adjustment": None,
    }
    base.update(overrides)
    return base


def _mock_conn(row: dict | None = None) -> AsyncMock:
    """构造 companies_page 所需的连接返回值。"""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1 if row is not None else 0
    data_result = MagicMock()
    data_result.mappings.return_value.all.return_value = [_make_mapping(row)] if row else []

    conn = AsyncMock()
    conn.execute = AsyncMock(side_effect=[count_result, data_result])
    return conn


async def _run_companies_page(row: dict | None = None, **kwargs):
    """执行列表查询并返回 rows、total、拼出的 SQL。"""
    svc = TenantQueryService()
    conn = _mock_conn(row or _list_row())
    rows, total = await svc.companies_page(conn, tenant_id=TENANT_ID, limit=10, **kwargs)
    sql = "\n".join(str(call.args[0]) for call in conn.execute.call_args_list)
    return rows, total, sql


class TestTenantCompaniesCollectionTypeFilter:
    """验证采集类型筛选三分支与响应字段。"""

    @pytest.mark.asyncio
    async def test_keyword_filter_uses_jsonb_contains(self):
        """collection_type=keyword 时使用 jsonb 包含条件。"""
        rows, total, sql = await _run_companies_page(collection_type="keyword")
        assert total == 1
        assert rows[0]["collection_type"] == "keyword"
        assert "wc.data_source_tags @>" in sql
        assert """'["外贸通关键词采集"]'::jsonb""" in sql

    @pytest.mark.asyncio
    async def test_reverse_filter_includes_null_and_not_contains(self):
        """collection_type=reverse 时包含 NULL 与 NOT @> 条件。"""
        rows, _total, sql = await _run_companies_page(
            collection_type="reverse",
            row=_list_row(data_source_tags=[]),
        )
        assert rows[0]["collection_type"] == "reverse"
        assert "wc.data_source_tags IS NULL" in sql
        assert "NOT wc.data_source_tags @>" in sql

    @pytest.mark.asyncio
    async def test_none_filter_does_not_add_collection_type_where(self):
        """不传 collection_type 时不添加采集类型 WHERE。"""
        _rows, _total, sql = await _run_companies_page()
        assert "外贸通关键词采集" not in sql

    @pytest.mark.asyncio
    async def test_jsonb_filters_do_not_use_array_overlap(self):
        """source_type、sources、product_tags 不再对 jsonb 使用数组重叠操作符。"""
        _rows, _total, sql = await _run_companies_page(
            source_type="外贸通关键词采集",
            sources=["外贸通关键词采集"],
            product_tags=["PCB"],
        )
        assert "&& ARRAY" not in sql
        assert "&& :" not in sql
        assert "jsonb_build_array(:source_type)" in sql
        assert "jsonb_array_elements_text(wc.data_source_tags)" in sql
        assert "jsonb_array_elements_text(wc.product_tags)" in sql


class TestTenantCompaniesBusinessStatusFilter:
    """验证 business_status 筛选——含 not_new 语义。"""

    @pytest.mark.asyncio
    async def test_not_new_generates_not_equal(self):
        """business_status=not_new 时生成 != 'new' 条件。"""
        _rows, _total, sql = await _run_companies_page(business_status="not_new")
        assert "tc.business_status != 'new'" in sql
        assert ":business_status" not in sql

    @pytest.mark.asyncio
    async def test_exact_match_preserved(self):
        """business_status=new 时仍使用精确匹配。"""
        _rows, _total, sql = await _run_companies_page(business_status="new")
        assert "tc.business_status = :business_status" in sql

    @pytest.mark.asyncio
    async def test_in_group_exact_match(self):
        """business_status=in_group 时使用精确匹配。"""
        _rows, _total, sql = await _run_companies_page(business_status="in_group")
        assert "tc.business_status = :business_status" in sql

    @pytest.mark.asyncio
    async def test_no_filter_no_business_status_clause(self):
        """不传 business_status 时不添加相关 WHERE。"""
        _rows, _total, sql = await _run_companies_page()
        assert "tc.business_status =" not in sql
        assert "tc.business_status !=" not in sql


def _fake_tenant_context():
    """构造 tenant 路由测试上下文。"""
    return TenantAuthContext(
        tenant_id=TENANT_ID,
        tenant_slug="test-tenant",
        user_id="u-001",
        email="test@test.com",
        name="Test",
        roles=["admin"],
        must_change_pwd=False,
        connection=AsyncMock(),
    )


@pytest.fixture
def app():
    """创建带租户依赖覆盖的 FastAPI app。"""
    application = create_app()
    context = _fake_tenant_context()
    application.dependency_overrides[get_current_tenant_user] = lambda: context
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """创建异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestTenantCompaniesRoute:
    """验证 ops.py 透传 collection_type 参数。"""

    @pytest.mark.asyncio
    async def test_collection_type_param_passed_to_service(self, client):
        """GET /companies 将 collection_type 透传给 companies_page。"""
        with patch(
            "app.api.tenant.ops.query_service.companies_page",
            new_callable=AsyncMock,
            return_value=([], 0),
        ) as mock_companies_page:
            response = await client.get(
                "/t/test-tenant/api/v1/companies",
                params={"collection_type": "keyword"},
            )

            assert response.status_code == 200
            mock_companies_page.assert_called_once()
            assert mock_companies_page.call_args.kwargs["collection_type"] == "keyword"
