from datetime import UTC, datetime

import pytest

from app.services.tenant_query_service import SENT_SCOPE_FILTER, TenantQueryService

TENANT_ID = "33333333-3333-3333-3333-333333333333"
PLAN_ID = "44444444-4444-4444-8444-444444444444"


class FakeMappingResult:
    def __init__(self, *, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def mappings(self):
        return self

    def one(self):
        return self.row

    def all(self):
        return self.rows


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakePlanOverviewConn:
    def __init__(self):
        self.executions = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.executions.append((sql, params or {}))

        if "tenant_keyword" in sql:
            return FakeMappingResult(
                row={
                    "keyword_count": 1,
                    "companies_collected": 2,
                    "companies_scored": 1,
                    "contacts_total": 3,
                }
            )
        if "FROM emails" in sql:
            return FakeMappingResult(row={"emails_drafted": 5, "emails_sent": 80})
        if "FROM sending_plans" in sql:
            return FakeMappingResult(rows=[])
        return FakeMappingResult(row={})


class FakeDailyQuotaConn:
    def __init__(self):
        self.executions = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.executions.append((sql, params or {}))
        if "FROM domain_warmup_status" in sql:
            return FakeScalarResult(100)
        if "FROM emails" in sql:
            return FakeScalarResult(80)
        return FakeScalarResult(0)


@pytest.mark.asyncio
async def test_plan_overview_tenant_sent_scope_excludes_failed():
    """覆盖 AE19：计划概览租户级 emails_sent 剔除 failed。"""
    conn = FakePlanOverviewConn()

    result = await TenantQueryService().plan_overview(conn, TENANT_ID)

    assert result["emails_sent"] == 80
    email_sql = [sql for sql, _ in conn.executions if "FROM emails" in sql][0]
    assert SENT_SCOPE_FILTER in email_sql


@pytest.mark.asyncio
async def test_plan_overview_plan_sent_scope_excludes_failed():
    """覆盖 AE19：计划概览计划级 emails_sent 剔除 failed。"""
    conn = FakePlanOverviewConn()

    await TenantQueryService().plan_overview(conn, TENANT_ID, plan_id=PLAN_ID)

    email_sql, email_params = [
        (sql, params) for sql, params in conn.executions if "FROM emails" in sql
    ][0]
    assert SENT_SCOPE_FILTER in email_sql
    assert email_params["plan_id"] == PLAN_ID


@pytest.mark.asyncio
async def test_daily_quota_sent_scope_excludes_failed():
    """覆盖 AE19：每日配额今日已发送剔除 failed。"""
    conn = FakeDailyQuotaConn()

    result = await TenantQueryService().daily_quota(
        conn,
        TENANT_ID,
        now_utc=datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
    )

    assert result == {"limit": 100, "used": 80, "remaining": 20}
    email_sql, email_params = [
        (sql, params) for sql, params in conn.executions if "FROM emails" in sql
    ][0]
    assert SENT_SCOPE_FILTER in email_sql
    assert email_params["tenant_id"] == TENANT_ID
