from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.helpers import create_tenant_via_admin
from tests.test_auth_integration import login_admin


async def test_sync_platform_email_template_creates_copies_for_matching_tenants() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)

            template_resp = await client.post(
                "/admin/api/v1/email-templates",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "industry": "PCB",
                    "name": f"同步测试模板-{uuid4().hex[:8]}",
                    "category": "outreach",
                    "subject": "你好 {{ contact_name }}",
                    "body_html": "<p>测试</p>",
                    "variables": [{"name": "contact_name", "label": "联系人"}],
                    "is_active": True,
                },
            )
            assert template_resp.status_code == 200, template_resp.text
            template_id = template_resp.json()["data"]["id"]

            slug = f"sync-{uuid4().hex[:8]}"
            await create_tenant_via_admin(client, token, slug=slug)

            sync_resp = await client.post(
                f"/admin/api/v1/email-templates/{template_id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert sync_resp.status_code == 200, sync_resp.text
            result = sync_resp.json()["data"]
            assert result["template_id"] == template_id
            assert result["industry"] == "PCB"
            assert result["total_tenants"] >= 1
            assert len(result["created"]) >= 1
            assert isinstance(result["skipped"], list)


async def test_sync_is_idempotent() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)

            template_resp = await client.post(
                "/admin/api/v1/email-templates",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "industry": "PCB",
                    "name": f"幂等测试-{uuid4().hex[:8]}",
                    "category": "outreach",
                    "subject": "主题",
                    "body_html": "<p>内容</p>",
                    "variables": [],
                    "is_active": True,
                },
            )
            assert template_resp.status_code == 200, template_resp.text
            template_id = template_resp.json()["data"]["id"]

            slug = f"idem-{uuid4().hex[:8]}"
            await create_tenant_via_admin(client, token, slug=slug)

            first_resp = await client.post(
                f"/admin/api/v1/email-templates/{template_id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert first_resp.status_code == 200
            first_result = first_resp.json()["data"]

            second_resp = await client.post(
                f"/admin/api/v1/email-templates/{template_id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert second_resp.status_code == 200
            second_result = second_resp.json()["data"]
            assert len(second_result["created"]) == 0
            assert len(second_result["skipped"]) >= len(first_result["created"])


async def test_sync_inactive_template_returns_400() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)

            template_resp = await client.post(
                "/admin/api/v1/email-templates",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "industry": "PCB",
                    "name": f"停用模板-{uuid4().hex[:8]}",
                    "category": "outreach",
                    "subject": "主题",
                    "body_html": "<p>内容</p>",
                    "variables": [],
                    "is_active": False,
                },
            )
            assert template_resp.status_code == 200, template_resp.text
            template_id = template_resp.json()["data"]["id"]

            sync_resp = await client.post(
                f"/admin/api/v1/email-templates/{template_id}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert sync_resp.status_code == 400


async def test_sync_nonexistent_template_returns_404() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)

            sync_resp = await client.post(
                f"/admin/api/v1/email-templates/{uuid4()}/sync",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert sync_resp.status_code == 404
