from uuid import uuid4

from sqlalchemy import text

from app.core.ids import new_uuid
from app.workers.collection_scheduler import CollectionSchedulerWorker
from tests.helpers import make_engine


async def test_collection_scheduler_worker_recovers_expired_task() -> None:
    slug = f"sched-worker-{uuid4().hex[:8]}"
    engine = make_engine()
    task_id = str(new_uuid())
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
                """
            ),
            {"tenant_id": tenant_id, "slug": slug},
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES (:user_id, :tenant_id, :email, 'hash', :slug, 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com", "slug": slug},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status, subscription_status, created_by)
                VALUES
                  (:keyword_id, :tenant_id, 'pcb', 'pcb', 'active', 'running', :user_id)
                """
            ),
            {"keyword_id": keyword_id, "tenant_id": tenant_id, "user_id": user_id},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_tasks
                  (id, keyword, keyword_normalized, countries, countries_hash, source_types, status, priority,
                   lease_id, lease_owner, lease_expires_at, attempt_count, max_attempts, scheduled_at)
                VALUES
                  (:task_id, 'pcb', 'pcb', '["DE"]'::jsonb, 'recover-hash', '["waimao_tong"]'::jsonb, 'running', 10,
                   :lease_id, 'collection-worker-1', now() - interval '10 minutes', 1, 3, now())
                """
            ),
            {"task_id": task_id, "lease_id": str(new_uuid())},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                VALUES (:id, :task_id, :keyword_id, :tenant_id)
                """
            ),
            {"id": str(new_uuid()), "task_id": task_id, "keyword_id": keyword_id, "tenant_id": tenant_id},
        )

    result = await CollectionSchedulerWorker().run_once(engine)

    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT status, lease_id, lease_expires_at FROM collection_tasks WHERE id = :task_id"),
                {"task_id": task_id},
            )
        ).mappings().one()
    await engine.dispose()

    assert result["recovery"]["requeued_count"] >= 1
    assert row["status"] in {"pending", "running"}
    if row["status"] == "pending":
        assert row["lease_id"] is None
        assert row["lease_expires_at"] is None


async def test_collection_scheduler_worker_once_without_tasks() -> None:
    engine = make_engine()
    result = await CollectionSchedulerWorker().run_once(engine)
    await engine.dispose()

    assert "recovery" in result
    assert "scheduled_count" in result
    assert isinstance(result["items"], list)
