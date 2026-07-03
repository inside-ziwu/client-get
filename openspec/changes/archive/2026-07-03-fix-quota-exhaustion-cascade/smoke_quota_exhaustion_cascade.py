from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.db.rls import set_current_tenant  # noqa: E402
from app.services.tenant_messaging_service import TenantMessagingService  # noqa: E402
from app.services.tenant_query_service import TenantQueryService  # noqa: E402


def _load_backend_env() -> None:
    for line in (BACKEND / ".env").read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _asyncpg_url(raw_url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(raw_url)
    return urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, "", ""))


async def _fetch_seed_contact(conn):
    result = await conn.execute(
        text(
            """
            SELECT cc.id AS clean_company_id,
                   shc.id AS clean_contact_id
            FROM waimaotong_clean_companies cc
            JOIN waimaotong_clean_contacts shc
              ON shc.company_id = cc.company_id
            WHERE shc.email IS NOT NULL
            LIMIT 1
            """
        )
    )
    row = result.mappings().first()
    if row is None:
        result = await conn.execute(
            text(
                """
                SELECT tc.clean_company_id, tco.clean_contact_id
                FROM tenant_companies tc
                JOIN tenant_contacts tco
                  ON tco.tenant_id = tc.tenant_id
                 AND tco.clean_company_id = tc.clean_company_id
                LIMIT 1
                """
            )
        )
        row = result.mappings().first()
    if row is None:
        raise AssertionError("dev 库缺少可复用的 clean company/contact")
    return row


async def _insert_base_graph(conn):
    suffix = uuid4().hex[:8]
    tenant_id = uuid4()
    user_id = uuid4()
    domain_id = uuid4()
    template_id = uuid4()
    plan_id = uuid4()
    step_id = uuid4()
    recipient_id = uuid4()
    enrollment_id = uuid4()
    lock_id = uuid4()
    email_id = uuid4()
    usage_id = uuid4()
    seed = await _fetch_seed_contact(conn)

    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, needs_onboarding)
            VALUES (:id, :name, :slug, 'pcb', false)
            """
        ),
        {"id": tenant_id, "name": f"smoke-{suffix}", "slug": f"smoke-{suffix}"},
    )
    await set_current_tenant(conn, str(tenant_id))
    await conn.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, email, password_hash, name, must_change_pwd)
            VALUES (:id, :tenant_id, :email, 'smoke', 'Smoke User', false)
            """
        ),
        {"id": user_id, "tenant_id": tenant_id, "email": f"smoke-{suffix}@example.com"},
    )
    await conn.execute(
        text(
            """
            INSERT INTO domain_warmup_status
              (id, tenant_id, domain, verification_status, daily_limit, sender_email)
            VALUES
              (:id, :tenant_id, :domain, 'verified', 10, :sender_email)
            """
        ),
        {
            "id": domain_id,
            "tenant_id": tenant_id,
            "domain": f"smoke-{suffix}.example.com",
            "sender_email": f"sender-{suffix}@example.com",
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO email_templates
              (id, tenant_id, source_type, name, category, subject, body_html, body_text)
            VALUES
              (:id, :tenant_id, 'custom', 'Smoke Template', 'cold_outreach',
               'Hello {{company_name}}', '<p>Hello</p>', 'Hello')
            """
        ),
        {"id": template_id, "tenant_id": tenant_id},
    )
    await conn.execute(
        text(
            """
            INSERT INTO sending_plans
              (id, tenant_id, created_by, name, status, recipient_source,
               recipient_config, sender_name, sender_email, domain_id)
            VALUES
              (:id, :tenant_id, :created_by, 'Smoke Plan', 'running', 'manual',
               '{}'::jsonb, 'Smoke', :sender_email, :domain_id)
            """
        ),
        {
            "id": plan_id,
            "tenant_id": tenant_id,
            "created_by": user_id,
            "sender_email": f"sender-{suffix}@example.com",
            "domain_id": domain_id,
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO sequence_steps
              (id, tenant_id, plan_id, step_number, template_id, condition_type, delay_days)
            VALUES (:id, :tenant_id, :plan_id, 1, :template_id, 'always', 0)
            """
        ),
        {"id": step_id, "tenant_id": tenant_id, "plan_id": plan_id, "template_id": template_id},
    )
    company_result = await conn.execute(
        text(
            """
            INSERT INTO tenant_companies (tenant_id, clean_company_id)
            VALUES (:tenant_id, :clean_company_id)
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "clean_company_id": seed["clean_company_id"]},
    )
    tenant_company_id = company_result.scalar_one()
    contact_result = await conn.execute(
        text(
            """
            INSERT INTO tenant_contacts (tenant_id, clean_contact_id, clean_company_id)
            VALUES (:tenant_id, :clean_contact_id, :clean_company_id)
            RETURNING id
            """
        ),
        {
            "tenant_id": tenant_id,
            "clean_contact_id": seed["clean_contact_id"],
            "clean_company_id": seed["clean_company_id"],
        },
    )
    tenant_contact_id = contact_result.scalar_one()
    await conn.execute(
        text(
            """
            INSERT INTO sending_plan_recipients
              (id, tenant_id, plan_id, tenant_company_id, tenant_contact_id, source_type)
            VALUES (:id, :tenant_id, :plan_id, :tenant_company_id, :tenant_contact_id, 'manual')
            """
        ),
        {
            "id": recipient_id,
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "tenant_company_id": tenant_company_id,
            "tenant_contact_id": tenant_contact_id,
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO sequence_enrollments
              (id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id,
               current_step, status, next_step_due_at, send_attempt_count)
            VALUES
              (:id, :tenant_id, :plan_id, :recipient_id, :tenant_contact_id,
               1, 'active', now() - interval '1 minute', 0)
            """
        ),
        {
            "id": enrollment_id,
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "recipient_id": recipient_id,
            "tenant_contact_id": tenant_contact_id,
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO email_send_locks
              (id, tenant_id, enrollment_id, step_id, status, locked_by,
               email_id, email_created_at)
            VALUES
              (:id, :tenant_id, :enrollment_id, :step_id, 'locked', 'smoke',
               :email_id, :email_created_at)
            """
        ),
        {
            "id": lock_id,
            "tenant_id": tenant_id,
            "enrollment_id": enrollment_id,
            "step_id": step_id,
            "email_id": email_id,
            "email_created_at": datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO domain_daily_usage
              (id, tenant_id, domain_id, usage_date, daily_limit, reserved_count)
            VALUES (:id, :tenant_id, :domain_id, :usage_date, 10, 1)
            """
        ),
        {
            "id": usage_id,
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "usage_date": date(2026, 7, 3),
        },
    )
    return {
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "template_id": template_id,
        "plan_id": plan_id,
        "step_id": step_id,
        "recipient_id": recipient_id,
        "enrollment_id": enrollment_id,
        "email_id": email_id,
        "email_created_at": datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
        "tenant_contact_id": tenant_contact_id,
    }


async def _insert_email(conn, ids, *, status, created_at, email_id=None):
    await conn.execute(
        text(
            """
            INSERT INTO emails
              (id, created_at, tenant_id, plan_id, step_id, step_number, template_id,
               enrollment_id, tenant_contact_id, from_email, to_email, subject,
               body_html, body_text, status, sent_at, engagelab_message_id)
            VALUES
              (:id, :created_at, :tenant_id, :plan_id, :step_id, 1, :template_id,
               :enrollment_id, :tenant_contact_id, 'sender@example.com',
               'buyer@example.com', 'Hello', '<p>Hello</p>', 'Hello', :status,
               :sent_at, :message_id)
            """
        ),
        {
            "id": email_id or uuid4(),
            "created_at": created_at,
            "tenant_id": ids["tenant_id"],
            "plan_id": ids["plan_id"],
            "step_id": ids["step_id"],
            "template_id": ids["template_id"],
            "enrollment_id": ids["enrollment_id"],
            "tenant_contact_id": ids["tenant_contact_id"],
            "status": status,
            "sent_at": None if status == "queued" else created_at,
            "message_id": None if status == "queued" else f"msg-{uuid4()}",
        },
    )


async def _assert_stats(conn, ids):
    query = TenantQueryService()
    created_at = datetime(2026, 7, 3, 1, 0, tzinfo=UTC)
    for _ in range(6):
        await _insert_email(conn, ids, status="delivered", created_at=created_at)
    for _ in range(2):
        await _insert_email(conn, ids, status="bounced", created_at=created_at)
    await _insert_email(conn, ids, status="failed", created_at=created_at)
    await _insert_email(conn, ids, status="queued", created_at=created_at)

    raw_count_result = await conn.execute(
        text(
            """
            SELECT count(*)
            FROM emails
            WHERE tenant_id = :tenant_id
              AND created_at >= :start_date
              AND created_at < :end_date
            """
        ),
        {
            "tenant_id": ids["tenant_id"],
            "start_date": datetime(2026, 7, 3, tzinfo=UTC),
            "end_date": datetime(2026, 7, 4, tzinfo=UTC),
        },
    )
    raw_count = raw_count_result.scalar_one()
    if raw_count != 10:
        debug = await conn.execute(
            text(
                """
                SELECT current_setting('app.current_tenant_id', true) AS tenant_setting,
                       count(*) FILTER (WHERE plan_id = :plan_id) AS by_plan,
                       array_agg(DISTINCT tenant_id::text)
                         FILTER (WHERE plan_id = :plan_id) AS plan_tenant_ids,
                       min(created_at) AS min_created_at,
                       max(created_at) AS max_created_at
                FROM emails
                """
            ),
            {"plan_id": ids["plan_id"]},
        )
        raise AssertionError(
            f"raw email count={raw_count}, expected tenant={ids['tenant_id']}, "
            f"debug={dict(debug.mappings().one())}"
        )

    stats = await query.email_stats_by_date_range(
        conn, str(ids["tenant_id"]), date(2026, 7, 3), date(2026, 7, 3)
    )
    assert stats["summary"]["targets"] == 10, stats
    assert stats["summary"]["sent"] == 8, stats
    assert stats["summary"]["billing"] == 8, stats
    assert stats["summary"]["delivered"] == 6, stats
    assert stats["summary"]["delivered_percent"] == 75.0, stats

    overview = await query.plan_overview(conn, str(ids["tenant_id"]))
    assert overview["emails_sent"] == 8
    plan_overview = await query.plan_overview(conn, str(ids["tenant_id"]), str(ids["plan_id"]))
    assert plan_overview["emails_sent"] == 8

    quota = await query.daily_quota(
        conn,
        str(ids["tenant_id"]),
        now_utc=datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
    )
    assert quota["used"] == 8
    print("smoke stats: ok")


async def _assert_window(conn, ids):
    service = TenantMessagingService()
    await conn.execute(
        text(
            """
            INSERT INTO domain_daily_usage
              (id, tenant_id, domain_id, usage_date, daily_limit, reserved_count)
            VALUES (:id, :tenant_id, :domain_id, :usage_date, 1, 1)
            """
        ),
        {
            "id": uuid4(),
            "tenant_id": ids["tenant_id"],
            "domain_id": ids["domain_id"],
            "usage_date": date(2026, 7, 2),
        },
    )
    reserved = await service.reserve_domain_quota(
        conn,
        domain_id=str(ids["domain_id"]),
        count=1,
        now_utc=datetime(2026, 7, 2, 16, 30, tzinfo=UTC),
    )
    assert reserved["usage_date"] == "2026-07-03"
    assert reserved["reserved_count"] == 2
    await service._release_reserved_quota(
        conn,
        domain_id=str(ids["domain_id"]),
        plan_id=ids["plan_id"],
        now_utc=datetime(2026, 7, 2, 16, 30, tzinfo=UTC),
    )
    usage = await conn.execute(
        text(
            """
            SELECT reserved_count
            FROM domain_daily_usage
            WHERE domain_id = :domain_id AND usage_date = :usage_date
            """
        ),
        {"domain_id": ids["domain_id"], "usage_date": date(2026, 7, 3)},
    )
    assert usage.scalar_one() == 1
    print("smoke window: ok")


async def _assert_defer_loop(conn, ids):
    service = TenantMessagingService()
    await _insert_email(
        conn,
        ids,
        status="queued",
        created_at=ids["email_created_at"],
        email_id=ids["email_id"],
    )
    resume_at = datetime(2026, 7, 3, 16, 0, tzinfo=UTC)
    result = await service.defer_email_for_quota(
        conn,
        email_id=str(ids["email_id"]),
        resume_at=resume_at,
        now_utc=datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
    )
    assert result["status"] == "deferred_for_quota"
    email_count = await conn.execute(
        text("SELECT count(*) FROM emails WHERE id = :email_id"),
        {"email_id": ids["email_id"]},
    )
    assert email_count.scalar_one() == 0
    lock = await conn.execute(
        text(
            """
            SELECT status, email_id
            FROM email_send_locks
            WHERE enrollment_id = :enrollment_id
            """
        ),
        {"enrollment_id": ids["enrollment_id"]},
    )
    lock_row = lock.mappings().one()
    assert lock_row["status"] == "released"
    assert lock_row["email_id"] is None
    enrollment = await conn.execute(
        text(
            """
            SELECT status, next_step_due_at, send_attempt_count
            FROM sequence_enrollments
            WHERE id = :enrollment_id
            """
        ),
        {"enrollment_id": ids["enrollment_id"]},
    )
    enrollment_row = enrollment.mappings().one()
    assert enrollment_row["status"] == "active"
    assert enrollment_row["next_step_due_at"] == resume_at
    assert enrollment_row["send_attempt_count"] == 0

    await conn.execute(
        text(
            """
            UPDATE sequence_enrollments
            SET next_step_due_at = now() - interval '1 minute'
            WHERE id = :enrollment_id
            """
        ),
        {"enrollment_id": ids["enrollment_id"]},
    )
    claimed = await service.claim_due_emails(
        conn,
        service_instance="smoke",
        limit=1,
        domain_id=str(ids["domain_id"]),
        timezone_config={"rules": {}, "default_rule": None, "countries": {}, "holidays": set()},
        now_utc=datetime(2026, 7, 3, 1, 0, tzinfo=UTC),
    )
    assert claimed["items"], "claim_due_emails should rebuild one queued email"
    rebuilt_email_id = claimed["items"][0]["email_id"]
    rebuilt = await conn.execute(
        text(
            """
            SELECT count(*)
            FROM emails
            WHERE id = :email_id AND status = 'queued'
            """
        ),
        {"email_id": rebuilt_email_id},
    )
    assert rebuilt.scalar_one() == 1
    print("smoke defer loop: ok")


async def main() -> None:
    _load_backend_env()
    raw_url = os.environ["CLIENTGET_DEV_DATABASE_URL"]
    engine = create_async_engine(_asyncpg_url(raw_url), connect_args={"ssl": True})
    async with engine.connect() as conn:
        tx = await conn.begin()
        try:
            ids = await _insert_base_graph(conn)
            await _assert_stats(conn, ids)
            await _assert_window(conn, ids)
            await _assert_defer_loop(conn, ids)
        finally:
            await tx.rollback()
    await engine.dispose()
    print("smoke all: ok (rolled back)")


if __name__ == "__main__":
    asyncio.run(main())
