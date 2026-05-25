"""EngageLab Stats API 集成测试 — TDD 驱动"""

import base64
import json

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
