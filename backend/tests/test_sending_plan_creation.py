from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.main import create_app
from app.services.tenant_messaging_service import TenantMessagingService
from tests.helpers import make_engine


async def _tenant(conn) -> str:
    tenant_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"tenant_id": tenant_id, "slug": f"send-plan-{uuid4().hex[:8]}"},
    )
    return tenant_id


async def _user(conn, tenant_id: str) -> str:
    user_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
            VALUES (:user_id, :tenant_id, :email, 'hash', '发送计划用户', 'active', false)
            """
        ),
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": f"send-plan-{uuid4().hex[:8]}@example.com",
        },
    )
    return user_id


async def _template(conn, tenant_id: str) -> str:
    template_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO email_templates
              (id, tenant_id, name, category, subject, body_html, body_text)
            VALUES
              (:id, :tenant_id, '首封模板', 'outreach', 'Subject', '<p>Body</p>', 'Body')
            """
        ),
        {"id": template_id, "tenant_id": tenant_id},
    )
    return template_id


async def _domain(conn, tenant_id: str, *, status: str = "verified", daily_limit: int = 50) -> str:
    domain_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO domain_warmup_status
              (id, tenant_id, domain, verification_status, daily_limit)
            VALUES
              (:id, :tenant_id, :domain, :status, :daily_limit)
            """
        ),
        {
            "id": domain_id,
            "tenant_id": tenant_id,
            "domain": f"{status}-{uuid4().hex[:8]}.example.com",
            "status": status,
            "daily_limit": daily_limit,
        },
    )
    return domain_id


async def _tenant_company_with_contact(
    conn,
    tenant_id: str,
    *,
    data_status: str = "ready",
    contact_status: str = "available",
    email: str | None = None,
) -> tuple[int, int]:
    clean_company_id = (
        await conn.execute(
            text(
                """
                INSERT INTO clean_companies (name, name_normalized, country_iso3, website)
                VALUES (:name, :name_normalized, 'USA', :website)
                RETURNING id
                """
            ),
            {
                "name": f"Send Plan Company {uuid4().hex}",
                "name_normalized": f"send-plan-company-{uuid4().hex}",
                "website": f"https://{uuid4().hex}.example.com",
            },
        )
    ).scalar_one()
    tenant_company_id = (
        await conn.execute(
            text(
                """
                INSERT INTO tenant_companies
                  (tenant_id, clean_company_id, business_status, data_status, visibility_status)
                VALUES
                  (:tenant_id, :clean_company_id, 'new', :data_status, 'visible')
                RETURNING id
                """
            ),
            {"tenant_id": tenant_id, "clean_company_id": clean_company_id, "data_status": data_status},
        )
    ).scalar_one()
    clean_contact_id = (
        await conn.execute(
            text(
                """
                INSERT INTO clean_contacts (clean_company_id, name, position, email)
                VALUES (:clean_company_id, 'Ada Buyer', 'Procurement', :email)
                RETURNING id
                """
            ),
            {"clean_company_id": clean_company_id, "email": email or f"ada-{uuid4().hex[:8]}@example.com"},
        )
    ).scalar_one()
    tenant_contact_id = (
        await conn.execute(
            text(
                """
                INSERT INTO tenant_contacts
                  (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                VALUES
                  (:tenant_id, :clean_contact_id, :clean_company_id, :contact_status, true)
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_contact_id": clean_contact_id,
                "clean_company_id": clean_company_id,
                "contact_status": contact_status,
            },
        )
    ).scalar_one()
    return tenant_company_id, tenant_contact_id


async def _group(conn, tenant_id: str, tenant_company_id: int, tenant_contact_id: int | None = None) -> str:
    group_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO groups (id, tenant_id, name, member_count)
            VALUES (:id, :tenant_id, :name, 1)
            """
        ),
        {"id": group_id, "tenant_id": tenant_id, "name": f"发送计划组 {uuid4().hex[:8]}"},
    )
    await conn.execute(
        text(
            """
            INSERT INTO group_members
              (id, tenant_id, group_id, tenant_company_id, tenant_contact_id, added_by)
            VALUES
              (:id, :tenant_id, :group_id, :tenant_company_id, :tenant_contact_id, 'manual')
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
    await conn.execute(
        text(
            """
            UPDATE tenant_companies
            SET business_status = 'in_group'
            WHERE tenant_id = :tenant_id AND id = :tenant_company_id
            """
        ),
        {"tenant_id": tenant_id, "tenant_company_id": tenant_company_id},
    )
    return group_id


def _payload(*, group_id: str, template_id: str, domain_id: str, lock_recipients: bool) -> dict:
    return {
        "plan": {
            "name": f"发送计划 {uuid4().hex[:8]}",
            "description": "TDD sending plan",
            "recipient_source": "group",
            "recipient_config": {"group_id": group_id},
            "send_strategy": {"timezone_aware": True, "preferred_hours": [9, 17]},
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
        "lock_recipients": lock_recipients,
    }


async def _counts(conn, tenant_id: str) -> dict[str, int]:
    return {
        "plans": (
            await conn.execute(text("SELECT count(*) FROM sending_plans WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        ).scalar_one(),
        "steps": (
            await conn.execute(text("SELECT count(*) FROM sequence_steps WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        ).scalar_one(),
        "recipients": (
            await conn.execute(text("SELECT count(*) FROM sending_plan_recipients WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        ).scalar_one(),
    }


async def test_complete_creation_allows_draft_with_unverified_domain_without_changing_company_status() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="pending")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)

            plan = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=_payload(
                    group_id=group_id,
                    template_id=template_id,
                    domain_id=domain_id,
                    lock_recipients=False,
                ),
            )

            steps = await service.list_plan_steps(conn, tenant_id, plan["id"])
            counts = await _counts(conn, tenant_id)
            business_status = (
                await conn.execute(
                    text("SELECT business_status FROM tenant_companies WHERE id = :id"),
                    {"id": tenant_company_id},
                )
            ).scalar_one()

        assert plan["status"] == "draft"
        assert plan["domain_id"] == domain_id
        assert [step["step_number"] for step in steps] == [1]
        assert counts == {"plans": 1, "steps": 1, "recipients": 0}
        assert business_status == "in_group"
    finally:
        await engine.dispose()


async def test_complete_creation_locks_verified_domain_recipients() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="verified")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)

            plan = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=_payload(
                    group_id=group_id,
                    template_id=template_id,
                    domain_id=domain_id,
                    lock_recipients=True,
                ),
            )

            recipients = await service.list_plan_recipients(conn, tenant_id, plan["id"])
            counts = await _counts(conn, tenant_id)

        assert plan["total_recipients"] == 1
        assert len(recipients) == 1
        assert recipients[0]["tenant_contact_id"] == str(tenant_contact_id)
        assert counts == {"plans": 1, "steps": 1, "recipients": 1}
    finally:
        await engine.dispose()


async def test_start_plan_rejects_unverified_domain_with_actionable_message() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="pending")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)
            plan = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=_payload(
                    group_id=group_id,
                    template_id=template_id,
                    domain_id=domain_id,
                    lock_recipients=False,
                ),
            )

            with pytest.raises(AppError) as error:
                await service.start_plan(
                    conn,
                    tenant_id=tenant_id,
                    plan_id=plan["id"],
                    user_id=user_id,
                )

        assert error.value.status_code == 422
        assert error.value.code == "VALIDATION_ERROR"
        assert "发送域名未验证" in error.value.message
    finally:
        await engine.dispose()


async def test_start_plan_with_verified_domain_creates_active_enrollment() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="verified")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)
            plan = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=_payload(
                    group_id=group_id,
                    template_id=template_id,
                    domain_id=domain_id,
                    lock_recipients=True,
                ),
            )

            started = await service.start_plan(
                conn,
                tenant_id=tenant_id,
                plan_id=plan["id"],
                user_id=user_id,
            )
            enrollment = (
                await conn.execute(
                    text(
                        """
                        SELECT status, current_step
                        FROM sequence_enrollments
                        WHERE tenant_id = :tenant_id AND plan_id = :plan_id
                        """
                    ),
                    {"tenant_id": tenant_id, "plan_id": plan["id"]},
                )
            ).mappings().one()

        assert started["status"] == "running"
        assert enrollment["status"] == "active"
        assert enrollment["current_step"] == 1
    finally:
        await engine.dispose()


async def test_claim_due_email_quota_failure_does_not_leave_blocking_lock() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="verified", daily_limit=0)
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)
            plan = await service.create_complete_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=_payload(
                    group_id=group_id,
                    template_id=template_id,
                    domain_id=domain_id,
                    lock_recipients=True,
                ),
            )
            await service.start_plan(
                conn,
                tenant_id=tenant_id,
                plan_id=plan["id"],
                user_id=user_id,
            )
            await conn.execute(
                text(
                    """
                    UPDATE sequence_enrollments
                    SET next_step_due_at = now() - interval '1 minute'
                    WHERE tenant_id = :tenant_id AND plan_id = :plan_id
                    """
                ),
                {"tenant_id": tenant_id, "plan_id": plan["id"]},
            )

        with pytest.raises(AppError) as error:
            async with engine.begin() as conn:
                await service.claim_due_emails(
                    conn,
                    service_instance="quota-test-worker",
                    limit=1,
                )

        async with engine.begin() as conn:
            lock_count = (
                await conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM email_send_locks l
                        JOIN sequence_enrollments e ON e.id = l.enrollment_id
                        WHERE e.plan_id = :plan_id
                        """
                    ),
                    {"plan_id": plan["id"]},
                )
            ).scalar_one()

        assert error.value.code == "QUOTA_EXCEEDED"
        assert lock_count == 0
    finally:
        await engine.dispose()


async def test_complete_creation_rejects_lock_with_unverified_domain_without_partial_data() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="pending")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)

            with pytest.raises(AppError) as error:
                await service.create_complete_sending_plan(
                    conn,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    payload=_payload(
                        group_id=group_id,
                        template_id=template_id,
                        domain_id=domain_id,
                        lock_recipients=True,
                    ),
                )
            counts = await _counts(conn, tenant_id)

        assert error.value.status_code == 422
        assert error.value.code == "VALIDATION_ERROR"
        assert "域名" in error.value.message
        assert counts == {"plans": 0, "steps": 0, "recipients": 0}
    finally:
        await engine.dispose()


async def test_complete_creation_rejects_zero_eligible_recipients_without_partial_data() -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="verified")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(
                conn,
                tenant_id,
                data_status="missing_contacts",
            )
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)

            with pytest.raises(AppError) as error:
                await service.create_complete_sending_plan(
                    conn,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    payload=_payload(
                        group_id=group_id,
                        template_id=template_id,
                        domain_id=domain_id,
                        lock_recipients=True,
                    ),
                )
            counts = await _counts(conn, tenant_id)

        assert error.value.status_code == 422
        assert error.value.code == "VALIDATION_ERROR"
        assert "可发送收件人" in error.value.message
        assert counts == {"plans": 0, "steps": 0, "recipients": 0}
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    ("mutate", "message_part"),
    [
        (lambda payload: payload["plan"].pop("name"), "名称"),
        (lambda payload: payload["steps"].__setitem__(0, {**payload["steps"][0], "delay_days": 1}), "第一步"),
        (lambda payload: payload["steps"].__setitem__(0, {**payload["steps"][0], "template_id": str(new_uuid())}), "模板"),
        (lambda payload: payload["plan"].__setitem__("domain_id", str(new_uuid())), "域名"),
        (lambda payload: payload["plan"]["recipient_config"].__setitem__("group_id", str(new_uuid())), "分组"),
    ],
)
async def test_complete_creation_rejects_invalid_inputs_before_persistence(mutate, message_part: str) -> None:
    engine = make_engine()
    service = TenantMessagingService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn)
            user_id = await _user(conn, tenant_id)
            template_id = await _template(conn, tenant_id)
            domain_id = await _domain(conn, tenant_id, status="verified")
            tenant_company_id, tenant_contact_id = await _tenant_company_with_contact(conn, tenant_id)
            group_id = await _group(conn, tenant_id, tenant_company_id, tenant_contact_id)
            payload = _payload(
                group_id=group_id,
                template_id=template_id,
                domain_id=domain_id,
                lock_recipients=False,
            )
            mutate(payload)

            with pytest.raises(AppError) as error:
                await service.create_complete_sending_plan(
                    conn,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    payload=payload,
                )
            counts = await _counts(conn, tenant_id)

        assert error.value.status_code == 422
        assert error.value.code == "VALIDATION_ERROR"
        assert message_part in error.value.message
        assert counts == {"plans": 0, "steps": 0, "recipients": 0}
    finally:
        await engine.dispose()


def test_complete_create_route_is_registered_before_dynamic_plan_route() -> None:
    app = create_app()
    paths = [
        getattr(route, "path", "")
        for route in app.router.routes
        if "POST" in getattr(route, "methods", set())
    ]

    complete_create = "/t/{slug}/api/v1/sending-plans/complete-create"
    dynamic_create = "/t/{slug}/api/v1/sending-plans/{plan_id}/steps"

    assert complete_create in paths
    assert paths.index(complete_create) < paths.index(dynamic_create)
