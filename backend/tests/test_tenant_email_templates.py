from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.helpers import create_tenant_via_admin, login_tenant
from tests.test_auth_integration import login_admin


async def _setup(client: AsyncClient):
    """创建租户并登录，返回 (slug, tenant_token, admin_token)"""
    token = await login_admin(client)
    slug = f"tpl-{uuid4().hex[:8]}"
    await create_tenant_via_admin(client, token, slug=slug)
    tenant_token = await login_tenant(client, slug=slug)
    return slug, tenant_token, token


async def test_create_template_with_body_design() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)
            design = {"components": [{"type": "text", "content": "hello"}]}

            resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "设计模板",
                    "category": "cold_outreach",
                    "subject": "测试主题",
                    "body_html": "<p>内容</p>",
                    "body_design": design,
                    "variables": [],
                },
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()["data"]
            assert data["body_design"] == design


async def test_create_template_without_body_design() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)

            resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "纯HTML模板",
                    "category": "follow_up",
                    "subject": "主题",
                    "body_html": "<p>纯HTML</p>",
                    "variables": [],
                },
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()["data"]
            assert "body_design" in data
            assert data["body_design"] is None


async def test_update_template_body_design() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)

            create_resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "待更新模板",
                    "category": "cold_outreach",
                    "subject": "主题",
                    "body_html": "<p>内容</p>",
                    "variables": [],
                },
            )
            assert create_resp.status_code == 200, create_resp.text
            template_id = create_resp.json()["data"]["id"]

            new_design = {"pages": [{"frames": []}]}
            update_resp = await client.put(
                f"/t/{slug}/api/v1/email-templates/{template_id}",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "待更新模板",
                    "category": "cold_outreach",
                    "subject": "主题",
                    "body_html": "<p>更新后</p>",
                    "body_design": new_design,
                    "variables": [],
                },
            )
            assert update_resp.status_code == 200, update_resp.text

            get_resp = await client.get(
                f"/t/{slug}/api/v1/email-templates/{template_id}",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert get_resp.status_code == 200, get_resp.text
            assert get_resp.json()["data"]["body_design"] == new_design


async def test_update_template_clear_body_design() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)
            design = {"components": []}

            create_resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "含设计模板",
                    "category": "promotion",
                    "subject": "主题",
                    "body_html": "<p>内容</p>",
                    "body_design": design,
                    "variables": [],
                },
            )
            assert create_resp.status_code == 200, create_resp.text
            template_id = create_resp.json()["data"]["id"]

            update_resp = await client.put(
                f"/t/{slug}/api/v1/email-templates/{template_id}",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "含设计模板",
                    "category": "promotion",
                    "subject": "主题",
                    "body_html": "<p>切回HTML编辑</p>",
                    "body_design": None,
                    "variables": [],
                },
            )
            assert update_resp.status_code == 200, update_resp.text

            get_resp = await client.get(
                f"/t/{slug}/api/v1/email-templates/{template_id}",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert get_resp.status_code == 200, get_resp.text
            assert get_resp.json()["data"]["body_design"] is None


async def test_sanitize_preserves_email_tags() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)

            html_with_email_tags = (
                '<table width="600"><tr><td>'
                '<img src="https://example.com/logo.png" alt="Logo">'
                '<div style="color:red"><span>styled</span></div>'
                "</td></tr></table>"
            )
            resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "邮件标签模板",
                    "category": "cold_outreach",
                    "subject": "主题",
                    "body_html": html_with_email_tags,
                    "variables": [],
                },
            )
            assert resp.status_code == 200, resp.text
            saved_html = resp.json()["data"]["body_html"]
            assert "<table" in saved_html
            assert "<img" in saved_html
            assert "<div" in saved_html
            assert "<span" in saved_html


async def test_sanitize_strips_dangerous_html() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)

            dangerous_html = (
                '<p>正常内容</p>'
                '<script>alert("xss")</script>'
                '<iframe src="evil.com"></iframe>'
                '<p onclick="hack()">点击</p>'
            )
            resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "危险标签模板",
                    "category": "cold_outreach",
                    "subject": "主题",
                    "body_html": dangerous_html,
                    "body_design": {"some": "design"},
                    "variables": [],
                },
            )
            assert resp.status_code == 200, resp.text
            saved_html = resp.json()["data"]["body_html"]
            assert "<script" not in saved_html
            assert "<iframe" not in saved_html
            assert "onclick" not in saved_html


async def test_clone_template_preserves_body_design() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)
            design = {"pages": [{"id": "page1"}]}

            create_resp = await client.post(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "name": "克隆源模板",
                    "category": "cold_outreach",
                    "subject": "主题",
                    "body_html": "<p>内容</p>",
                    "body_design": design,
                    "variables": [],
                },
            )
            assert create_resp.status_code == 200, create_resp.text
            template_id = create_resp.json()["data"]["id"]

            clone_resp = await client.post(
                f"/t/{slug}/api/v1/email-templates/{template_id}/clone",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert clone_resp.status_code == 200, clone_resp.text
            cloned = clone_resp.json()["data"]
            assert cloned["body_design"] == design
            assert cloned["id"] != template_id


# --- U4: 平台模板浏览 API ---


async def _create_platform_template(client: AsyncClient, admin_token: str, *, industry: str = "PCB", is_active: bool = True, name: str | None = None) -> dict:
    """Admin 创建平台模板，返回模板数据"""
    resp = await client.post(
        "/admin/api/v1/email-templates",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "industry": industry,
            "name": name or f"平台模板-{uuid4().hex[:8]}",
            "category": "cold_outreach",
            "subject": "你好 {{contact_name}}",
            "body_html": "<p>平台模板内容</p>",
            "body_design": {"pages": [{"id": "p1"}]},
            "variables": [{"name": "contact_name", "label": "联系人"}],
            "is_active": is_active,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def test_list_platform_templates_returns_matching_industry() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, admin_token = await _setup(client)
            await _create_platform_template(client, admin_token, industry="PCB")

            resp = await client.get(
                f"/t/{slug}/api/v1/platform-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code == 200, resp.text
            items = resp.json()["data"]
            assert len(items) >= 1
            assert all("name" in t for t in items)


async def test_list_platform_templates_empty_when_no_match() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, admin_token = await _setup(client)
            await _create_platform_template(client, admin_token, industry="LED")

            resp = await client.get(
                f"/t/{slug}/api/v1/platform-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code == 200, resp.text
            items = resp.json()["data"]
            led_names = [t["name"] for t in items if "LED" in t.get("name", "")]
            assert len(led_names) == 0


async def test_list_platform_templates_excludes_inactive() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, admin_token = await _setup(client)
            inactive = await _create_platform_template(client, admin_token, industry="PCB", is_active=False, name=f"停用模板-{uuid4().hex[:8]}")

            resp = await client.get(
                f"/t/{slug}/api/v1/platform-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code == 200, resp.text
            items = resp.json()["data"]
            item_ids = [t["id"] for t in items]
            assert inactive["id"] not in item_ids


# --- U5: 平台模板复制 API ---


async def test_copy_platform_template_success() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, admin_token = await _setup(client)
            platform_tpl = await _create_platform_template(client, admin_token, industry="PCB")

            resp = await client.post(
                f"/t/{slug}/api/v1/platform-templates/{platform_tpl['id']}/copy",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()["data"]
            assert data["source_type"] == "platform_copy"
            assert data["platform_template_id"] == platform_tpl["id"]
            assert data["body_design"] == platform_tpl.get("body_design")
            assert data["name"] == platform_tpl["name"]


async def test_copy_platform_template_industry_mismatch() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, admin_token = await _setup(client)
            led_tpl = await _create_platform_template(client, admin_token, industry="LED")

            resp = await client.post(
                f"/t/{slug}/api/v1/platform-templates/{led_tpl['id']}/copy",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code in (400, 403, 404), resp.text


async def test_copy_platform_template_inactive_returns_error() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, admin_token = await _setup(client)
            inactive_tpl = await _create_platform_template(client, admin_token, industry="PCB", is_active=False)

            resp = await client.post(
                f"/t/{slug}/api/v1/platform-templates/{inactive_tpl['id']}/copy",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code in (400, 404), resp.text


async def test_copy_platform_template_not_found() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            slug, tenant_token, _ = await _setup(client)

            resp = await client.post(
                f"/t/{slug}/api/v1/platform-templates/{uuid4()}/copy",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code == 404, resp.text


# --- U6: 租户创建时复制包含 body_design ---


async def test_copy_platform_templates_on_tenant_creation_includes_body_design() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            await _create_platform_template(client, admin_token, industry="PCB", name=f"创建时复制-{uuid4().hex[:8]}")

            slug = f"new-{uuid4().hex[:8]}"
            await create_tenant_via_admin(client, admin_token, slug=slug)
            tenant_token = await login_tenant(client, slug=slug)

            resp = await client.get(
                f"/t/{slug}/api/v1/email-templates",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert resp.status_code == 200, resp.text
            items = resp.json()["data"]
            platform_copies = [t for t in items if t["source_type"] == "platform_copy"]
            assert len(platform_copies) >= 1

            first_id = platform_copies[0]["id"]
            detail_resp = await client.get(
                f"/t/{slug}/api/v1/email-templates/{first_id}",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert detail_resp.status_code == 200, detail_resp.text
            detail = detail_resp.json()["data"]
            assert "body_design" in detail
