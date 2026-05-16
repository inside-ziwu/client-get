from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.tenant_hard_delete_service import (
    TARGET_TENANT_SLUG,
    TenantHardDeleteError,
    TenantHardDeleteService,
)
from app.services.tenant_messaging_service import TenantMessagingService
from tests.helpers import make_engine


async def _tenant(conn, *, slug: str | None = None, name: str | None = None) -> tuple[str, str]:
    if slug:
        existing = (
            await conn.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": slug},
            )
        ).mappings().first()
        if existing is not None:
            await conn.execute(
                text("UPDATE tenants SET name = :name WHERE slug = :slug"),
                {"name": name or slug, "slug": slug},
            )
            return str(existing["id"]), slug

    tenant_id = str(new_uuid())
    actual_slug = slug or f"hard-delete-{uuid4().hex[:8]}"
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:tenant_id, :name, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"tenant_id": tenant_id, "name": name or actual_slug, "slug": actual_slug},
    )
    return tenant_id, actual_slug


async def _user(conn, tenant_id: str) -> str:
    user_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
            VALUES (:user_id, :tenant_id, :email, 'hash', '硬删除测试用户', 'active', false)
            """
        ),
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": f"hard-delete-{uuid4().hex[:8]}@example.com",
        },
    )
    return user_id


async def _clean_company(
    conn,
    *,
    name: str,
    normalized: str | None = None,
    country_iso3: str = "USA",
) -> int:
    return (
        await conn.execute(
            text(
                """
                INSERT INTO clean_companies (name, name_normalized, country_iso3, website)
                VALUES (:name, :name_normalized, :country_iso3, :website)
                ON CONFLICT (name_normalized, country_iso3) DO UPDATE
                  SET name = EXCLUDED.name,
                      website = COALESCE(clean_companies.website, EXCLUDED.website)
                RETURNING id
                """
            ),
            {
                "name": name,
                "name_normalized": normalized or name.lower(),
                "country_iso3": country_iso3,
                "website": f"https://{uuid4().hex}.example.com",
            },
        )
    ).scalar_one()


async def _tenant_company(
    conn,
    tenant_id: str,
    *,
    name: str,
    normalized: str | None = None,
    country_iso3: str = "USA",
) -> int:
    clean_company_id = await _clean_company(
        conn,
        name=name,
        normalized=normalized,
        country_iso3=country_iso3,
    )
    return (
        await conn.execute(
            text(
                """
                INSERT INTO tenant_companies
                  (tenant_id, clean_company_id, business_status, data_status, visibility_status)
                VALUES (:tenant_id, :clean_company_id, 'new', 'ready', 'visible')
                RETURNING id
                """
            ),
            {"tenant_id": tenant_id, "clean_company_id": clean_company_id},
        )
    ).scalar_one()


async def _tenant_contact(conn, tenant_id: str, tenant_company_id: int) -> int:
    clean_company_id = (
        await conn.execute(
            text("SELECT clean_company_id FROM tenant_companies WHERE id = :id"),
            {"id": tenant_company_id},
        )
    ).scalar_one()
    clean_contact_id = (
        await conn.execute(
            text(
                """
                INSERT INTO clean_contacts (clean_company_id, name, position, email)
                VALUES (:clean_company_id, 'Hard Delete Buyer', 'Buyer', :email)
                RETURNING id
                """
            ),
            {"clean_company_id": clean_company_id, "email": f"buyer-{uuid4().hex[:8]}@example.com"},
        )
    ).scalar_one()
    return (
        await conn.execute(
            text(
                """
                INSERT INTO tenant_contacts
                  (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                VALUES (:tenant_id, :clean_contact_id, :clean_company_id, 'available', true)
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_contact_id": clean_contact_id,
                "clean_company_id": clean_company_id,
            },
        )
    ).scalar_one()


async def _group(
    conn,
    tenant_id: str,
    tenant_company_id: int,
    tenant_contact_id: int | None = None,
) -> str:
    group_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO groups (id, tenant_id, name, member_count)
            VALUES (:id, :tenant_id, :name, 1)
            """
        ),
        {"id": group_id, "tenant_id": tenant_id, "name": f"硬删除群组 {uuid4().hex[:8]}"},
    )
    await conn.execute(
        text(
            """
            INSERT INTO group_members
              (id, tenant_id, group_id, tenant_company_id, tenant_contact_id, added_by)
            VALUES (:id, :tenant_id, :group_id, :tenant_company_id, :tenant_contact_id, 'manual')
            """
        ),
        {
            "id": str(new_uuid()),
            "tenant_id": tenant_id,
            "group_id": group_id,
            "tenant_company_id": tenant_company_id,
            "tenant_contact_id": tenant_contact_id,
        },
    )
    return group_id


async def _template(conn, tenant_id: str) -> str:
    template_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO email_templates
              (id, tenant_id, name, category, subject, body_html, body_text)
            VALUES (:id, :tenant_id, '硬删除模板', 'outreach', 'Subject', '<p>Body</p>', 'Body')
            """
        ),
        {"id": template_id, "tenant_id": tenant_id},
    )
    return template_id


async def _domain(conn, tenant_id: str) -> str:
    domain_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO domain_warmup_status
              (id, tenant_id, domain, verification_status, daily_limit)
            VALUES (:id, :tenant_id, :domain, 'verified', 50)
            """
        ),
        {"id": domain_id, "tenant_id": tenant_id, "domain": f"{uuid4().hex}.example.com"},
    )
    return domain_id


async def _sending_runtime(
    conn,
    tenant_id: str,
    user_id: str,
    tenant_company_id: int,
    tenant_contact_id: int,
) -> str:
    plan_id = str(new_uuid())
    step_id = str(new_uuid())
    recipient_id = str(new_uuid())
    enrollment_id = str(new_uuid())
    lock_id = str(new_uuid())
    email_id = str(new_uuid())
    template_id = await _template(conn, tenant_id)
    domain_id = await _domain(conn, tenant_id)
    await conn.execute(
        text(
            """
            INSERT INTO sending_plans
              (id, tenant_id, created_by, name, status, recipient_source, recipient_config,
               send_strategy, sender_name, sender_email, domain_id)
            VALUES
              (:id, :tenant_id, :created_by, :name, 'running', 'manual', '{}'::jsonb,
               '{}'::jsonb, 'ClientGet', 'sender@example.com', :domain_id)
            """
        ),
        {
            "id": plan_id,
            "tenant_id": tenant_id,
            "created_by": user_id,
            "name": f"硬删除计划 {uuid4().hex[:8]}",
            "domain_id": domain_id,
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO sequence_steps
              (id, tenant_id, plan_id, step_number, template_id, delay_days, condition_type)
            VALUES (:id, :tenant_id, :plan_id, 1, :template_id, 0, 'always')
            """
        ),
        {"id": step_id, "tenant_id": tenant_id, "plan_id": plan_id, "template_id": template_id},
    )
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
              (id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id, status)
            VALUES (:id, :tenant_id, :plan_id, :plan_recipient_id, :tenant_contact_id, 'active')
            """
        ),
        {
            "id": enrollment_id,
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "plan_recipient_id": recipient_id,
            "tenant_contact_id": tenant_contact_id,
        },
    )
    await conn.execute(
        text(
            """
            INSERT INTO email_send_locks
              (id, tenant_id, enrollment_id, step_id, status, email_id, email_created_at)
            VALUES (:id, :tenant_id, :enrollment_id, :step_id, 'sent', :email_id, now())
            """
        ),
        {
            "id": lock_id,
            "tenant_id": tenant_id,
            "enrollment_id": enrollment_id,
            "step_id": step_id,
            "email_id": email_id,
        },
    )
    email_created_at = (
        await conn.execute(
            text(
                """
                INSERT INTO emails
                  (id, tenant_id, plan_id, step_id, step_number, template_id, enrollment_id,
                   tenant_contact_id, from_email, to_email, subject, body_html, status)
                VALUES
                  (:id, :tenant_id, :plan_id, :step_id, 1, :template_id, :enrollment_id,
                   :tenant_contact_id, 'sender@example.com', 'buyer@example.com',
                   'Subject', '<p>Body</p>', 'sent')
                RETURNING created_at
                """
            ),
            {
                "id": email_id,
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "step_id": step_id,
                "template_id": template_id,
                "enrollment_id": enrollment_id,
                "tenant_contact_id": tenant_contact_id,
            },
        )
    ).scalar_one()
    await conn.execute(
        text(
            """
            UPDATE email_send_locks
            SET email_created_at = :email_created_at
            WHERE id = :lock_id
            """
        ),
        {"email_created_at": email_created_at, "lock_id": lock_id},
    )
    await conn.execute(
        text(
            """
            INSERT INTO email_events (id, tenant_id, email_id, email_created_at, event_type)
            VALUES (:id, :tenant_id, :email_id, :email_created_at, 'sent')
            """
        ),
        {
            "id": str(new_uuid()),
            "tenant_id": tenant_id,
            "email_id": email_id,
            "email_created_at": email_created_at,
        },
    )
    return plan_id


async def _count(conn, table: str, tenant_id: str) -> int:
    return (
        await conn.execute(
            text(f"SELECT count(*) FROM {table} WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
    ).scalar_one()


async def _seed_cleanup_target(conn) -> tuple[str, str, str, int]:
    target_tenant_id, target_slug = await _tenant(conn, slug=TARGET_TENANT_SLUG, name="赵奎")
    await _reset_tenant_scope(conn, target_tenant_id)
    target_user_id = await _user(conn, target_tenant_id)
    muzi_company_id = await _tenant_company(conn, target_tenant_id, name="muzi", normalized="muzi")
    muzi_contact_id = await _tenant_contact(conn, target_tenant_id, muzi_company_id)
    await _group(conn, target_tenant_id, muzi_company_id, muzi_contact_id)
    await _sending_runtime(conn, target_tenant_id, target_user_id, muzi_company_id, muzi_contact_id)
    return target_tenant_id, target_slug, target_user_id, muzi_company_id


async def _reset_tenant_scope(conn, tenant_id: str) -> None:
    await conn.execute(
        text(
            """
            DELETE FROM email_events
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id},
    )
    for table in (
        "email_send_locks",
        "emails",
        "sequence_enrollments",
        "sending_plan_recipients",
        "sequence_steps",
        "sending_plans",
        "group_members",
        "groups",
        "company_scores",
        "scoring_jobs",
        "tenant_contacts",
        "tenant_companies",
    ):
        await conn.execute(
            text(f"DELETE FROM {table} WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )


async def test_dry_run_reports_counts_without_writing() -> None:
    engine = make_engine()
    service = TenantHardDeleteService()
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        target_tenant_id, target_slug, _, _ = await _seed_cleanup_target(conn)
        preview = await service.preview(conn, tenant_slug=target_slug)

        assert preview["tenant"]["id"] == target_tenant_id
        assert preview["muzi_candidates_count"] == 1
        assert preview["counts"]["tenant_companies"] == 1
        assert preview["counts"]["tenant_contacts"] == 1
        assert preview["counts"]["groups"] == 1
        assert preview["counts"]["group_members"] == 1
        assert preview["counts"]["sending_plans"] == 1
        assert preview["counts"]["emails"] == 1
        assert preview["counts"]["email_events"] == 1

        assert await _count(conn, "tenant_companies", target_tenant_id) == 1
        assert await _count(conn, "groups", target_tenant_id) == 1
        assert await _count(conn, "sending_plans", target_tenant_id) == 1
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def test_execute_deletes_only_target_tenant_rows_and_preserves_clean_data() -> None:
    engine = make_engine()
    service = TenantHardDeleteService()
    messaging = TenantMessagingService()
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        target_tenant_id, target_slug, target_user_id, _ = await _seed_cleanup_target(conn)
        other_tenant_id, _ = await _tenant(conn, name="其他租户")
        other_user_id = await _user(conn, other_tenant_id)
        other_company_id = await _tenant_company(
            conn,
            other_tenant_id,
            name="muzi",
            normalized="muzi",
        )
        other_contact_id = await _tenant_contact(conn, other_tenant_id, other_company_id)
        await _group(conn, other_tenant_id, other_company_id, other_contact_id)
        await _sending_runtime(
            conn,
            other_tenant_id,
            other_user_id,
            other_company_id,
            other_contact_id,
        )
        fuzzy_company_id = await _tenant_company(
            conn,
            target_tenant_id,
            name="muzi electronics",
            normalized="muzi-electronics",
        )

        result = await service.execute(conn, tenant_slug=target_slug, confirm=target_slug)

        assert result["verification"]["remaining"]["tenant_companies"] == 0
        assert result["verification"]["remaining"]["groups"] == 0
        assert result["verification"]["remaining"]["sending_plans"] == 0
        assert await _count(conn, "groups", target_tenant_id) == 0
        assert await _count(conn, "sending_plans", target_tenant_id) == 0
        assert await _count(conn, "emails", target_tenant_id) == 0
        assert await _count(conn, "email_events", target_tenant_id) == 0
        assert await _count(conn, "tenant_companies", other_tenant_id) == 1
        assert await _count(conn, "groups", other_tenant_id) == 1
        assert await _count(conn, "sending_plans", other_tenant_id) == 1
        assert (
            await conn.execute(text("SELECT count(*) FROM clean_companies WHERE name = 'muzi'"))
        ).scalar_one() >= 1
        with pytest.raises(AppError):
            await messaging.get_sending_plan(
                conn,
                target_tenant_id,
                result["deleted_plan_ids"][0],
            )
        fuzzy_exists = (
            await conn.execute(
                text("SELECT count(*) FROM tenant_companies WHERE id = :id"),
                {"id": fuzzy_company_id},
            )
        ).scalar_one()
        assert fuzzy_exists == 1

        template_id = await _template(conn, target_tenant_id)
        domain_id = await _domain(conn, target_tenant_id)
        new_company_id = await _tenant_company(conn, target_tenant_id, name="new target")
        new_contact_id = await _tenant_contact(conn, target_tenant_id, new_company_id)
        group_id = await _group(conn, target_tenant_id, new_company_id, new_contact_id)
        new_plan = await messaging.create_complete_sending_plan(
            conn,
            tenant_id=target_tenant_id,
            user_id=target_user_id,
            payload={
                "plan": {
                    "name": "清理后新计划",
                    "recipient_source": "group",
                    "recipient_config": {"group_id": group_id},
                    "sender_name": "ClientGet",
                    "sender_email": "sender@example.com",
                    "domain_id": domain_id,
                },
                "steps": [
                    {
                        "step_number": 1,
                        "template_id": template_id,
                        "delay_days": 0,
                        "condition_type": "always",
                    }
                ],
                "lock_recipients": False,
            },
        )
        assert new_plan["id"]
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def test_execute_requires_exact_confirmation_and_single_exact_muzi_candidate() -> None:
    engine = make_engine()
    service = TenantHardDeleteService()
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        target_tenant_id, target_slug, _, _ = await _seed_cleanup_target(conn)

        with pytest.raises(TenantHardDeleteError, match="确认 token"):
            await service.execute(conn, tenant_slug=target_slug, confirm="wrong")

        await _tenant_company(
            conn,
            target_tenant_id,
            name="MUZI",
            normalized="muzi",
            country_iso3="CAN",
        )
        with pytest.raises(TenantHardDeleteError, match="muzi"):
            await service.execute(conn, tenant_slug=target_slug, confirm=target_slug)
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def test_execute_allows_explicitly_confirmed_multiple_muzi_candidates() -> None:
    engine = make_engine()
    service = TenantHardDeleteService()
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        target_tenant_id, target_slug, _, first_company_id = await _seed_cleanup_target(conn)
        second_company_id = await _tenant_company(
            conn,
            target_tenant_id,
            name="MUZI",
            normalized="muzi",
            country_iso3="CAN",
        )

        with pytest.raises(TenantHardDeleteError, match="候选"):
            await service.execute(
                conn,
                tenant_slug=target_slug,
                confirm=target_slug,
                confirmed_company_ids=[first_company_id],
            )

        result = await service.execute(
            conn,
            tenant_slug=target_slug,
            confirm=target_slug,
            confirmed_company_ids=[first_company_id, second_company_id],
        )

        assert sorted(result["deleted_tenant_company_ids"]) == sorted(
            [first_company_id, second_company_id]
        )
        assert result["verification"]["remaining"]["tenant_companies"] == 0
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()
