from datetime import datetime, timedelta, timezone
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text

from app.core.config import get_settings
from app.main import create_app
from tests.helpers import make_engine


async def login_admin(client: AsyncClient) -> str:
    response = await client.post(
        "/admin/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "change-me-now"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


async def test_platform_admin_login_and_me() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            token = await login_admin(client)
            me_response = await client.get(
                "/admin/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["data"]["roles"] == ["platform_admin"]


async def test_admin_tenant_list_includes_created_and_updated_times() -> None:
    slug = f"list-times-{uuid4().hex[:8]}"
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            create_response = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "列表时间字段",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "张三",
                    "contact_phone": "13800000000",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "张三",
                    "admin_password": "temporary-password",
                },
            )
            assert create_response.status_code == 200, create_response.text

            list_response = await client.get(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    assert list_response.status_code == 200, list_response.text
    item = next(row for row in list_response.json()["data"] if row["name"] == "列表时间字段")
    assert item["created_at"]
    assert item["updated_at"]


async def test_create_tenant_then_login_change_password_and_me() -> None:
    slug = f"tenant-{uuid4().hex[:8]}"
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            create_response = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "测试租户",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "张三",
                    "contact_phone": "13800000000",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "张三",
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

            me_response = await client.get(
                f"/t/{slug}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert me_response.status_code == 200, me_response.text
            assert me_response.json()["data"]["must_change_pwd"] is True

            change_password = await client.post(
                f"/t/{slug}/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {tenant_token}"},
                json={
                    "current_password": "temporary-password",
                    "new_password": "temporary-password-2",
                },
            )
            assert change_password.status_code == 200, change_password.text

            relogin_response = await client.post(
                f"/t/{slug}/api/v1/auth/login",
                json={"email": f"{slug}@example.com", "password": "temporary-password-2"},
            )

    assert relogin_response.status_code == 200, relogin_response.text


async def test_tenant_slug_mismatch_and_expired_token_are_rejected() -> None:
    slug = f"mismatch-{uuid4().hex[:8]}"
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            tenant = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "测试租户",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "张三",
                    "contact_phone": "13800000000",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "张三",
                    "admin_password": "temporary-password",
                },
            )
            assert tenant.status_code == 200, tenant.text
            tenant_id = tenant.json()["data"]["id"]

            tenant_login = await client.post(
                f"/t/{slug}/api/v1/auth/login",
                json={"email": f"{slug}@example.com", "password": "temporary-password"},
            )
            assert tenant_login.status_code == 200, tenant_login.text
            tenant_token = tenant_login.json()["data"]["access_token"]

            mismatch_response = await client.get(
                f"/t/other-{slug}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert mismatch_response.status_code == 403, mismatch_response.text

            engine = make_engine()
            async with engine.begin() as conn:
                tenant_user_id = (
                    await conn.execute(
                        text("SELECT id FROM users WHERE tenant_id = :tenant_id ORDER BY created_at ASC LIMIT 1"),
                        {"tenant_id": tenant_id},
                    )
                ).scalar_one()
            await engine.dispose()

            settings = get_settings()
            expired_token = jwt.encode(
                {
                    "sub": str(tenant_user_id),
                    "kind": "tenant",
                    "tid": tenant_id,
                    "slug": slug,
                    "roles": ["admin"],
                    "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
                    "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
                },
                settings.jwt_secret,
                algorithm=settings.jwt_algorithm,
            )
            expired_response = await client.get(
                f"/t/{slug}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
            assert expired_response.status_code == 401, expired_response.text


async def test_failed_login_lockout_after_five_attempts() -> None:
    slug = f"lock-{uuid4().hex[:8]}"
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            admin_token = await login_admin(client)
            create_response = await client.post(
                "/admin/api/v1/tenants",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "name": "测试租户",
                    "slug": slug,
                    "industry": "PCB",
                    "contact_name": "李四",
                    "contact_phone": "13800000001",
                    "admin_email": f"{slug}@example.com",
                    "admin_name": "李四",
                    "admin_password": "temporary-password",
                },
            )
            assert create_response.status_code == 200, create_response.text

            for _ in range(5):
                bad_login = await client.post(
                    f"/t/{slug}/api/v1/auth/login",
                    json={"email": f"{slug}@example.com", "password": "wrong-password"},
                )
                assert bad_login.status_code == 401, bad_login.text

            locked_response = await client.post(
                f"/t/{slug}/api/v1/auth/login",
                json={"email": f"{slug}@example.com", "password": "temporary-password"},
            )
            assert locked_response.status_code == 423, locked_response.text
