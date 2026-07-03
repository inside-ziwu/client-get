from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.tenant_messaging_service import (
    TenantMessagingService,
)
from app.services.tenant_query_service import TenantQueryService
from app.utils.beijing_time import beijing_day_bounds, beijing_today

DOMAIN_ID = "11111111-1111-1111-1111-111111111111"
PLAN_ID = "22222222-2222-2222-2222-222222222222"
TENANT_ID = "33333333-3333-3333-3333-333333333333"


class FakeResult:
    def __init__(self, *, row=None, scalar=None):
        self.row = row
        self.scalar = scalar

    def mappings(self):
        return self

    def first(self):
        return self.row

    def scalar_one(self):
        return self.scalar


class FakeQuotaWindowConn:
    def __init__(self, *, reserve_update_row=None, domain_row=None, second_update_row=None):
        self.reserve_update_row = reserve_update_row
        self.domain_row = domain_row or {
            "tenant_id": UUID(TENANT_ID),
            "daily_limit": 9000,
        }
        self.second_update_row = second_update_row
        self.executions = []
        self._domain_usage_updates = 0

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.executions.append((sql, params))

        if "UPDATE domain_daily_usage" in sql:
            self._domain_usage_updates += 1
            if self._domain_usage_updates == 1:
                return FakeResult(row=self.reserve_update_row)
            return FakeResult(row=self.second_update_row)

        if "FROM domain_warmup_status" in sql:
            return FakeResult(row=self.domain_row)

        if "SELECT domain_id FROM sending_plans" in sql:
            return FakeResult(row={"domain_id": UUID(DOMAIN_ID)})

        return FakeResult()

    def domain_usage_calls(self):
        return [(sql, params) for sql, params in self.executions if "domain_daily_usage" in sql]


class FakeDailyQuotaConn:
    def __init__(self):
        self.executions = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.executions.append((sql, params))
        if "FROM domain_warmup_status" in sql:
            return FakeResult(scalar=9000)
        if "FROM emails" in sql:
            return FakeResult(scalar=12)
        return FakeResult(scalar=0)


def test_beijing_today_crosses_at_utc_16_boundary():
    """覆盖 AE10：北京自然日窗口不跟随 UTC 零点拆分。"""
    assert beijing_today(datetime(2026, 7, 2, 15, 59, tzinfo=UTC)) == date(2026, 7, 2)
    assert beijing_today(datetime(2026, 7, 2, 16, 1, tzinfo=UTC)) == date(2026, 7, 3)


def test_beijing_today_rejects_naive_datetime():
    with pytest.raises(ValueError):
        beijing_today(datetime(2026, 7, 2, 16, 0))


@pytest.mark.asyncio
async def test_reserve_domain_quota_uses_beijing_usage_date_for_all_statements():
    """覆盖 AE9：北京零点后配额门/预留都写入新的北京日窗口。"""
    usage_date = date(2026, 7, 3)
    conn = FakeQuotaWindowConn(
        second_update_row={
            "id": UUID("44444444-4444-4444-8444-444444444444"),
            "domain_id": UUID(DOMAIN_ID),
            "usage_date": usage_date,
            "daily_limit": 9000,
            "reserved_count": 1,
            "sent_count": 0,
            "failed_count": 0,
        }
    )

    result = await TenantMessagingService().reserve_domain_quota(
        conn,
        domain_id=DOMAIN_ID,
        count=1,
        now_utc=datetime(2026, 7, 2, 16, 30, tzinfo=UTC),
    )

    assert result["usage_date"] == "2026-07-03"
    for sql, params in conn.domain_usage_calls():
        assert "CURRENT_DATE" not in sql
        assert params["usage_date"] == usage_date


@pytest.mark.asyncio
async def test_release_reserved_quota_uses_beijing_usage_date():
    """覆盖 AE12：释放预留配额也按同一个北京日窗口回退。"""
    conn = FakeQuotaWindowConn()

    await TenantMessagingService()._release_reserved_quota(
        conn,
        domain_id=None,
        plan_id=PLAN_ID,
        now_utc=datetime(2026, 7, 2, 16, 30, tzinfo=UTC),
    )

    quota_sql, quota_params = conn.domain_usage_calls()[0]
    assert "CURRENT_DATE" not in quota_sql
    assert quota_params == {"domain_id": DOMAIN_ID, "usage_date": date(2026, 7, 3)}


@pytest.mark.asyncio
async def test_reserve_domain_quota_still_raises_when_limit_is_exceeded():
    """超限行为不因窗口改造而变化。"""
    conn = FakeQuotaWindowConn(second_update_row=None)

    with pytest.raises(AppError) as exc_info:
        await TenantMessagingService().reserve_domain_quota(
            conn,
            domain_id=DOMAIN_ID,
            count=1,
            now_utc=datetime(2026, 7, 2, 16, 30, tzinfo=UTC),
        )

    assert exc_info.value.code == "QUOTA_EXCEEDED"


def test_beijing_day_bounds_are_aware_instants():
    today, tomorrow = beijing_day_bounds(datetime(2026, 7, 3, 1, 0, tzinfo=UTC))

    assert today.astimezone(UTC) == datetime(2026, 7, 2, 16, 0, tzinfo=UTC)
    assert tomorrow.astimezone(UTC) == datetime(2026, 7, 3, 16, 0, tzinfo=UTC)
    assert tomorrow - today == timedelta(days=1)


@pytest.mark.asyncio
async def test_daily_quota_uses_beijing_day_timestamptz_bounds():
    """覆盖 AE9：daily_quota 今日统计按北京日零点瞬时取 created_at 范围。"""
    conn = FakeDailyQuotaConn()

    result = await TenantQueryService().daily_quota(
        conn,
        tenant_id=TENANT_ID,
        now_utc=datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
    )

    assert result == {"limit": 9000, "used": 12, "remaining": 8988}
    email_params = conn.executions[1][1]
    assert email_params["today"].astimezone(UTC) == datetime(2026, 7, 2, 16, 0, tzinfo=UTC)
    assert email_params["tomorrow"].astimezone(UTC) == datetime(2026, 7, 3, 16, 0, tzinfo=UTC)
