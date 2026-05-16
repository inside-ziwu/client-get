from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.ids import new_uuid
from app.services.collection_service import CollectionService


async def test_claim_tasks_treats_null_scheduled_at_as_due() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TEMP TABLE collection_tasks (
                      id uuid PRIMARY KEY,
                      run_id bigint,
                      keyword text NOT NULL,
                      countries jsonb NOT NULL DEFAULT '[]'::jsonb,
                      source_types jsonb NOT NULL DEFAULT '[]'::jsonb,
                      task_type varchar(50) NOT NULL DEFAULT 'competitor_search',
                      context jsonb,
                      status varchar(20) NOT NULL,
                      priority int NOT NULL DEFAULT 0,
                      page_size int NOT NULL DEFAULT 10,
                      cursor_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
                      scheduled_at timestamptz,
                      started_at timestamptz,
                      completed_at timestamptz,
                      lease_id uuid,
                      lease_owner varchar(100),
                      lease_expires_at timestamptz,
                      attempt_count int NOT NULL DEFAULT 0,
                      max_attempts int NOT NULL DEFAULT 3,
                      error_message text,
                      created_at timestamptz NOT NULL DEFAULT now(),
                      updated_at timestamptz NOT NULL DEFAULT now()
                    ) ON COMMIT DROP
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_tasks
                      (id, keyword, source_types, status, priority, scheduled_at)
                    VALUES
                      ('00000000-0000-0000-0000-000000000001',
                       'pcb', '["lixiaoyun"]'::jsonb, 'pending', 10, NULL)
                    """
                )
            )

            result = await CollectionService().claim_tasks(
                conn,
                service_instance="test-worker",
                limit=1,
                lease_seconds=300,
            )

        assert [item["id"] for item in result["tasks"]] == ["00000000-0000-0000-0000-000000000001"]
    finally:
        await engine.dispose()


async def test_claim_tasks_skips_pending_tasks_before_admin_trigger() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            tenant_id = str(new_uuid())
            user_id = str(new_uuid())
            keyword_id = str(new_uuid())
            task_id = str(new_uuid())
            slug = f"claim-not-started-{uuid4().hex[:8]}"
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
                      (:keyword_id, :tenant_id, 'manual only pcb', 'manual only pcb',
                       'active', 'not_started', :user_id)
                    """
                ),
                {"keyword_id": keyword_id, "tenant_id": tenant_id, "user_id": user_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_tasks
                      (id, keyword, keyword_normalized, countries, countries_hash,
                       source_types, task_type, status, priority, scheduled_at)
                    VALUES
                      (:task_id, 'manual only pcb', 'manual only pcb', '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search', 'pending', 999999, now())
                    """
                ),
                {"task_id": task_id},
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

            result = await CollectionService().claim_tasks(
                conn,
                service_instance="test-worker",
                limit=1,
                lease_seconds=300,
            )

        assert result["tasks"] == []
    finally:
        await engine.dispose()


async def test_claim_tasks_uses_collection_run_status_not_tenant_subscription_status() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            tenant_id = str(new_uuid())
            user_id = str(new_uuid())
            keyword_id = str(new_uuid())
            keyword_master_id = str(new_uuid())
            task_id = str(new_uuid())
            slug = f"claim-run-{uuid4().hex[:8]}"
            keyword = f"claim run pcb {uuid4().hex[:6]}"
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
                      (:task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search', 'pending', 999999, now())
                    """
                ),
                {"task_id": task_id, "run_id": run_id, "keyword": keyword},
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

            result = await CollectionService().claim_tasks(
                conn,
                service_instance="test-worker",
                limit=1,
                lease_seconds=300,
            )

        assert [item["id"] for item in result["tasks"]] == [task_id]
    finally:
        await engine.dispose()


async def test_claim_tasks_inherits_cursor_and_skip_source_ids_from_parent_run() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            keyword_master_id = str(new_uuid())
            task_id = str(new_uuid())
            keyword = f"resume cursor pcb {uuid4().hex[:6]}"
            await conn.execute(
                text(
                    """
                    INSERT INTO keyword_master (id, keyword, keyword_normalized)
                    VALUES (:keyword_master_id, :keyword, :keyword)
                    """
                ),
                {"keyword_master_id": keyword_master_id, "keyword": keyword},
            )
            run_id = (
                await conn.execute(
                    text(
                        """
                    INSERT INTO collection_runs
                      (keyword_master_id, provider, stage, status,
                       daily_limit, request_page_size, today_fetched, cursor, skip_source_ids)
                    VALUES
                      (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors',
                       'daily_limit_reached', 1000, 10, 1000,
                       '{"page": 7}'::jsonb, '["old-src"]'::jsonb)
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
                       source_types, task_type, status, priority, scheduled_at, cursor_snapshot)
                    VALUES
                      (:task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search', 'pending', 999999, now(),
                       '{}'::jsonb)
                    """
                ),
                {"task_id": task_id, "run_id": run_id, "keyword": keyword},
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

            result = await CollectionService().claim_tasks(
                conn,
                service_instance="test-worker",
                limit=1,
                lease_seconds=300,
            )

        assert [item["id"] for item in result["tasks"]] == [task_id]
        assert result["tasks"][0]["context"]["params"]["cursor"] == {"page": 7}
        assert result["tasks"][0]["context"]["params"]["skip_source_ids"] == ["old-src"]
    finally:
        await engine.dispose()


async def test_submit_result_marks_run_daily_limit_and_creates_next_day_task() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            keyword_master_id = str(new_uuid())
            task_id = str(new_uuid())
            lease_id = str(new_uuid())
            keyword = f"daily run pcb {uuid4().hex[:6]}"
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
                    -- Daily limit is platform keyword/run scoped. This empty temp table
                    -- only shadows stale local test schema while keeping the test free
                    -- of any tenant subscription rows.
                    CREATE TEMP TABLE tenant_keyword (
                      id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                      tenant_id uuid NOT NULL,
                      keyword_master_id uuid NOT NULL,
                      keyword_raw text NOT NULL,
                      created_by uuid,
                      created_at timestamptz NOT NULL DEFAULT now(),
                      status text NOT NULL DEFAULT 'active',
                      UNIQUE (tenant_id, keyword_master_id)
                    ) ON COMMIT DROP
                    """
                )
            )
            run_id = (
                await conn.execute(
                    text(
                        """
                    INSERT INTO collection_runs
                      (keyword_master_id, provider, stage, status,
                       daily_limit, request_page_size, today_fetched)
                    VALUES
                      (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors',
                       'running', 2, 10, 1)
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
                       source_types, task_type, status, priority, scheduled_at,
                       lease_id, lease_owner, lease_expires_at, attempt_count)
                    VALUES
                      (:task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search', 'running', 999999, now(),
                       :lease_id, 'test-worker', now() + interval '5 minutes', 1)
                    """
                ),
                {"task_id": task_id, "run_id": run_id, "keyword": keyword, "lease_id": lease_id},
            )
            await CollectionService().submit_result(
                conn,
                task_id=task_id,
                lease_id=lease_id,
                companies=[],
                contacts=[],
                competitors=[
                    {
                        "target_table": "lixiaoyun_raw_companies",
                        "source_id": f"daily-src-{uuid4().hex[:8]}",
                        "name": "每日上限测试公司",
                        "raw_payload": {},
                    }
                ],
                request_id=f"daily-limit-{uuid4().hex}",
                service_name="collection-service",
            )
            run = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT status, next_run_at, today_fetched
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
            continuation = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT status, scheduled_at
                        FROM collection_tasks
                        WHERE run_id = :run_id
                          AND id <> :task_id
                        """
                        ),
                        {"run_id": run_id, "task_id": task_id},
                    )
                )
                .mappings()
                .one()
            )

        assert run["status"] == "daily_limit_reached"
        assert run["today_fetched"] == 2
        assert run["next_run_at"] is not None
        assert continuation["status"] == "pending"
        assert continuation["scheduled_at"] == run["next_run_at"]
    finally:
        await engine.dispose()


async def test_submit_result_persists_run_cursor_and_skip_source_ids() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            keyword_master_id = str(new_uuid())
            task_id = str(new_uuid())
            lease_id = str(new_uuid())
            keyword = f"cursor pcb {uuid4().hex[:6]}"
            await conn.execute(
                text(
                    """
                    CREATE TEMP TABLE tenant_keyword (
                      id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                      tenant_id uuid NOT NULL,
                      keyword_master_id uuid NOT NULL,
                      keyword_raw text NOT NULL,
                      created_by uuid,
                      created_at timestamptz NOT NULL DEFAULT now(),
                      status text NOT NULL DEFAULT 'active',
                      UNIQUE (tenant_id, keyword_master_id)
                    ) ON COMMIT DROP
                    """
                )
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
            run_id = (
                await conn.execute(
                    text(
                        """
                    INSERT INTO collection_runs
                      (keyword_master_id, provider, stage, status,
                       daily_limit, request_page_size, today_fetched, cursor, skip_source_ids)
                    VALUES
                      (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors',
                       'running', 1000, 10, 0, '{}'::jsonb, '[]'::jsonb)
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
                       source_types, task_type, status, priority, scheduled_at,
                       lease_id, lease_owner, lease_expires_at, attempt_count)
                    VALUES
                      (:task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search', 'running', 999999, now(),
                       :lease_id, 'test-worker', now() + interval '5 minutes', 1)
                    """
                ),
                {"task_id": task_id, "run_id": run_id, "keyword": keyword, "lease_id": lease_id},
            )

            await CollectionService().submit_result(
                conn,
                task_id=task_id,
                lease_id=lease_id,
                companies=[],
                contacts=[],
                competitors=[
                    {
                        "target_table": "lixiaoyun_raw_companies",
                        "source_id": "cursor-src-1",
                        "name": "Cursor Company",
                        "raw_payload": {},
                    }
                ],
                cursor={"page": 3},
                skip_source_ids=["cursor-src-1"],
                request_id=f"cursor-{uuid4().hex}",
                service_name="collection-service",
            )
            run = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT cursor, skip_source_ids
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

        assert run["cursor"] == {"page": 3}
        assert run["skip_source_ids"] == ["cursor-src-1"]
    finally:
        await engine.dispose()


async def test_tenant_keyword_map_uses_run_keyword_master_subscribers() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            tenant_a = str(new_uuid())
            tenant_b = str(new_uuid())
            keyword_master_id = str(new_uuid())
            task_id = str(new_uuid())
            keyword = f"fanout map pcb {uuid4().hex[:6]}"
            await conn.execute(
                text(
                    """
                    CREATE TEMP TABLE tenant_keyword (
                      id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                      tenant_id uuid NOT NULL,
                      keyword_master_id uuid NOT NULL,
                      keyword_raw text NOT NULL,
                      created_by uuid,
                      created_at timestamptz NOT NULL DEFAULT now(),
                      status text NOT NULL DEFAULT 'active',
                      UNIQUE (tenant_id, keyword_master_id)
                    ) ON COMMIT DROP
                    """
                )
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
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES
                      (:tenant_a, :keyword_master_id, 'PCB', 'active'),
                      (:tenant_b, :keyword_master_id, 'P.C.B', 'active')
                    """
                ),
                {
                    "tenant_a": tenant_a,
                    "tenant_b": tenant_b,
                    "keyword_master_id": keyword_master_id,
                },
            )
            run_id = (
                await conn.execute(
                    text(
                        """
                    INSERT INTO collection_runs
                      (keyword_master_id, provider, stage, status)
                    VALUES (:keyword_master_id, 'lixiaoyun', 'lixiaoyun_competitors', 'running')
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
                      (:task_id, :run_id, :keyword, :keyword, '[]'::jsonb, '',
                       '["lixiaoyun"]'::jsonb, 'competitor_search', 'running', 999999, now())
                    """
                ),
                {"task_id": task_id, "run_id": run_id, "keyword": keyword},
            )

            tenant_keyword_map = await CollectionService().get_tenant_keyword_map(conn, task_id)

        assert set(tenant_keyword_map) == {tenant_a, tenant_b}
        assert tenant_keyword_map[tenant_a]
        assert tenant_keyword_map[tenant_b]
    finally:
        await engine.dispose()


async def test_lixiaoyun_upsert_accepts_esdate_string() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            keyword_master_id = str(new_uuid())
            await conn.execute(
                text(
                    """
                    CREATE TEMP TABLE lixiaoyun_raw_companies (
                      id bigserial PRIMARY KEY,
                      keyword_master_id uuid,
                      source_id text NOT NULL,
                      name text,
                      english_name text,
                      domain text,
                      esdate date,
                      legalperson text,
                      uncid text,
                      reg_capital text,
                      employee_scale text,
                      reg_address text,
                      raw_payload jsonb,
                      created_at timestamptz DEFAULT now(),
                      UNIQUE (keyword_master_id, source_id)
                    ) ON COMMIT DROP
                    """
                )
            )

            await CollectionService()._upsert_lixiaoyun_raw(
                conn,
                {
                    "keyword_master_id": keyword_master_id,
                    "source_id": "lx-date-string",
                    "task_id": "00000000-0000-0000-0000-000000000002",
                    "name": "日期测试公司",
                    "esdate": "2013-03-14",
                    "raw_payload": {"esdate": "2013-03-14"},
                },
            )

            result = await conn.execute(
                text(
                    "SELECT esdate::text FROM lixiaoyun_raw_companies WHERE source_id = 'lx-date-string'"
                )
            )

        assert result.scalar_one() == "2013-03-14"
    finally:
        await engine.dispose()


async def test_lixiaoyun_upsert_refreshes_employee_scale_on_conflict() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, future=True)
    try:
        async with engine.begin() as conn:
            keyword_master_id = str(new_uuid())
            await conn.execute(
                text(
                    """
                    CREATE TEMP TABLE lixiaoyun_raw_companies (
                      id bigserial PRIMARY KEY,
                      keyword_master_id uuid,
                      source_id text NOT NULL,
                      name text,
                      english_name text,
                      domain text,
                      esdate date,
                      legalperson text,
                      uncid text,
                      reg_capital text,
                      employee_scale text,
                      reg_address text,
                      raw_payload jsonb,
                      created_at timestamptz DEFAULT now(),
                      UNIQUE (keyword_master_id, source_id)
                    ) ON COMMIT DROP
                    """
                )
            )

            service = CollectionService()
            await service._upsert_lixiaoyun_raw(
                conn,
                {
                    "keyword_master_id": keyword_master_id,
                    "source_id": "lx-scale-refresh",
                    "task_id": "00000000-0000-0000-0000-000000000003",
                    "name": "规模测试公司",
                    "employee_scale": "",
                    "raw_payload": {"employee_scale": ""},
                },
            )
            await service._upsert_lixiaoyun_raw(
                conn,
                {
                    "keyword_master_id": keyword_master_id,
                    "source_id": "lx-scale-refresh",
                    "task_id": "00000000-0000-0000-0000-000000000003",
                    "name": "规模测试公司",
                    "employee_scale": "1000人以上",
                    "raw_payload": {"employee_scale": "1000人以上"},
                },
            )

            result = await conn.execute(
                text(
                    "SELECT employee_scale FROM lixiaoyun_raw_companies WHERE source_id = 'lx-scale-refresh'"
                )
            )

        assert result.scalar_one() == "1000人以上"
    finally:
        await engine.dispose()
