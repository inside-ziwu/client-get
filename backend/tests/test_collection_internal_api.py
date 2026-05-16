from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.ids import new_uuid
from app.main import create_app
from app.security.jwt import create_access_token


def service_token() -> str:
    return create_access_token(
        {
            "sub": "collection-sh-01",
            "kind": "service",
            "service_name": "collection-service",
            "aud": "internal:collection",
            "scopes": ["collection:claim", "collection:write"],
        }
    )


async def prepare_collection_task(slug: str) -> str:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        task_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES (:id, :name, :slug, 'PCB', 'active', '{}'::jsonb, false)
                """
            ),
            {"id": tenant_id, "name": slug, "slug": slug},
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES (:id, :tenant_id, :email, 'hash', :name, 'active', false)
                """
            ),
            {"id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com", "name": slug},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status, subscription_status, created_by)
                VALUES
                  (:id, :tenant_id, 'multilayer pcb', 'multilayer pcb',
                   'active', 'running', :created_by)
                """
            ),
            {"id": keyword_id, "tenant_id": tenant_id, "created_by": user_id},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_tasks
                  (id, keyword, keyword_normalized, countries, countries_hash, source_types, status, priority, scheduled_at)
                VALUES
                  (:id, 'multilayer pcb', 'multilayer pcb', '["DE"]'::jsonb, 'hash-de', '["waimao_tong"]'::jsonb, 'pending', 999999, now() - interval '30 days')
                """
            ),
            {"id": task_id},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                VALUES (:id, :task_id, :keyword_id, :tenant_id)
                """
            ),
            {
                "id": str(new_uuid()),
                "task_id": task_id,
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
            },
        )
        await conn.execute(
            text(
                """
                UPDATE collection_tasks
                SET status = 'cancelled',
                    lease_id = NULL,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    scheduled_at = now() + interval '10 days',
                    updated_at = now()
                WHERE id <> :task_id
                  AND status IN ('pending', 'running')
                """
            ),
            {"task_id": task_id},
        )
    await engine.dispose()
    return task_id


async def prepare_collection_task_with_tenant_admin(slug: str) -> tuple[str, str, str]:
    task_id = await prepare_collection_task(slug)
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    """
                    SELECT u.id AS user_id, u.tenant_id
                    FROM users u
                    JOIN tenants t ON t.id = u.tenant_id
                    WHERE t.slug = :slug
                    """
                ),
                {"slug": slug},
            )
        ).mappings().one()
        await conn.execute(
            text(
                """
                INSERT INTO user_roles (id, tenant_id, user_id, role)
                VALUES (:id, :tenant_id, :user_id, 'admin')
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": row["tenant_id"],
                "user_id": row["user_id"],
            },
        )
    await engine.dispose()
    return task_id, str(row["tenant_id"]), str(row["user_id"])


async def test_collection_claim_heartbeat_and_submit_result() -> None:
    slug = f"collection-{uuid4().hex[:8]}"
    await prepare_collection_task(slug)
    token = service_token()
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            claim_response = await client.post(
                "/internal/api/v1/collection/tasks/claim",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Service-Name": "collection-service",
                },
                json={"service_instance": "collection-sh-01", "limit": 1, "lease_seconds": 300},
            )
            assert claim_response.status_code == 200, claim_response.text
            claim_data = claim_response.json()["data"]
            assert len(claim_data["tasks"]) == 1
            task_id = claim_data["tasks"][0]["id"]
            lease_id = claim_data["lease_id"]

            heartbeat_response = await client.post(
                f"/internal/api/v1/collection/tasks/{task_id}/heartbeat",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Service-Name": "collection-service",
                },
                json={"lease_id": lease_id, "lease_seconds": 300},
            )
            assert heartbeat_response.status_code == 200, heartbeat_response.text

            company_source_id = f"src-{uuid4().hex[:8]}"
            submit_payload = {
                "lease_id": lease_id,
                "companies": [
                    {
                        # new-style: routes to waimaotong_raw_companies
                        "target_table": "waimaotong_raw_companies",
                        "source_id": company_source_id,
                        "collection_type": "direct_search",
                        "name": "ABC GmbH",
                        "country_iso3": "DEU",
                        "website": "https://abc.de",
                        "industry": "PCB",
                        "raw_payload": {"is_precise_customer": False},
                    }
                ],
                "contacts": [],
                "competitors": [],
            }

            submit_response = await client.post(
                f"/internal/api/v1/collection/tasks/{task_id}/submit-result",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Service-Name": "collection-service",
                    "X-Request-Id": f"req-{uuid4().hex}",
                },
                json=submit_payload,
            )
            assert submit_response.status_code == 200, submit_response.text
            assert submit_response.json()["data"]["summary"]["companies_count"] == 1


async def test_collection_submit_result_does_not_filter_blacklisted_companies() -> None:
    """黑名单是租户查询层的过滤，采集链路应无条件写入 waimaotong_raw_companies，不感知黑名单。"""
    slug = f"collection-blacklist-{uuid4().hex[:8]}"
    await prepare_collection_task(slug)
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)

    # 在 company_blacklist 中加入 domain 级黑名单
    async with engine.begin() as conn:
        tenant_row = (
            await conn.execute(text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": slug})
        ).mappings().one()
        await conn.execute(
            text(
                """
                INSERT INTO company_blacklist
                  (id, tenant_id, match_domain, match_name_pattern, reason)
                VALUES
                  (:id, :tenant_id, 'blocked.example.com', 'Blocked GmbH', 'test blacklist')
                """
            ),
            {"id": str(new_uuid()), "tenant_id": tenant_row["id"]},
        )
    await engine.dispose()

    source_id = f"src-bl-{uuid4().hex[:8]}"
    token = service_token()
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            claim_response = await client.post(
                "/internal/api/v1/collection/tasks/claim",
                headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                json={"service_instance": "collection-sh-02", "limit": 1, "lease_seconds": 300},
            )
            assert claim_response.status_code == 200, claim_response.text
            claim_data = claim_response.json()["data"]
            claimed_task_id = claim_data["tasks"][0]["id"]
            lease_id = claim_data["lease_id"]

            submit_response = await client.post(
                f"/internal/api/v1/collection/tasks/{claimed_task_id}/submit-result",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Service-Name": "collection-service",
                    "X-Request-Id": f"req-{uuid4().hex}",
                },
                json={
                    "lease_id": lease_id,
                    "companies": [
                        {
                            # 黑名单公司 —— 采集层不应过滤，必须正常写入 raw 表
                            "target_table": "waimaotong_raw_companies",
                            "source_id": source_id,
                            "collection_type": "direct_search",
                            "name": "Blocked GmbH",
                            "country_iso3": "DEU",
                            "domain": "blocked.example.com",
                            "industry": "PCB",
                            "raw_payload": {},
                        }
                    ],
                    "contacts": [],
                    "competitors": [],
                },
            )
            assert submit_response.status_code == 200, submit_response.text
            # 采集层不过滤，companies_count 应为 1
            assert submit_response.json()["data"]["summary"]["companies_count"] == 1

    # raw 表必须有该行（采集无条件写入）
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.begin() as conn:
        raw_count = (
            await conn.execute(
                text("SELECT count(*) FROM waimaotong_raw_companies WHERE source_id = :sid"),
                {"sid": source_id},
            )
        ).scalar_one()
    await engine.dispose()
    assert raw_count == 1, "黑名单公司应写入 waimaotong_raw_companies（黑名单过滤在查询层，非采集层）"


async def test_collection_mark_failed_requeues_then_fails_after_max_attempts() -> None:
    slug = f"collection-fail-{uuid4().hex[:8]}"
    await prepare_collection_task(slug)
    token = service_token()
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            first_claim = await client.post(
                "/internal/api/v1/collection/tasks/claim",
                headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                json={"service_instance": "collection-sh-fail", "limit": 1, "lease_seconds": 300},
            )
            assert first_claim.status_code == 200, first_claim.text
            claim_data = first_claim.json()["data"]
            task_id = claim_data["tasks"][0]["id"]
            lease_id = claim_data["lease_id"]

            first_failed = await client.post(
                f"/internal/api/v1/collection/tasks/{task_id}/mark-failed",
                headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                json={"lease_id": lease_id, "error_code": "PROVIDER_ERROR", "error_message": "boom", "retryable": True},
            )
            assert first_failed.status_code == 200, first_failed.text
            assert first_failed.json()["data"]["status"] == "pending"

            engine = create_async_engine(get_settings().database_url, future=True)
            async with engine.begin() as conn:
                row = (
                    await conn.execute(
                        text("SELECT status, attempt_count, error_message FROM collection_tasks WHERE id = :task_id"),
                        {"task_id": task_id},
                    )
                ).mappings().one()
            await engine.dispose()
            assert row["status"] == "pending"
            assert row["attempt_count"] == 1
            assert "PROVIDER_ERROR" in row["error_message"]

            for _ in range(2):
                claim = await client.post(
                    "/internal/api/v1/collection/tasks/claim",
                    headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                    json={"service_instance": "collection-sh-fail", "limit": 1, "lease_seconds": 300},
                )
                assert claim.status_code == 200, claim.text
                lease_id = claim.json()["data"]["lease_id"]
                failed = await client.post(
                    f"/internal/api/v1/collection/tasks/{task_id}/mark-failed",
                    headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                    json={"lease_id": lease_id, "error_message": "still failing", "retryable": True},
                )
                assert failed.status_code == 200, failed.text

            engine = create_async_engine(get_settings().database_url, future=True)
            async with engine.begin() as conn:
                final_row = (
                    await conn.execute(
                        text("SELECT status, attempt_count, completed_at FROM collection_tasks WHERE id = :task_id"),
                        {"task_id": task_id},
                    )
                ).mappings().one()
            await engine.dispose()
            assert final_row["status"] == "failed"
            assert final_row["attempt_count"] == 3
            assert final_row["completed_at"] is not None


async def test_collection_mark_failed_credential_expired_final_failure_does_not_notify_tenant_admin() -> None:
    slug = f"collection-cred-expired-{uuid4().hex[:8]}"
    _, tenant_id, user_id = await prepare_collection_task_with_tenant_admin(slug)
    token = service_token()
    app = create_app()

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            claim_response = await client.post(
                "/internal/api/v1/collection/tasks/claim",
                headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                json={"service_instance": "collection-sh-cred", "limit": 1, "lease_seconds": 300},
            )
            assert claim_response.status_code == 200, claim_response.text
            claim_data = claim_response.json()["data"]
            task_id = claim_data["tasks"][0]["id"]
            lease_id = claim_data["lease_id"]

            failed_response = await client.post(
                f"/internal/api/v1/collection/tasks/{task_id}/mark-failed",
                headers={"Authorization": f"Bearer {token}", "X-Service-Name": "collection-service"},
                json={
                    "lease_id": lease_id,
                    "error_code": "CREDENTIAL_EXPIRED",
                    "error_message": "腾道 Cookie 会话已过期，请重新登录并更新凭证",
                    "retryable": False,
                },
            )
            assert failed_response.status_code == 200, failed_response.text
            assert failed_response.json()["data"]["status"] == "failed"

            tenant_token = create_access_token(
                {
                    "sub": user_id,
                    "kind": "tenant",
                    "tid": tenant_id,
                    "slug": slug,
                    "roles": ["admin"],
                }
            )
            notifications_response = await client.get(
                f"/t/{slug}/api/v1/notifications",
                headers={"Authorization": f"Bearer {tenant_token}"},
            )
            assert notifications_response.status_code == 200, notifications_response.text
            notifications_text = notifications_response.text
            assert "CREDENTIAL_EXPIRED" not in notifications_text
            assert "Cookie 会话已过期" not in notifications_text

    engine = create_async_engine(get_settings().database_url, future=True)
    async with engine.begin() as conn:
        task_row = (
            await conn.execute(
                text("SELECT status, error_message FROM collection_tasks WHERE id = :task_id"),
                {"task_id": task_id},
            )
        ).mappings().one()
        notification_count = (
            await conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM notifications
                    WHERE tenant_id = :tenant_id
                      AND user_id = :user_id
                      AND entity_type = 'collection_task'
                      AND entity_id = :task_id
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id, "task_id": task_id},
            )
        ).scalar_one()
    await engine.dispose()

    assert task_row["status"] == "failed"
    assert "[CREDENTIAL_EXPIRED]" in task_row["error_message"]
    assert notification_count == 0
