from uuid import uuid4

import httpx
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.helpers import create_tenant_via_admin, install_openrouter_transport, login_tenant, make_service_token
from tests.test_auth_integration import login_admin


async def test_intelligence_publish_summary_and_unpublished_access() -> None:
    paid_slug = f"intel-paid-{uuid4().hex[:8]}"
    free_slug = f"intel-free-{uuid4().hex[:8]}"
    tag = f"pcb-{uuid4().hex[:6]}"
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/credits":
            return httpx.Response(200, json={"data": {"total_credits": 10, "total_usage": 1}})
        if request.url.path == "/api/v1/key":
            return httpx.Response(200, json={"data": {"limit": 10, "limit_remaining": 9}})
        return httpx.Response(404)

    install_openrouter_transport(httpx.MockTransport(handler))
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            paid_tenant = await create_tenant_via_admin(client, admin_token, slug=paid_slug)
            await create_tenant_via_admin(client, admin_token, slug=free_slug)

            configure_response = await client.put(
                f"/admin/api/v1/tenants/{paid_tenant['id']}/ai-provider/openrouter",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"api_key": "sk-or-v1-intel-paid-secret"},
            )
            assert configure_response.status_code == 200, configure_response.text

            paid_token = await login_tenant(client, slug=paid_slug)
            free_token = await login_tenant(client, slug=free_slug)
            paid_headers = {"Authorization": f"Bearer {paid_token}"}
            free_headers = {"Authorization": f"Bearer {free_token}"}

            paid_sub = await client.put(
                f"/t/{paid_slug}/api/v1/intelligence/subscriptions",
                headers=paid_headers,
                json={"industry_tags": [tag], "min_relevance": 0.5, "notify_enabled": True},
            )
            assert paid_sub.status_code == 200, paid_sub.text
            free_sub = await client.put(
                f"/t/{free_slug}/api/v1/intelligence/subscriptions",
                headers=free_headers,
                json={"industry_tags": [tag], "min_relevance": 0.5, "notify_enabled": True},
            )
            assert free_sub.status_code == 200, free_sub.text

            intel_token = make_service_token("intelligence-service", ["intelligence:publish"])
            intel_headers = {
                "Authorization": f"Bearer {intel_token}",
                "X-Service-Name": "intelligence-service",
            }

            publish_response = await client.post(
                "/internal/api/v1/intelligence/articles/publish",
                headers=intel_headers,
                json={
                    "title": "PCB market update",
                    "url": "https://example.com/pcb",
                    "content_raw": "PCB market demand is rising rapidly across Europe.",
                    "ai_tags": [tag],
                    "ai_relevance_score": 0.9,
                    "estimated_cost": 1,
                },
            )
            assert publish_response.status_code == 200, publish_response.text
            payload = publish_response.json()["data"]
            article_id = payload["article_id"]
            assert payload["published_tenants"] == 2
            assert payload["tenants_with_summary"] == 1

            paid_articles = await client.get(f"/t/{paid_slug}/api/v1/intelligence/articles", headers=paid_headers)
            assert paid_articles.status_code == 200, paid_articles.text
            paid_item = paid_articles.json()["data"][0]
            assert paid_item["has_summary"] is True
            assert paid_item["content_summary"]

            free_articles = await client.get(f"/t/{free_slug}/api/v1/intelligence/articles", headers=free_headers)
            assert free_articles.status_code == 200, free_articles.text
            free_item = free_articles.json()["data"][0]
            assert free_item["has_summary"] is False
            assert free_item["content_summary"] is None

            unpublished_response = await client.post(
                "/internal/api/v1/intelligence/articles/publish",
                headers=intel_headers,
                json={
                    "title": "Automotive market update",
                    "url": "https://example.com/auto",
                    "content_raw": "Automotive news unrelated to PCB.",
                    "ai_tags": ["automotive"],
                    "ai_relevance_score": 0.9,
                    "estimated_cost": 1,
                },
            )
            assert unpublished_response.status_code == 200, unpublished_response.text
            other_article_id = unpublished_response.json()["data"]["article_id"]

            paid_other = await client.get(f"/t/{paid_slug}/api/v1/intelligence/articles/{other_article_id}", headers=paid_headers)
            assert paid_other.status_code == 404, paid_other.text

            paid_get = await client.get(f"/t/{paid_slug}/api/v1/intelligence/articles/{article_id}", headers=paid_headers)
            assert paid_get.status_code == 200, paid_get.text
