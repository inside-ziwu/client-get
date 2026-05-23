"""发送计划列表筛选、分页 service 层测试"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.tenant_messaging_service import TenantMessagingService

TENANT_ID = "t-001"


def _make_plan_row(*, name="测试计划", status="draft", created_at=None):
    """构造模拟的数据库行"""
    now = created_at or datetime(2026, 5, 23, 10, 0, 0)
    return {
        "id": "plan-001",
        "name": name,
        "description": "desc",
        "status": status,
        "recipient_source": "csv",
        "recipient_config": None,
        "send_strategy": "immediate",
        "sender_name": "Test",
        "sender_email": "test@test.com",
        "domain_id": None,
        "total_recipients": 0,
        "sent_count": 0,
        "scheduled_at": None,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }


def _mock_conn_with_rows(rows: list[dict]) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = rows
    conn = AsyncMock()
    conn.execute.return_value = mock_result
    return conn


class TestListSendingPlansStatusFilter:
    """U1: status 参数筛选"""

    @pytest.mark.asyncio
    async def test_no_status_returns_all(self):
        rows = [_make_plan_row(status="draft"), _make_plan_row(status="running")]
        conn = _mock_conn_with_rows(rows)
        svc = TenantMessagingService()

        result = await svc.list_sending_plans(conn, TENANT_ID)

        assert len(result) == 2
        sql_text = conn.execute.call_args[0][0].text
        assert "status" not in sql_text or "deleted_at" in sql_text

    @pytest.mark.asyncio
    async def test_status_draft_filters(self):
        rows = [_make_plan_row(status="draft")]
        conn = _mock_conn_with_rows(rows)
        svc = TenantMessagingService()

        result = await svc.list_sending_plans(conn, TENANT_ID, status="draft")

        assert len(result) == 1
        sql_text = conn.execute.call_args[0][0].text
        assert "status = :status" in sql_text
        params = conn.execute.call_args[0][1]
        assert params["status"] == "draft"

    @pytest.mark.asyncio
    async def test_status_running_filters(self):
        rows = [_make_plan_row(status="running")]
        conn = _mock_conn_with_rows(rows)
        svc = TenantMessagingService()

        result = await svc.list_sending_plans(conn, TENANT_ID, status="running")

        sql_text = conn.execute.call_args[0][0].text
        assert "status = :status" in sql_text
        params = conn.execute.call_args[0][1]
        assert params["status"] == "running"


class TestListSendingPlansKeywordFilter:
    """U2: keyword 模糊搜索"""

    @pytest.mark.asyncio
    async def test_keyword_generates_ilike(self):
        rows = [_make_plan_row(name="巴西客户计划")]
        conn = _mock_conn_with_rows(rows)
        svc = TenantMessagingService()

        await svc.list_sending_plans(conn, TENANT_ID, keyword="巴西")

        sql_text = conn.execute.call_args[0][0].text
        assert "ILIKE" in sql_text.upper()
        params = conn.execute.call_args[0][1]
        assert params["keyword"] == "%巴西%"

    @pytest.mark.asyncio
    async def test_empty_keyword_ignored(self):
        rows = []
        conn = _mock_conn_with_rows(rows)
        svc = TenantMessagingService()

        await svc.list_sending_plans(conn, TENANT_ID, keyword="")

        sql_text = conn.execute.call_args[0][0].text
        assert "ILIKE" not in sql_text.upper()


class TestListSendingPlansDateFilter:
    """U3: 日期范围筛选"""

    @pytest.mark.asyncio
    async def test_date_from_generates_gte(self):
        conn = _mock_conn_with_rows([])
        svc = TenantMessagingService()

        await svc.list_sending_plans(conn, TENANT_ID, date_from="2026-05-01")

        sql_text = conn.execute.call_args[0][0].text
        assert "created_at >= :date_from" in sql_text
        params = conn.execute.call_args[0][1]
        assert params["date_from"] == "2026-05-01"

    @pytest.mark.asyncio
    async def test_date_to_includes_whole_day(self):
        """date_to 包含当天：加一天处理"""
        conn = _mock_conn_with_rows([])
        svc = TenantMessagingService()

        await svc.list_sending_plans(conn, TENANT_ID, date_to="2026-05-23")

        sql_text = conn.execute.call_args[0][0].text
        assert "created_at < :date_to" in sql_text
        params = conn.execute.call_args[0][1]
        assert params["date_to"] == "2026-05-24"

    @pytest.mark.asyncio
    async def test_both_dates_combined(self):
        conn = _mock_conn_with_rows([])
        svc = TenantMessagingService()

        await svc.list_sending_plans(conn, TENANT_ID, date_from="2026-05-01", date_to="2026-05-23")

        sql_text = conn.execute.call_args[0][0].text
        assert "created_at >= :date_from" in sql_text
        assert "created_at < :date_to" in sql_text


class TestListSendingPlansPagination:
    """U4: 分页 + COUNT(*)"""

    @pytest.mark.asyncio
    async def test_returns_items_and_total(self):
        """带 page/page_size 时返回 {items, total} 结构"""
        rows = [_make_plan_row()]
        count_result = MagicMock()
        count_result.scalar_one.return_value = 5

        data_result = MagicMock()
        data_result.mappings.return_value.all.return_value = rows

        conn = AsyncMock()
        conn.execute.side_effect = [count_result, data_result]
        svc = TenantMessagingService()

        result = await svc.list_sending_plans(conn, TENANT_ID, page=1, page_size=20)

        assert "items" in result
        assert result["total"] == 5
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_offset_calculation(self):
        """page=2, page_size=10 → OFFSET 10"""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 25

        data_result = MagicMock()
        data_result.mappings.return_value.all.return_value = []

        conn = AsyncMock()
        conn.execute.side_effect = [count_result, data_result]
        svc = TenantMessagingService()

        await svc.list_sending_plans(conn, TENANT_ID, page=2, page_size=10)

        data_sql = conn.execute.call_args_list[1][0][0].text
        assert "LIMIT" in data_sql
        assert "OFFSET" in data_sql
        params = conn.execute.call_args_list[1][0][1]
        assert params["limit"] == 10
        assert params["offset"] == 10

    @pytest.mark.asyncio
    async def test_without_pagination_returns_list(self):
        """不传 page/page_size 时保持原有列表返回"""
        rows = [_make_plan_row()]
        conn = _mock_conn_with_rows(rows)
        svc = TenantMessagingService()

        result = await svc.list_sending_plans(conn, TENANT_ID)

        assert isinstance(result, list)
        assert len(result) == 1
