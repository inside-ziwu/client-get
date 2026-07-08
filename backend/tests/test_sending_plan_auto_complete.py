from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sending_plan_completion import complete_running_plan_if_finished
from app.services.email_reconciliation_service import EmailReconciliationService
from app.services.tenant_messaging_service import TenantMessagingService
from app.services.webhook_service import WebhookService


class _Result:
    def __init__(self, row=None):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


@pytest.mark.asyncio
async def test_complete_running_plan_if_finished_requires_no_active_or_paused_enrollments():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_Result({"id": "plan-001"}))

    completed = await complete_running_plan_if_finished(conn, plan_id="plan-001")

    assert completed is True
    sql = str(conn.execute.await_args.args[0])
    params = conn.execute.await_args.args[1]
    assert "sp.status = 'running'" in sql
    assert "EXISTS" in sql
    assert "NOT EXISTS" in sql
    assert "se.status IN ('active', 'paused')" in sql
    assert "status = 'completed'" in sql
    assert "completed_at = COALESCE(sp.completed_at, now())" in sql
    assert "updated_at = now()" in sql
    assert params == {"plan_id": "plan-001"}


@pytest.mark.asyncio
async def test_complete_running_plan_if_finished_returns_false_when_no_update():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_Result(None))

    completed = await complete_running_plan_if_finished(conn, plan_id="plan-001")

    assert completed is False


def _query_result(first=None, all_rows=None):
    result = MagicMock()
    result.mappings.return_value.first.return_value = first
    result.mappings.return_value.all.return_value = all_rows or []
    return result


def _email_row(**overrides):
    row = {
        "id": "email-001",
        "created_at": datetime.now(UTC),
        "plan_id": "plan-001",
        "step_number": 2,
        "tenant_contact_id": "contact-001",
        "enrollment_id": "enrollment-001",
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_mark_email_sent_checks_plan_completion_after_last_step():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(),
            MagicMock(),
            _query_result(first=None),
            MagicMock(),
            MagicMock(),
        ]
    )

    with (
        patch.object(svc, "_load_email", new_callable=AsyncMock, return_value=_email_row()),
        patch(
            "app.services.tenant_messaging_service.complete_running_plan_if_finished",
            new_callable=AsyncMock,
            return_value=True,
        ) as complete_plan,
    ):
        await svc.mark_email_sent(
            conn,
            email_id="email-001",
            payload={"engagelab_message_id": "msg-001"},
        )

    complete_plan.assert_awaited_once_with(conn, plan_id="plan-001")


@pytest.mark.asyncio
async def test_mark_email_sent_does_not_check_plan_completion_when_next_step_exists():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(),
            MagicMock(),
            _query_result(first={"step_number": 3, "delay_days": 1}),
            MagicMock(),
            MagicMock(),
        ]
    )

    with (
        patch.object(svc, "_load_email", new_callable=AsyncMock, return_value=_email_row()),
        patch(
            "app.services.tenant_messaging_service.complete_running_plan_if_finished",
            new_callable=AsyncMock,
            return_value=True,
        ) as complete_plan,
    ):
        await svc.mark_email_sent(
            conn,
            email_id="email-001",
            payload={"engagelab_message_id": "msg-001"},
        )

    complete_plan.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_email_failed_checks_plan_completion_for_permanent_failure():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(),
            _query_result(first={"send_attempt_count": 0}),
            MagicMock(),
        ]
    )

    with (
        patch.object(svc, "_load_email", new_callable=AsyncMock, return_value=_email_row()),
        patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock),
        patch.object(svc, "_update_contact_for_permanent_failure", new_callable=AsyncMock),
        patch(
            "app.services.tenant_messaging_service.complete_running_plan_if_finished",
            new_callable=AsyncMock,
            return_value=True,
        ) as complete_plan,
    ):
        result = await svc.mark_email_failed(
            conn,
            email_id="email-001",
            payload={"is_permanent": True, "domain_id": "domain-001", "status_code": 422},
        )

    assert result["status"] == "failed"
    complete_plan.assert_awaited_once_with(conn, plan_id="plan-001")


@pytest.mark.asyncio
async def test_mark_email_failed_checks_plan_completion_when_retries_are_exhausted():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(),
            _query_result(first={"send_attempt_count": len(svc.RETRY_DELAYS)}),
            MagicMock(),
        ]
    )

    with (
        patch.object(svc, "_load_email", new_callable=AsyncMock, return_value=_email_row()),
        patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock),
        patch.object(svc, "_update_contact_for_permanent_failure", new_callable=AsyncMock),
        patch(
            "app.services.tenant_messaging_service.complete_running_plan_if_finished",
            new_callable=AsyncMock,
            return_value=True,
        ) as complete_plan,
    ):
        result = await svc.mark_email_failed(
            conn,
            email_id="email-001",
            payload={"is_permanent": False, "domain_id": "domain-001"},
        )

    assert result["status"] == "failed"
    complete_plan.assert_awaited_once_with(conn, plan_id="plan-001")


@pytest.mark.asyncio
async def test_mark_email_failed_does_not_check_plan_completion_when_retry_is_scheduled():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(),
            _query_result(first={"send_attempt_count": 0}),
            MagicMock(),
        ]
    )

    with (
        patch.object(svc, "_load_email", new_callable=AsyncMock, return_value=_email_row()),
        patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock),
        patch.object(svc, "_update_contact_for_permanent_failure", new_callable=AsyncMock),
        patch(
            "app.services.tenant_messaging_service.complete_running_plan_if_finished",
            new_callable=AsyncMock,
            return_value=True,
        ) as complete_plan,
    ):
        result = await svc.mark_email_failed(
            conn,
            email_id="email-001",
            payload={"is_permanent": False, "domain_id": "domain-001"},
        )

    assert result["status"] == "retry_scheduled"
    complete_plan.assert_not_awaited()


def _webhook_email_row(**overrides):
    row = {
        "id": "email-001",
        "created_at": datetime.now(UTC),
        "tenant_id": "tenant-001",
        "plan_id": "plan-001",
        "enrollment_id": "enrollment-001",
        "tenant_contact_id": "contact-001",
        "to_email": "buyer@example.com",
        "status": "sent",
        "open_count": 0,
        "first_opened_at": None,
    }
    row.update(overrides)
    return row


def _webhook_payload(raw_event: str) -> dict:
    return {
        "itime": 1760000000000,
        "response": {
            "event": raw_event,
            "response_data": {"email_id": "msg-001"},
        },
    }


@pytest.mark.asyncio
async def test_webhook_terminal_event_checks_plan_completion():
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            _query_result(first=_webhook_email_row()),
            _query_result(first={"id": "event-001"}),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
    )

    with patch(
        "app.services.webhook_service.complete_running_plan_if_finished",
        new_callable=AsyncMock,
        return_value=True,
    ) as complete_plan:
        result = await WebhookService().process_engagelab_event(
            conn,
            _webhook_payload("unsubscribe"),
        )

    first_sql = str(conn.execute.await_args_list[0].args[0])
    assert "plan_id" in first_sql
    assert result["status"] == "processed"
    complete_plan.assert_awaited_once_with(conn, plan_id="plan-001")


@pytest.mark.asyncio
async def test_webhook_non_terminal_event_does_not_check_plan_completion():
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            _query_result(first=_webhook_email_row()),
            _query_result(first={"id": "event-001"}),
            MagicMock(),
            MagicMock(),
        ]
    )

    with patch(
        "app.services.webhook_service.complete_running_plan_if_finished",
        new_callable=AsyncMock,
        return_value=True,
    ) as complete_plan:
        result = await WebhookService().process_engagelab_event(
            conn,
            {
                "itime": 1760000000000,
                "status": {
                    "message_status": "delivered",
                    "status_data": {"email_id": "msg-001"},
                },
            },
        )

    assert result["status"] == "processed"
    complete_plan.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconciliation_bounce_checks_plan_completion():
    svc = EmailReconciliationService()
    conn = AsyncMock()
    sent_at = datetime(2026, 7, 8, 8, 0, tzinfo=UTC)
    conn.execute = AsyncMock(
        side_effect=[
            _query_result(
                all_rows=[
                    {
                        "id": "email-001",
                        "created_at": datetime.now(UTC),
                        "sent_at": sent_at,
                        "tenant_id": "tenant-001",
                        "plan_id": "plan-001",
                        "enrollment_id": "enrollment-001",
                        "tenant_contact_id": "contact-001",
                        "to_email": "buyer@example.com",
                        "engagelab_message_id": "msg-001",
                    }
                ]
            ),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
    )
    client = MagicMock()
    client.query_email_status = AsyncMock(
        return_value=[
            {
                "email_id": "msg-001",
                "status": 4,
                "update_time": "2026-07-08T09:00:00Z",
            }
        ]
    )

    with (
        patch(
            "app.services.email_reconciliation_service.get_settings",
            return_value=MagicMock(instance_id="instance-001"),
        ),
        patch(
            "app.services.email_reconciliation_service.complete_running_plan_if_finished",
            new_callable=AsyncMock,
            return_value=True,
        ) as complete_plan,
    ):
        result = await svc.reconcile_once(conn, client)

    first_sql = str(conn.execute.await_args_list[0].args[0])
    assert "e.plan_id" in first_sql
    assert result["bounced_invalid"] == 1
    complete_plan.assert_awaited_once_with(conn, plan_id="plan-001")


def test_backfill_migration_completes_finished_running_plans():
    migration = Path("alembic/versions/20260708_0002_complete_finished_sending_plans.py")
    sql = migration.read_text()

    assert "UPDATE sending_plans sp" in sql
    assert "SET status = 'completed'" in sql
    assert "completed_at = COALESCE(sp.completed_at, now())" in sql
    assert "sp.status = 'running'" in sql
    assert "EXISTS" in sql
    assert "NOT EXISTS" in sql
    assert "se.status IN ('active', 'paused')" in sql
    assert "UPDATE sequence_enrollments" not in sql
