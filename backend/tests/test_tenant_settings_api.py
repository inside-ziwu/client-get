from uuid import uuid4

import httpx
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.helpers import install_openrouter_transport
from tests.test_auth_integration import login_admin


async def test_tenant_onboarding_settings_flow() -> None:
    slug = f"settings-{uuid4().hex[:8]}"
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            create_response = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "设置租户",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "王五",
                    "contact_phone": "13700000000",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "王五",
                    "admin_password": "temporary-password",
                },
            )
            assert create_response.status_code == 200, create_response.text

            tenant_login = await client.post(
                f"/t/{slug}/api/v1/auth/login",
                json={"email": f"{slug}@example.com", "password": "temporary-password"},
            )
            assert tenant_login.status_code == 200, tenant_login.text
            tenant_token = tenant_login.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {tenant_token}"}

            keywords_before = await client.get(f"/t/{slug}/api/v1/keywords", headers=headers)
            assert keywords_before.status_code == 200, keywords_before.text

            create_keyword = await client.post(
                f"/t/{slug}/api/v1/keywords",
                headers=headers,
                json={"keyword": "multilayer pcb", "countries": ["DE", "US"], "source_types": ["waimao_tong"]},
            )
            assert create_keyword.status_code == 200, create_keyword.text

            scoring_templates = await client.get(f"/t/{slug}/api/v1/scoring-templates", headers=headers)
            assert scoring_templates.status_code == 200, scoring_templates.text
            template_id = scoring_templates.json()["data"][0]["id"]

            update_scoring = await client.put(
                f"/t/{slug}/api/v1/scoring-templates/{template_id}",
                headers=headers,
                json={"name": "更新后模板"},
            )
            assert update_scoring.status_code == 200, update_scoring.text

            contact_rules = await client.get(f"/t/{slug}/api/v1/contact-rules", headers=headers)
            assert contact_rules.status_code == 404, contact_rules.text

            complete_onboarding = await client.post(f"/t/{slug}/api/v1/onboarding/complete", headers=headers)
            assert complete_onboarding.status_code == 200, complete_onboarding.text


async def test_tenant_admin_can_manage_openrouter_settings() -> None:
    slug = f"tenant-or-{uuid4().hex[:8]}"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/credits":
            return httpx.Response(403, json={"error": {"message": "management key required"}})
        if request.url.path == "/api/v1/key":
            return httpx.Response(200, json={"data": {"limit": 8, "limit_remaining": 3.25}})
        return httpx.Response(404)

    install_openrouter_transport(httpx.MockTransport(handler))
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            create_response = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "设置租户",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "王五",
                    "contact_phone": "13700000000",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "王五",
                    "admin_password": "temporary-password",
                },
            )
            assert create_response.status_code == 200, create_response.text

            tenant_login = await client.post(
                f"/t/{slug}/api/v1/auth/login",
                json={"email": f"{slug}@example.com", "password": "temporary-password"},
            )
            assert tenant_login.status_code == 200, tenant_login.text
            tenant_token = tenant_login.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {tenant_token}"}

            put_response = await client.put(
                f"/t/{slug}/api/v1/settings/ai-provider/openrouter",
                headers=headers,
                json={"api_key": "sk-or-v1-tenant-secret-token"},
            )
            assert put_response.status_code == 200, put_response.text
            assert put_response.json()["data"]["balance"]["status"] == "available"
            assert put_response.json()["data"]["balance"]["source"] == "key"

            refresh_response = await client.post(
                f"/t/{slug}/api/v1/settings/ai-provider/openrouter/balance/refresh",
                headers=headers,
            )
            assert refresh_response.status_code == 200, refresh_response.text

            delete_response = await client.delete(
                f"/t/{slug}/api/v1/settings/ai-provider/openrouter",
                headers=headers,
            )
            assert delete_response.status_code == 200, delete_response.text
