"""EngageLab Stats API 集成测试 — TDD 驱动"""

import base64
import time
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.integrations.engagelab import EngageLabClient, EngageLabSendError


# ── U1: 配置层 ──────────────────────────────────────────────


class TestStatsBaseUrlConfig:
    def test_stats_base_url_default(self):
        """未设置 ENGAGELAB_STATS_BASE_URL 时，返回默认值"""
        settings = Settings(
            _env_file=None,
            DATABASE_URL="postgresql+asyncpg://x@localhost/x",
            JWT_SECRET="s",
            ADMIN_EMAIL="a@b.c",
            ADMIN_PASSWORD="p",
            DATA_SOURCE_ENCRYPTION_KEY="k",
            INTERNAL_SERVICE_SECRET="s",
            ENGAGELAB_WEBHOOK_SECRET="ws",
        )
        assert settings.engagelab_stats_base_url == "https://email.api.engagelab.cc"


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        _env_file=None,
        DATABASE_URL="postgresql+asyncpg://x@localhost/x",
        JWT_SECRET="s",
        ADMIN_EMAIL="a@b.c",
        ADMIN_PASSWORD="p",
        DATA_SOURCE_ENCRYPTION_KEY="k",
        INTERNAL_SERVICE_SECRET="s",
        ENGAGELAB_WEBHOOK_SECRET="ws",
        ENGAGELAB_API_USER="test_user",
        ENGAGELAB_CREDENTIAL="test_credential",
        ENGAGELAB_STATS_BASE_URL="https://email.api.engagelab.cc",
    )
    defaults.update(overrides)
    return Settings(**defaults)


# ── U2: 集成层 ──────────────────────────────────────────────


MOCK_SUMMARY_RESPONSE = {
    "result": {
        "targets": 100,
        "sent": 90,
        "delivered": 85,
        "delivered_percent": 94.4,
        "invalid_email": 3,
        "soft_bounce": 2,
        "billing_count": 90,
        "total_opens": 50,
        "total_open_percent": 58.8,
        "opens": 30,
        "open_percent": 35.3,
        "report_spam": 1,
        "unsubscribe": 2,
    }
}

MOCK_DAILY_RESPONSE = {
    "result": [
        {"send_date": "2026-05-01", "sent": 30, "delivered": 28, "total_opens": 15},
        {"send_date": "2026-05-02", "sent": 30, "delivered": 29, "total_opens": 10},
        {"send_date": "2026-05-03", "sent": 30, "delivered": 28, "total_opens": 25},
    ]
}


class TestGetStatsDay:
    @pytest.mark.asyncio
    async def test_aggregate_summary(self):
        """aggregate_by=1 返回汇总 dict"""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/stats_day"
            assert "start_date=2026-05-01" in str(request.url)
            assert "aggregate_by=1" in str(request.url)
            return httpx.Response(200, json=MOCK_SUMMARY_RESPONSE)

        transport = httpx.MockTransport(handler)
        client = EngageLabClient(settings=_make_settings(), transport=transport)
        result = await client.get_stats_day("2026-05-01", "2026-05-25", aggregate_by=1)
        assert result["targets"] == 100
        assert result["delivered"] == 85

    @pytest.mark.asyncio
    async def test_aggregate_daily(self):
        """aggregate_by=0 返回每日明细 list"""

        def handler(request: httpx.Request) -> httpx.Response:
            assert "aggregate_by=0" in str(request.url)
            return httpx.Response(200, json=MOCK_DAILY_RESPONSE)

        transport = httpx.MockTransport(handler)
        client = EngageLabClient(settings=_make_settings(), transport=transport)
        result = await client.get_stats_day("2026-05-01", "2026-05-03", aggregate_by=0)
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["send_date"] == "2026-05-01"

    @pytest.mark.asyncio
    async def test_api_error_raises(self):
        """API 返回非 200 时 raise EngageLabSendError"""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "internal"})

        transport = httpx.MockTransport(handler)
        client = EngageLabClient(settings=_make_settings(), transport=transport)
        with pytest.raises(EngageLabSendError):
            await client.get_stats_day("2026-05-01", "2026-05-25", aggregate_by=1)

    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self):
        """凭证未配置时 raise EngageLabSendError，不发起 HTTP 请求"""
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json={})

        transport = httpx.MockTransport(handler)
        settings = _make_settings(ENGAGELAB_API_USER="", ENGAGELAB_CREDENTIAL="")
        client = EngageLabClient(settings=settings, transport=transport)
        with pytest.raises(EngageLabSendError):
            await client.get_stats_day("2026-05-01", "2026-05-25", aggregate_by=1)
        assert not called

    @pytest.mark.asyncio
    async def test_auth_header_correct(self):
        """请求头包含正确的 Authorization: Basic base64(user:credential)"""
        captured_headers = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json=MOCK_SUMMARY_RESPONSE)

        transport = httpx.MockTransport(handler)
        client = EngageLabClient(settings=_make_settings(), transport=transport)
        await client.get_stats_day("2026-05-01", "2026-05-25", aggregate_by=1)

        expected = "Basic " + base64.b64encode(b"test_user:test_credential").decode()
        assert captured_headers["authorization"] == expected


# ── U3: 服务层 ──────────────────────────────────────────────


def _mock_client(summary_res=None, daily_res=None, err=None):
    cl = MagicMock()
    if err:
        cl.get_stats_day = AsyncMock(side_effect=err)
        return cl

    async def get_stats(sd, ed, *, aggregate_by=1):
        if aggregate_by == 1:
            return summary_res if summary_res is not None else {}
        return daily_res if daily_res is not None else []

    cl.get_stats_day = AsyncMock(side_effect=get_stats)
    return cl


class TestEmailStatsByDateRange:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from app.services import tenant_query_service as m

        m._stats_cache.clear()
        yield
        m._stats_cache.clear()

    @pytest.mark.asyncio
    async def test_normal_summary(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client(MOCK_SUMMARY_RESPONSE["result"], MOCK_DAILY_RESPONSE["result"])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            r = await TenantQueryService().email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
        s = r["summary"]
        assert s["targets"] == 100
        assert s["delivered"] == 85
        assert s["billing"] == 90
        assert isinstance(s["delivered_percent"], float)
        assert s["delivered_percent"] == 94.4

    @pytest.mark.asyncio
    async def test_normal_daily(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client(MOCK_SUMMARY_RESPONSE["result"], MOCK_DAILY_RESPONSE["result"])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            r = await TenantQueryService().email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
        d = r["daily"]
        assert len(d) == 3
        assert d[0]["date"] == "2026-05-01"
        assert d[0]["opens"] == 15

    @pytest.mark.asyncio
    async def test_empty_data(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client({}, [])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            r = await TenantQueryService().email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
        assert r["summary"]["targets"] == 0
        assert len(r["daily"]) == 3
        assert r["daily"][0] == {"date": "2026-05-01", "sent": 0, "delivered": 0, "opens": 0}

    @pytest.mark.asyncio
    async def test_error_degradation(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client(err=EngageLabSendError("x"))
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            r = await TenantQueryService().email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
        assert r["summary"]["targets"] == 0
        assert r["daily"] == []

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client(MOCK_SUMMARY_RESPONSE["result"], MOCK_DAILY_RESPONSE["result"])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            svc = TenantQueryService()
            await svc.email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
            await svc.email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
        assert mc.get_stats_day.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_expired(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client(MOCK_SUMMARY_RESPONSE["result"], MOCK_DAILY_RESPONSE["result"])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            with patch("app.services.tenant_query_service.time") as mt:
                mt.monotonic.side_effect = [0.0, 301.0, 301.0]
                svc = TenantQueryService()
                await svc.email_stats_by_date_range(
                    MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
                )
                await svc.email_stats_by_date_range(
                    MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
                )
        assert mc.get_stats_day.call_count == 4

    @pytest.mark.asyncio
    async def test_billing_mapping(self):
        from app.services.tenant_query_service import TenantQueryService

        mc = _mock_client({**MOCK_SUMMARY_RESPONSE["result"], "billing_count": 77}, [])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            r = await TenantQueryService().email_stats_by_date_range(
                MagicMock(), "t", date(2026, 5, 1), date(2026, 5, 3)
            )
        assert r["summary"]["billing"] == 77


# ── U4: 路由层端到端 ──────────────────────────────────────────


class TestDashboardEmailStatsRoute:
    @pytest.fixture
    def app(self):
        from app.main import create_app
        from app.security.dependencies import TenantAuthContext, get_current_tenant_user

        application = create_app()
        conn = AsyncMock()
        ctx = TenantAuthContext(
            tenant_id="t-001",
            tenant_slug="test-tenant",
            user_id="u-001",
            email="test@test.com",
            name="Test",
            roles=["admin"],
            must_change_pwd=False,
            connection=conn,
        )
        application.dependency_overrides[get_current_tenant_user] = lambda: ctx
        yield application
        application.dependency_overrides.clear()

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        from app.services import tenant_query_service as m

        m._stats_cache.clear()
        yield
        m._stats_cache.clear()

    @pytest.mark.asyncio
    async def test_email_stats_route_returns_summary_and_daily(self, app):
        import httpx

        mc = _mock_client(MOCK_SUMMARY_RESPONSE["result"], MOCK_DAILY_RESPONSE["result"])
        with patch("app.services.tenant_query_service.EngageLabClient", return_value=mc):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get(
                    "/t/test-tenant/api/v1/dashboard/email-stats",
                    params={"start_date": "2026-05-01", "end_date": "2026-05-03"},
                )

        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]

        s = data["summary"]
        assert s["targets"] == 100
        assert s["delivered"] == 85
        assert s["billing"] == 90
        assert s["delivered_percent"] == 94.4
        assert s["open_percent"] == 35.3

        d = data["daily"]
        assert len(d) == 3
        assert d[0]["date"] == "2026-05-01"
        assert d[0]["opens"] == 15
