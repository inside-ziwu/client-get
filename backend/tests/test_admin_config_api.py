from uuid import uuid4

import httpx
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.helpers import install_openrouter_transport
from tests.test_auth_integration import login_admin


async def test_admin_credentials_masking_and_scene_default_validation() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)
            credential_response = await client.post(
                "/admin/api/v1/data-sources/waimao_tong/credentials",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "account_no": f"acct-{uuid4().hex[:8]}",
                    "username": "robot-user",
                    "secret": "super-secret-token",
                    "rotation_order": 1,
                    "daily_quota": 100,
                },
            )
            assert credential_response.status_code == 200, credential_response.text
            credential_id = credential_response.json()["data"]["id"]
            assert credential_response.json()["data"]["secret_masked"] != "super-secret-token"

            list_response = await client.get(
                "/admin/api/v1/data-sources/waimao_tong/credentials",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert list_response.status_code == 200, list_response.text
            items = list_response.json()["data"]
            matched = next(item for item in items if item["id"] == credential_id)
            assert matched["secret_masked"] != "super-secret-token"
            assert "secret" not in matched

            create_model_response = await client.post(
                "/admin/api/v1/ai-config/models",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "provider": "openrouter",
                    "model_id": f"test-model-{uuid4().hex[:8]}",
                    "display_name": "Inactive Test Model",
                    "is_active": False,
                    "config": {},
                },
            )
            assert create_model_response.status_code == 200, create_model_response.text
            model_id = create_model_response.json()["data"]["id"]

            scene_defaults_response = await client.put(
                "/admin/api/v1/ai-config/scene-defaults",
                headers={"Authorization": f"Bearer {token}"},
                json=[{"scene": "scoring", "model_id": model_id, "config": {}}],
            )
            assert scene_defaults_response.status_code == 422, scene_defaults_response.text


async def test_admin_can_configure_tenant_openrouter_key_with_masked_response() -> None:
    slug = f"admin-or-{uuid4().hex[:8]}"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/credits":
            return httpx.Response(200, json={"data": {"total_credits": 20, "total_usage": 2.5}})
        if request.url.path == "/api/v1/key":
            return httpx.Response(200, json={"data": {"limit": 20, "limit_remaining": 17.5}})
        return httpx.Response(404)

    install_openrouter_transport(httpx.MockTransport(handler))
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)
            tenant_response = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "OpenRouter Tenant",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "管理员",
                    "contact_phone": "13800000000",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "管理员",
                    "admin_password": "temporary-password",
                },
            )
            assert tenant_response.status_code == 200, tenant_response.text
            tenant_id = tenant_response.json()["data"]["id"]

            put_response = await client.put(
                f"/admin/api/v1/tenants/{tenant_id}/ai-provider/openrouter",
                headers={"Authorization": f"Bearer {token}"},
                json={"api_key": "sk-or-v1-admin-secret-token"},
            )
            assert put_response.status_code == 200, put_response.text
            payload = put_response.json()["data"]
            assert payload["secret_masked"] != "sk-or-v1-admin-secret-token"
            assert payload["balance"]["status"] == "available"
            assert payload["balance"]["source"] == "credits"

            get_response = await client.get(
                f"/admin/api/v1/tenants/{tenant_id}/ai-provider/openrouter",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert get_response.status_code == 200, get_response.text
            assert get_response.json()["data"]["secret_masked"] == payload["secret_masked"]
