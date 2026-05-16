from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.integrations.openrouter import OpenRouterClient
from app.security.jwt import create_access_token


def make_service_token(service_name: str, scopes: list[str]) -> str:
    return create_access_token(
        {
            "sub": f"{service_name}-instance",
            "kind": "service",
            "service_name": service_name,
            "scopes": scopes,
        }
    )


def make_engine():
    settings = get_settings()
    return create_async_engine(settings.database_url, future=True)


async def create_tenant_via_admin(client: AsyncClient, admin_token: str, *, slug: str, password: str = "temporary-password") -> dict:
    response = await client.post(
        "/admin/api/v1/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": f"租户-{slug}",
            "slug": slug,
            "industry": "PCB",
            "contact_name": "测试用户",
            "contact_phone": "13800000000",
            "admin_email": f"{slug}@example.com",
            "admin_name": "测试用户",
            "admin_password": password,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def login_tenant(client: AsyncClient, *, slug: str, password: str = "temporary-password") -> str:
    response = await client.post(
        f"/t/{slug}/api/v1/auth/login",
        json={"email": f"{slug}@example.com", "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def install_openrouter_transport(transport) -> None:
    from app.api.admin import tenants as admin_tenants_api
    from app.api.tenant import core as tenant_core_api
    from app.api.tenant import intelligence as tenant_intelligence_api
    from app.api.tenant import messaging as tenant_messaging_api
    from app.api.tenant import settings as tenant_settings_api
    from app.api.internal import ops as internal_ops_api

    client = OpenRouterClient(transport=transport)
    admin_tenants_api.ai_provider_service.client = client
    tenant_settings_api.ai_provider_service.client = client
    tenant_core_api.service.ai_provider.client = client
    tenant_messaging_api.service.ai_provider.client = client
    tenant_intelligence_api.service.ai_provider.client = client
    internal_ops_api.service.scoring.ai_provider.client = client
    internal_ops_api.service.messaging.ai_provider.client = client
    internal_ops_api.service.intelligence.ai_provider.client = client
