from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.integrations.openrouter import OpenRouterClient
from app.services.tenant_ai_provider_service import TenantAiProviderService
from tests.helpers import make_engine


async def create_tenant(slug: str) -> str:
    tenant_id = str(new_uuid())
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES (:id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
                """
            ),
            {"id": tenant_id, "slug": slug},
        )
    await engine.dispose()
    return tenant_id


async def test_openrouter_service_masks_secret_and_falls_back_to_key_limit_remaining() -> None:
    tenant_id = await create_tenant(f"or-key-{uuid4().hex[:8]}")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/credits":
            return httpx.Response(403, json={"error": {"message": "management key required"}})
        if request.url.path == "/api/v1/key":
            return httpx.Response(
                200,
                json={"data": {"limit": 10, "limit_remaining": 6.75}},
            )
        return httpx.Response(404)

    service = TenantAiProviderService(client=OpenRouterClient(transport=httpx.MockTransport(handler)))
    engine = make_engine()
    async with engine.begin() as conn:
        result = await service.upsert_config(conn, tenant_id=tenant_id, api_key="sk-or-v1-demo-secret-token")
    await engine.dispose()

    assert result["is_configured"] is True
    assert result["secret_masked"] != "sk-or-v1-demo-secret-token"
    assert result["balance"]["status"] == "available"
    assert result["balance"]["source"] == "key"
    assert result["balance"]["amount"] == 6.75


async def test_openrouter_service_unknown_when_key_has_no_limit_remaining() -> None:
    tenant_id = await create_tenant(f"or-unknown-{uuid4().hex[:8]}")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/credits":
            return httpx.Response(403, json={"error": {"message": "management key required"}})
        if request.url.path == "/api/v1/key":
            return httpx.Response(200, json={"data": {"limit": None, "limit_remaining": None}})
        return httpx.Response(404)

    service = TenantAiProviderService(client=OpenRouterClient(transport=httpx.MockTransport(handler)))
    engine = make_engine()
    async with engine.begin() as conn:
        result = await service.upsert_config(conn, tenant_id=tenant_id, api_key="sk-or-v1-demo-secret-token")
        assert result["balance"]["status"] == "unknown"
        with pytest.raises(AppError) as exc_info:
            await service.assert_feature_available(conn, tenant_id=tenant_id)
    await engine.dispose()

    assert exc_info.value.code == "OPENROUTER_BALANCE_UNKNOWN"


async def test_openrouter_service_invalid_key_maps_to_422() -> None:
    tenant_id = await create_tenant(f"or-invalid-{uuid4().hex[:8]}")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    service = TenantAiProviderService(client=OpenRouterClient(transport=httpx.MockTransport(handler)))
    engine = make_engine()
    async with engine.begin() as conn:
        result = await service.upsert_config(conn, tenant_id=tenant_id, api_key="sk-or-v1-invalid-token")
        assert result["balance"]["status"] == "invalid_api_key"
        with pytest.raises(AppError) as exc_info:
            await service.assert_feature_available(conn, tenant_id=tenant_id)
    await engine.dispose()

    assert exc_info.value.code == "INVALID_OPENROUTER_API_KEY"
