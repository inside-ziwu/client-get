from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from tests.test_auth_integration import login_admin


async def _setup_tenant(client: AsyncClient, admin_token: str) -> tuple[str, str, dict]:
    """创建租户并登录，返回 (slug, tenant_token, headers)"""
    slug = f"grp-{uuid4().hex[:8]}"
    res = await client.post(
        "/admin/api/v1/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "群组测试租户",
            "slug": slug,
            "industry": "PCB",
            "contact_name": "测试",
            "contact_phone": "13700000000",
            "admin_email": f"{slug}@example.com",
            "admin_name": "测试",
            "admin_password": "test-password",
        },
    )
    assert res.status_code == 200, res.text

    login = await client.post(
        f"/t/{slug}/api/v1/auth/login",
        json={"email": f"{slug}@example.com", "password": "test-password"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    return slug, token, {"Authorization": f"Bearer {token}"}


async def test_companies_without_group_id_returns_all() -> None:
    """不传 group_id 时行为不变，返回全量公司（回归测试）"""
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            slug, _, headers = await _setup_tenant(client, admin_token)

            res = await client.get(f"/t/{slug}/api/v1/companies", headers=headers)
            assert res.status_code == 200, res.text
            body = res.json()
            assert "data" in body
            assert "pagination" in body


async def test_companies_with_group_id_filters_correctly() -> None:
    """创建群组 → 添加公司 → group_id 过滤只返回群组内公司"""
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            slug, _, headers = await _setup_tenant(client, admin_token)

            group_res = await client.post(
                f"/t/{slug}/api/v1/groups",
                headers=headers,
                json={"name": "测试群组"},
            )
            assert group_res.status_code == 200, group_res.text
            group_id = group_res.json()["data"]["id"]

            all_res = await client.get(f"/t/{slug}/api/v1/companies", headers=headers)
            assert all_res.status_code == 200, all_res.text
            all_companies = all_res.json()["data"]
            all_total = all_res.json()["pagination"]["total"]

            if len(all_companies) >= 2:
                tc_ids = [all_companies[0]["tc_id"], all_companies[1]["tc_id"]]
                add_res = await client.post(
                    f"/t/{slug}/api/v1/groups/{group_id}/members/batch-add",
                    headers=headers,
                    json={"tenant_company_ids": tc_ids},
                )
                assert add_res.status_code == 200, add_res.text

                filtered_res = await client.get(
                    f"/t/{slug}/api/v1/companies",
                    headers=headers,
                    params={"group_id": group_id},
                )
                assert filtered_res.status_code == 200, filtered_res.text
                filtered_data = filtered_res.json()["data"]
                filtered_total = filtered_res.json()["pagination"]["total"]
                assert filtered_total == 2
                assert len(filtered_data) == 2
                filtered_tc_ids = {c["tc_id"] for c in filtered_data}
                assert filtered_tc_ids == set(tc_ids)

            empty_res = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers=headers,
                params={"group_id": group_id} if len(all_companies) < 2 else {"group_id": str(uuid4())},
            )
            assert empty_res.status_code == 200, empty_res.text


async def test_empty_group_returns_zero() -> None:
    """空群组 → 返回空列表和 total=0"""
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            slug, _, headers = await _setup_tenant(client, admin_token)

            group_res = await client.post(
                f"/t/{slug}/api/v1/groups",
                headers=headers,
                json={"name": "空群组"},
            )
            assert group_res.status_code == 200, group_res.text
            group_id = group_res.json()["data"]["id"]

            res = await client.get(
                f"/t/{slug}/api/v1/companies",
                headers=headers,
                params={"group_id": group_id},
            )
            assert res.status_code == 200, res.text
            assert res.json()["pagination"]["total"] == 0
            assert res.json()["data"] == []
