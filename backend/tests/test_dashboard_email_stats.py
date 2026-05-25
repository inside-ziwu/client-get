"""仪表盘 email-stats 本地 DB 聚合测试 — TDD 驱动"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.tenant_query_service import TenantQueryService


# ── 辅助工具 ──────────────────────────────────────────────


def _make_summary_row(
    targets=0, sent=0, delivered=0, invalid_email=0, soft_bounce=0,
    total_opens=0, opens=0, report_spam=0, unsubscribe=0,
):
    """构造汇总查询返回的 MappingResult 行"""
    return {
        "targets": targets,
        "sent": sent,
        "delivered": delivered,
        "invalid_email": invalid_email,
        "soft_bounce": soft_bounce,
        "total_opens": total_opens,
        "opens": opens,
        "report_spam": report_spam,
        "unsubscribe": unsubscribe,
    }


def _make_daily_rows(*rows):
    """构造每日明细查询返回的 MappingResult 行列表"""
    result = []
    for r in rows:
        result.append({
            "date": r[0],
            "sent": r[1],
            "delivered": r[2],
            "opens": r[3],
        })
    return result


def _mock_conn(summary_row, daily_rows):
    """构造 mock conn，按调用顺序返回汇总和每日明细"""
    conn = AsyncMock()

    summary_mapping = MagicMock()
    summary_mapping.one.return_value = summary_row

    daily_mapping = MagicMock()
    daily_mapping.all.return_value = daily_rows

    summary_result = MagicMock()
    summary_result.mappings.return_value = summary_mapping

    daily_result = MagicMock()
    daily_result.mappings.return_value = daily_mapping

    conn.execute = AsyncMock(side_effect=[summary_result, daily_result])
    return conn


# ── 服务层测试 ──────────────────────────────────────────────


class TestEmailStatsByDateRange:
    @pytest.mark.asyncio
    async def test_normal_data(self):
        """正常数据：各 FILTER 计数正确"""
        summary = _make_summary_row(
            targets=20, sent=15, delivered=12, invalid_email=2,
            soft_bounce=1, total_opens=30, opens=8, report_spam=1, unsubscribe=1,
        )
        daily = _make_daily_rows(
            (date(2026, 5, 1), 8, 7, 5),
            (date(2026, 5, 2), 7, 5, 3),
        )
        conn = _mock_conn(summary, daily)

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 2)
        )

        s = r["summary"]
        assert s["targets"] == 20
        assert s["sent"] == 15
        assert s["delivered"] == 12
        assert s["invalid_email"] == 2
        assert s["soft_bounce"] == 1
        assert s["total_opens"] == 30
        assert s["opens"] == 8
        assert s["report_spam"] == 1
        assert s["unsubscribe"] == 1

    @pytest.mark.asyncio
    async def test_percentage_calculation(self):
        """百分比计算：以 sent 为分母，保留两位小数"""
        summary = _make_summary_row(
            targets=15, sent=10, delivered=8, total_opens=5, opens=3,
        )
        conn = _mock_conn(summary, [])

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 3)
        )

        s = r["summary"]
        assert s["delivered_percent"] == 80.0
        assert s["total_open_percent"] == 50.0
        assert s["open_percent"] == 30.0

    @pytest.mark.asyncio
    async def test_billing_equals_sent(self):
        """billing 字段值 == sent 字段值"""
        summary = _make_summary_row(targets=20, sent=15)
        conn = _mock_conn(summary, [])

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 3)
        )

        assert r["summary"]["billing"] == r["summary"]["sent"]
        assert r["summary"]["billing"] == 15

    @pytest.mark.asyncio
    async def test_empty_data(self):
        """空数据：summary 全 0、百分比全 0、daily 为空"""
        summary = _make_summary_row()
        conn = _mock_conn(summary, [])

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 3)
        )

        s = r["summary"]
        assert s["targets"] == 0
        assert s["sent"] == 0
        assert s["delivered_percent"] == 0
        assert s["total_open_percent"] == 0
        assert s["open_percent"] == 0
        assert r["daily"] == []

    @pytest.mark.asyncio
    async def test_sent_zero_no_division_error(self):
        """sent=0 时百分比为 0，不抛除零错误"""
        summary = _make_summary_row(targets=5, sent=0, delivered=0)
        conn = _mock_conn(summary, [])

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 3)
        )

        s = r["summary"]
        assert s["delivered_percent"] == 0
        assert s["total_open_percent"] == 0
        assert s["open_percent"] == 0

    @pytest.mark.asyncio
    async def test_daily_grouped_by_date(self):
        """每日明细按日期分组、升序返回"""
        daily = _make_daily_rows(
            (date(2026, 5, 1), 10, 8, 5),
            (date(2026, 5, 2), 5, 4, 2),
            (date(2026, 5, 3), 8, 7, 3),
        )
        conn = _mock_conn(_make_summary_row(sent=23), daily)

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 3)
        )

        d = r["daily"]
        assert len(d) == 3
        assert d[0]["date"] == "2026-05-01"
        assert d[0]["sent"] == 10
        assert d[1]["date"] == "2026-05-02"
        assert d[2]["date"] == "2026-05-03"
        assert d[2]["opens"] == 3

    @pytest.mark.asyncio
    async def test_date_range_filter(self):
        """验证 SQL 参数传递了正确的日期范围"""
        conn = _mock_conn(_make_summary_row(), [])

        await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 10), date(2026, 5, 20)
        )

        args = conn.execute.call_args_list[0]
        params = args[0][1] if len(args[0]) > 1 else args[1].get("parameters", {})
        assert str(params["start_date"]) == "2026-05-10"
        assert str(params["end_date"]) == "2026-05-20"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """租户隔离：tenant_id 被正确传入 SQL 查询"""
        conn = _mock_conn(_make_summary_row(), [])

        await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-xyz", date(2026, 5, 1), date(2026, 5, 3)
        )

        for call in conn.execute.call_args_list:
            params = call[0][1] if len(call[0]) > 1 else call[1].get("parameters", {})
            assert params["tenant_id"] == "tenant-xyz"


# ── 13 字段完整性断言 ──────────────────────────────────────────

EXPECTED_SUMMARY_KEYS = {
    "targets", "sent", "delivered", "delivered_percent",
    "invalid_email", "soft_bounce", "billing",
    "total_opens", "total_open_percent", "opens", "open_percent",
    "report_spam", "unsubscribe",
}


class TestSummaryFieldCompleteness:
    @pytest.mark.asyncio
    async def test_all_13_fields_present(self):
        """summary 包含全部 13 个字段"""
        conn = _mock_conn(_make_summary_row(sent=10, delivered=8), [])

        r = await TenantQueryService().email_stats_by_date_range(
            conn, "tenant-001", date(2026, 5, 1), date(2026, 5, 3)
        )

        assert set(r["summary"].keys()) == EXPECTED_SUMMARY_KEYS
