"""GET /prospects 路由与 service 签名对齐防回归（pcb_supplier_presence 移除后）。"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.tenant_query_service import TenantQueryService


class TestProspectsSignatureAligned:
    def test_pcb_supplier_presence_fully_removed(self):
        import app.api.tenant.ops as ops_mod
        import app.services.company_filter_sql as filter_mod
        import app.services.tenant_query_service as query_mod

        for mod in (ops_mod, query_mod, filter_mod):
            assert "pcb_supplier_presence" not in inspect.getsource(mod)

    @pytest.mark.asyncio
    async def test_prospects_accepts_route_kwargs(self):
        """按路由实际传参调用 service，签名不匹配会在此抛 TypeError。"""
        result = MagicMock()
        result.mappings.return_value.all.return_value = []
        conn = AsyncMock()
        conn.execute.return_value = result

        items = await TenantQueryService().prospects(
            conn,
            "tenant-001",
            keyword=None,
            countries=None,
            sub_industries=None,
            product_tags=None,
            sources=None,
            employee_count_min=None,
            employee_count_max=None,
            trade_amount_min=None,
            trade_amount_max=None,
            trade_count_min=None,
            trade_count_max=None,
            contact_count_min=None,
            contact_count_max=None,
            founded_year_from=None,
            founded_year_to=None,
            limit=50,
        )
        assert items == []
