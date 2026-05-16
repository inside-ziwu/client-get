from uuid import uuid4

from sqlalchemy import text

from app.core.ids import new_uuid
from app.services.admin_collection_service import AdminCollectionService
from app.services.collection_scheduler_service import CollectionSchedulerService
from app.services.keyword_service import normalize_keyword
from app.services.tenant_settings_service import TenantSettingsService
from tests.helpers import make_engine


async def test_collection_scheduler_merges_same_keyword_normalized() -> None:
    slug_a = f"sched-a-{uuid4().hex[:8]}"
    slug_b = f"sched-b-{uuid4().hex[:8]}"
    keyword = f"multilayer pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_a = str(new_uuid())
        tenant_b = str(new_uuid())
        user_a = str(new_uuid())
        user_b = str(new_uuid())
        keyword_master_id = str(new_uuid())
        await conn.execute(
            text(
                """
                CREATE TEMP TABLE lixiaoyun_raw_companies (
                  keyword_master_id uuid,
                  source_id text,
                  created_at timestamptz NOT NULL DEFAULT now()
                ) ON COMMIT DROP
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES
                  (:tenant_a, :slug_a, :slug_a, 'PCB', 'active', '{}'::jsonb, false),
                  (:tenant_b, :slug_b, :slug_b, 'PCB', 'active', '{}'::jsonb, false)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b, "slug_a": slug_a, "slug_b": slug_b},
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES
                  (:user_a, :tenant_a, :email_a, 'hash', 'A', 'active', false),
                  (:user_b, :tenant_b, :email_b, 'hash', 'B', 'active', false)
                """
            ),
            {
                "user_a": user_a,
                "tenant_a": tenant_a,
                "email_a": f"{slug_a}@example.com",
                "user_b": user_b,
                "tenant_b": tenant_b,
                "email_b": f"{slug_b}@example.com",
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, keyword_master_id)
                VALUES
                  (:id_a, :tenant_a, :keyword, :keyword, 'active',
                   'running', :user_a, :keyword_master_id),
                  (:id_b, :tenant_b, :keyword, :keyword, 'active',
                   'running', :user_b, :keyword_master_id)
                """
            ),
            {
                "id_a": str(new_uuid()),
                "tenant_a": tenant_a,
                "user_a": user_a,
                "id_b": str(new_uuid()),
                "tenant_b": tenant_b,
                "user_b": user_b,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )
        result = await CollectionSchedulerService().schedule_due_tasks(conn)
        matched = next(item for item in result["items"] if item["keyword_normalized"] == keyword)
        task_id = matched["task_id"]
        assert matched["linked_keywords"] == 2
        link_count = (
            await conn.execute(
                text("SELECT count(*) FROM collection_task_keywords WHERE task_id = :task_id"),
                {"task_id": task_id},
            )
        ).scalar_one()
    assert link_count == 2


async def test_tenant_create_keyword_binds_keyword_master_without_starting_run() -> None:
    slug_a = f"kw-a-{uuid4().hex[:8]}"
    slug_b = f"kw-b-{uuid4().hex[:8]}"
    keyword = f"PCB, Board {uuid4().hex[:6]}"
    keyword_normalized = normalize_keyword(keyword)
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_a = str(new_uuid())
        tenant_b = str(new_uuid())
        user_a = str(new_uuid())
        user_b = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES
                  (:tenant_a, :slug_a, :slug_a, 'PCB', 'active', '{}'::jsonb, false),
                  (:tenant_b, :slug_b, :slug_b, 'PCB', 'active', '{}'::jsonb, false)
                """
            ),
            {"tenant_a": tenant_a, "tenant_b": tenant_b, "slug_a": slug_a, "slug_b": slug_b},
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES
                  (:user_a, :tenant_a, :email_a, 'hash', 'A', 'active', false),
                  (:user_b, :tenant_b, :email_b, 'hash', 'B', 'active', false)
                """
            ),
            {
                "user_a": user_a,
                "tenant_a": tenant_a,
                "email_a": f"{slug_a}@example.com",
                "user_b": user_b,
                "tenant_b": tenant_b,
                "email_b": f"{slug_b}@example.com",
            },
        )

        first = await TenantSettingsService().create_keyword(
            conn,
            tenant_id=tenant_a,
            user_id=user_a,
            payload={"keyword": keyword},
        )
        second = await TenantSettingsService().create_keyword(
            conn,
            tenant_id=tenant_b,
            user_id=user_b,
            payload={"keyword": keyword.lower()},
        )
        keyword_master_count = (
            await conn.execute(
                text("SELECT count(*) FROM keyword_master WHERE keyword_normalized = :kn"),
                {"kn": keyword_normalized},
            )
        ).scalar_one()
        tenant_keyword_count = (
            await conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM tenant_keyword tk
                    JOIN keyword_master km ON km.id = tk.keyword_master_id
                    WHERE km.keyword_normalized = :kn
                    """
                ),
                {"kn": keyword_normalized},
            )
        ).scalar_one()
        run_count = (
            await conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM collection_runs cr
                    JOIN keyword_master km ON km.id = cr.keyword_master_id
                    WHERE km.keyword_normalized = :kn
                    """
                ),
                {"kn": keyword_normalized},
            )
        ).scalar_one()

    await engine.dispose()

    assert first["keyword_normalized"] == keyword_normalized
    assert second["keyword_normalized"] == keyword_normalized
    assert first["collection_hint"]["matched"] is False
    assert second["collection_hint"]["matched"] is True
    assert keyword_master_count == 1
    assert tenant_keyword_count == 2
    assert run_count == 0


async def test_collection_scheduler_skips_keywords_before_manual_first_trigger() -> None:
    slug = f"sched-not-started-{uuid4().hex[:8]}"
    keyword = f"manual first pcb {uuid4().hex[:6]}"
    engine = make_engine()
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status, subscription_status, created_by)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active', 'not_started', :user_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
            },
        )

        result = await CollectionSchedulerService().schedule_due_tasks(conn)

    await engine.dispose()

    assert all(item["keyword_normalized"] != keyword for item in result["items"])


async def test_collection_scheduler_default_lixiaoyun_daily_limit_is_1000() -> None:
    slug = f"sched-limit-{uuid4().hex[:8]}"
    keyword = f"daily limit pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        keyword_master_id = str(new_uuid())
        await conn.execute(
            text(
                """
                CREATE TEMP TABLE lixiaoyun_raw_companies (
                  keyword_master_id uuid,
                  source_id text,
                  created_at timestamptz NOT NULL DEFAULT now()
                ) ON COMMIT DROP
                """
            )
        )
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, daily_stage1_limit, keyword_master_id)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active',
                   'running', :user_id, NULL, :keyword_master_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )

        result = await CollectionSchedulerService().schedule_due_tasks(conn)

    await engine.dispose()

    matched = next(item for item in result["items"] if item["keyword_normalized"] == keyword)
    assert matched["max_competitors"] == 1000


async def test_manual_trigger_marks_keyword_running_for_future_scheduler_runs() -> None:
    slug = f"sched-trigger-{uuid4().hex[:8]}"
    keyword = f"trigger first pcb {uuid4().hex[:6]}"
    engine = make_engine()
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status, subscription_status, created_by)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active', 'not_started', :user_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
            },
        )

        trigger_result = await AdminCollectionService().trigger_collection(
            conn,
            keyword_normalized=keyword,
            channel="lixiaoyun",
        )
        status = (
            await conn.execute(
                text("SELECT subscription_status FROM collection_keywords WHERE id = :keyword_id"),
                {"keyword_id": keyword_id},
            )
        ).scalar_one()

    await engine.dispose()

    assert trigger_result["task_id"]
    assert status == "running"


async def test_manual_trigger_creates_collection_run_and_first_task() -> None:
    slug = f"sched-run-{uuid4().hex[:8]}"
    keyword = f"run model pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        keyword_master_id = str(new_uuid())
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw)
                VALUES (:tenant_id, :keyword_master_id, :keyword)
                """
            ),
            {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, keyword_master_id)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active',
                   'not_started', :user_id, :keyword_master_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )
        await conn.execute(
            text(
                """
                CREATE TEMP TABLE lixiaoyun_raw_companies (
                  keyword_master_id uuid,
                  source_id text
                ) ON COMMIT DROP
                """
            )
        )
        trigger_result = await AdminCollectionService().trigger_collection(
            conn,
            keyword_normalized=keyword,
            channel="lixiaoyun",
        )
        task_id = trigger_result["task_id"]
        run_id = int(trigger_result["run_id"])
        run_row = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT id::text, keyword_master_id::text, status, request_page_size, daily_limit
                    FROM collection_runs
                    WHERE id = :run_id
                    """
                    ),
                    {"run_id": run_id},
                )
            )
            .mappings()
            .one()
        )
        task_row = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT run_id::text, page_size, scheduled_biz_date
                    FROM collection_tasks
                    WHERE id = :task_id
                    """
                    ),
                    {"task_id": task_id},
                )
            )
            .mappings()
            .one()
        )

    await engine.dispose()

    assert run_row["keyword_master_id"] == keyword_master_id
    assert run_row["status"] == "running"
    assert run_row["request_page_size"] == 10
    assert run_row["daily_limit"] == 1000
    assert task_row["run_id"] == str(run_id)
    assert task_row["page_size"] == 10
    assert task_row["scheduled_biz_date"] is not None


async def test_manual_trigger_daily_limit_is_platform_keyword_scoped_not_tenant_keyword_setting() -> (
    None
):
    slug = f"sched-run-limit-{uuid4().hex[:8]}"
    keyword = f"platform limit pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        keyword_master_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                VALUES (:tenant_id, :slug, :slug, 'PCB', 'active',
                        '{"daily_stage1_limit": 17}'::jsonb, false)
                """
            ),
            {"tenant_id": tenant_id, "slug": slug},
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw)
                VALUES (:tenant_id, :keyword_master_id, :keyword)
                """
            ),
            {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, keyword_master_id, daily_stage1_limit)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active',
                   'not_started', :user_id, :keyword_master_id, 3)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )
        await conn.execute(
            text(
                """
                CREATE TEMP TABLE lixiaoyun_raw_companies (
                  keyword_master_id uuid,
                  source_id text
                ) ON COMMIT DROP
                """
            )
        )

        trigger_result = await AdminCollectionService().trigger_collection(
            conn,
            keyword_normalized=keyword,
            channel="lixiaoyun",
        )
        run_id = int(trigger_result["run_id"])
        rows = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT cr.daily_limit, ct.context
                    FROM collection_runs cr
                    JOIN collection_tasks ct ON ct.run_id = cr.id
                    WHERE cr.id = :run_id
                    """
                    ),
                    {"run_id": run_id},
                )
            )
            .mappings()
            .one()
        )

    await engine.dispose()

    assert rows["daily_limit"] == 1000
    assert rows["context"]["params"]["daily_limit"] == 1000
    assert rows["context"]["params"]["max_competitors"] == 10


async def test_stop_keyword_returns_keyword_to_not_started() -> None:
    slug = f"sched-stop-{uuid4().hex[:8]}"
    keyword = f"stop pcb {uuid4().hex[:6]}"
    engine = make_engine()
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status, subscription_status, created_by)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active', 'running', :user_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
            },
        )

        result = await AdminCollectionService().stop_keyword(conn, keyword_normalized=keyword)
        status = (
            await conn.execute(
                text("SELECT subscription_status FROM collection_keywords WHERE id = :keyword_id"),
                {"keyword_id": keyword_id},
            )
        ).scalar_one()

    await engine.dispose()

    assert result["subscription_status"] == "not_started"
    assert status == "not_started"


async def test_stop_keyword_stops_run_and_cancels_future_tasks() -> None:
    slug = f"sched-stop-run-{uuid4().hex[:8]}"
    keyword = f"stop run pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        keyword_master_id = str(new_uuid())
        running_task_id = str(new_uuid())
        future_task_id = str(new_uuid())
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, keyword_master_id)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active',
                   'running', :user_id, :keyword_master_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )
        run_id = (
            await conn.execute(
                text(
                    """
                INSERT INTO collection_runs
                  (keyword_master_id, provider, stage, status)
                VALUES
                  (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors', 'running')
                RETURNING id
                """
                ),
                {"keyword_master_id": keyword_master_id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO collection_tasks
                  (id, run_id, keyword, keyword_normalized, countries, countries_hash,
                   source_types, task_type, status, priority, scheduled_at)
                VALUES
                  (:running_task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                   '["lixiaoyun"]'::jsonb, 'competitor_search', 'running', 10, now()),
                  (:future_task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                   '["lixiaoyun"]'::jsonb, 'competitor_search', 'pending', 10,
                   now() + interval '1 day')
                """
            ),
            {
                "running_task_id": running_task_id,
                "future_task_id": future_task_id,
                "run_id": run_id,
                "keyword": keyword,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                VALUES
                  (:link_a, :running_task_id, :keyword_id, :tenant_id),
                  (:link_b, :future_task_id, :keyword_id, :tenant_id)
                """
            ),
            {
                "link_a": str(new_uuid()),
                "link_b": str(new_uuid()),
                "running_task_id": running_task_id,
                "future_task_id": future_task_id,
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
            },
        )

        result = await AdminCollectionService().stop_keyword(conn, keyword_normalized=keyword)
        run_status = (
            await conn.execute(
                text("SELECT status FROM collection_runs WHERE id = :run_id"),
                {"run_id": run_id},
            )
        ).scalar_one()
        task_statuses = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT status
                    FROM collection_tasks
                    WHERE id IN (:running_task_id, :future_task_id)
                    ORDER BY id
                    """
                    ),
                    {"running_task_id": running_task_id, "future_task_id": future_task_id},
                )
            )
            .scalars()
            .all()
        )

    await engine.dispose()

    assert result["run_status"] == "stopped"
    assert run_status == "stopped"
    assert task_statuses == ["cancelled", "cancelled"]


async def test_scheduler_creates_continuation_task_for_due_daily_limit_run() -> None:
    slug = f"sched-continue-{uuid4().hex[:8]}"
    keyword = f"continue pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        keyword_master_id = str(new_uuid())
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, keyword_master_id)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active',
                   'not_started', :user_id, :keyword_master_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )
        run_id = (
            await conn.execute(
                text(
                    """
                INSERT INTO collection_runs
                  (keyword_master_id, provider, stage, status,
                   cursor, skip_source_ids, next_run_at, daily_limit, request_page_size)
                VALUES
                  (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors',
                   'daily_limit_reached', '{"page": 11}'::jsonb, '["seen-1"]'::jsonb,
                   now() - interval '1 minute', 1000, 10)
                RETURNING id
                """
                ),
                {"keyword_master_id": keyword_master_id},
            )
        ).scalar_one()

        result = await CollectionSchedulerService().schedule_due_tasks(conn)
        task = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT run_id::text, status, cursor_snapshot, page_size
                    FROM collection_tasks
                    WHERE run_id = :run_id
                    """
                    ),
                    {"run_id": run_id},
                )
            )
            .mappings()
            .one()
        )

    await engine.dispose()

    assert result["scheduled_count"] == 1
    assert result["items"][0]["run_id"] == str(run_id)
    assert task["run_id"] == str(run_id)
    assert task["status"] == "pending"
    assert task["cursor_snapshot"] == {"page": 11}
    assert task["page_size"] == 10


async def test_admin_keyword_list_uses_collection_run_status_not_subscription_status() -> None:
    slug = f"admin-run-status-{uuid4().hex[:8]}"
    keyword = f"run status pcb {uuid4().hex[:6]}"
    engine = make_engine()
    async with engine.begin() as conn:
        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        keyword_id = str(new_uuid())
        keyword_master_id = str(new_uuid())
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
                VALUES (:user_id, :tenant_id, :email, 'hash', 'A', 'active', false)
                """
            ),
            {"user_id": user_id, "tenant_id": tenant_id, "email": f"{slug}@example.com"},
        )
        await conn.execute(
            text(
                """
                INSERT INTO keyword_master (id, keyword, keyword_normalized)
                VALUES (:keyword_master_id, :keyword, :keyword)
                """
            ),
            {"keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status,
                   subscription_status, created_by, keyword_master_id)
                VALUES
                  (:keyword_id, :tenant_id, :keyword, :keyword, 'active',
                   'not_started', :user_id, :keyword_master_id)
                """
            ),
            {
                "keyword_id": keyword_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO collection_runs
                  (keyword_master_id, provider, stage, status,
                   daily_limit, request_page_size, next_run_at)
                VALUES
                  (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors',
                   'daily_limit_reached', 1000, 10, now() + interval '1 day')
                RETURNING id
                """
            ),
            {"keyword_master_id": keyword_master_id},
        )
        await conn.execute(
            text(
                """
                INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw)
                VALUES (:tenant_id, :keyword_master_id, :keyword)
                """
            ),
            {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id, "keyword": keyword},
        )
        await conn.execute(
            text(
                """
                INSERT INTO lixiaoyun_raw_companies (keyword_master_id, source_id, name)
                VALUES (:keyword_master_id, :source_id, :name)
                """
            ),
            {
                "keyword_master_id": keyword_master_id,
                "source_id": f"lxy-{uuid4().hex}",
                "name": "Run Status Peer",
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO tendata_raw_companies (keyword_master_id, source_id, name)
                VALUES (:keyword_master_id, :source_id, :name)
                """
            ),
            {
                "keyword_master_id": keyword_master_id,
                "source_id": f"td-{uuid4().hex}",
                "name": "Run Status Buyer",
            },
        )

        rows = await AdminCollectionService().list_collection_keywords(conn)
        matched = next(row for row in rows if row["keyword_normalized"] == keyword)

    await engine.dispose()

    assert matched["subscription_status"] == "daily_limit_reached"
    assert matched["reverse_stage1"]["status"] == "daily_limit_reached"
    assert matched["reverse_stage1"]["total_count"] == 1
    assert matched["reverse_stage2"]["total_count"] == 1
