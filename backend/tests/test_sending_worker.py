import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.integrations.engagelab import EngageLabClient, EngageLabSendError
from app.services.tenant_messaging_service import TenantMessagingService
from app.workers.sending import SendingWorker


def _settings() -> Settings:
    return Settings(
        JWT_SECRET="test-secret",
        ADMIN_EMAIL="admin@example.com",
        ADMIN_PASSWORD="password",
        DATA_SOURCE_ENCRYPTION_KEY="test-encryption-key-0123456789abcdef",
        INTERNAL_SERVICE_SECRET="internal-secret",
        ENGAGELAB_WEBHOOK_SECRET="webhook-secret",
        ENGAGELAB_BASE_URL="https://provider.example",
        ENGAGELAB_API_USER="user",
        ENGAGELAB_CREDENTIAL="credential",
    )


def _result(*, first=None, all_rows=None):
    mappings = MagicMock()
    mappings.first.return_value = first
    mappings.all.return_value = all_rows or []
    result = MagicMock()
    result.mappings.return_value = mappings
    return result


class _Begin:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Engine:
    def begin(self):
        return _Begin()


class _Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 5, 30, 8, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class _Provider:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.payloads = []

    async def send_email(self, payload):
        self.payloads.append(payload)
        if self.error:
            raise self.error
        return {"engagelab_message_id": "msg-001"}


class _Service:
    def __init__(self, *, domains=None, items=None) -> None:
        self.domains = ["domain-a"] if domains is None else domains
        self.items = items if items is not None else [_claimed_item("domain-a")]
        self.failed_payloads = []
        self.sent_payloads = []
        self.recover_calls = 0
        self.claim_calls = []

    async def recover_stale_locks(self, conn):
        self.recover_calls += 1
        return {"recovered_count": 0, "enrollment_ids": []}

    async def list_running_domain_ids(self, conn):
        return self.domains

    async def load_timezone_config(self, conn):
        return {}

    async def claim_due_emails(self, conn, **kwargs):
        self.claim_calls.append(kwargs)
        return {"items": self.items}

    async def mark_email_sent(self, conn, *, email_id, payload):
        self.sent_payloads.append(payload)
        return {"email_id": email_id, "status": "sent"}

    async def mark_email_failed(self, conn, *, email_id, payload):
        self.failed_payloads.append(payload)
        return {"email_id": email_id, "status": "retry_scheduled", "send_attempt_count": 1}


def _claimed_item(domain_id: str) -> dict:
    return {
        "email_id": "email-001",
        "tenant_id": "tenant-001",
        "enrollment_id": "enrollment-001",
        "plan_id": "plan-001",
        "step_id": "step-001",
        "domain_id": domain_id,
        "send_strategy": {"interval_seconds": [30, 120]},
        "tenant_contact_id": "contact-001",
        "from_email": "sales@example.com",
        "from_name": "Sales",
        "to_email": "buyer@example.com",
        "to_name": "Buyer",
        "subject": "Hello",
        "body_html": "<p>Hello</p>",
        "body_text": "Hello",
    }


@pytest.mark.asyncio
async def test_engagelab_error_carries_status_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "temporary"})

    client = EngageLabClient(settings=_settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(EngageLabSendError) as exc_info:
        await client.send_email(
            {
                "from_email": "sales@example.com",
                "to_email": "buyer@example.com",
                "subject": "Hello",
                "body_html": "<p>Hello</p>",
            }
        )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_engagelab_request_body_includes_idempotency_key():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["idempotency_key"] == "enrollment-001:step-001"
        return httpx.Response(200, json={"message_id": "msg-001"})

    client = EngageLabClient(settings=_settings(), transport=httpx.MockTransport(handler))

    result = await client.send_email(
        {
            "from_email": "sales@example.com",
            "to_email": "buyer@example.com",
            "subject": "Hello",
            "body_html": "<p>Hello</p>",
            "idempotency_key": "enrollment-001:step-001",
        }
    )

    assert result["engagelab_message_id"] == "msg-001"


@pytest.mark.asyncio
async def test_worker_sends_one_email_and_sets_domain_clock():
    clock = _Clock()
    logs = []
    service = _Service(domains=["domain-a"], items=[_claimed_item("domain-a")])
    provider = _Provider()
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 45,
        log_sink=logs.append,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert result["claimed_count"] == 1
    assert service.claim_calls[0]["limit"] == 1
    assert service.claim_calls[0]["domain_id"] == "domain-a"
    assert provider.payloads[0]["idempotency_key"] == "enrollment-001:step-001"
    assert worker.domain_clocks["domain-a"] == clock.value + timedelta(seconds=45)
    assert logs[-1]["event"] == "send_ok"


@pytest.mark.asyncio
async def test_worker_rotates_to_due_second_domain_while_first_cools_down():
    clock = _Clock()
    service = _Service(domains=["domain-a", "domain-b"], items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 60,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")
    service.items = [_claimed_item("domain-b")]
    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.claim_calls[0]["domain_id"] == "domain-a"
    assert service.claim_calls[1]["domain_id"] == "domain-b"


@pytest.mark.asyncio
async def test_worker_sleeps_when_all_domains_are_cooling_down():
    clock = _Clock()
    sleep = AsyncMock()
    service = _Service(domains=["domain-a"], items=[])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        clock=clock,
        sleep=sleep,
        log_sink=lambda record: None,
    )
    worker.domain_clocks["domain-a"] = clock.value + timedelta(seconds=30)

    result = await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=5)

    assert result["processed_count"] == 0
    sleep.assert_awaited_once_with(5)
    assert service.claim_calls == []


@pytest.mark.asyncio
async def test_worker_sleeps_when_no_domains_are_running():
    sleep = AsyncMock()
    service = _Service(domains=[], items=[])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        sleep=sleep,
        log_sink=lambda record: None,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=5)

    assert result["processed_count"] == 0
    sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_worker_treats_401_as_temporary_failure():
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("auth", status_code=401)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 30,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.failed_payloads[0]["is_permanent"] is False
    assert service.failed_payloads[0]["status_code"] == 401
    assert service.failed_payloads[0]["error_category"] is None


@pytest.mark.asyncio
async def test_worker_treats_422_as_invalid_permanent_failure():
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("invalid", status_code=422)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 30,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.failed_payloads[0]["is_permanent"] is True
    assert service.failed_payloads[0]["error_category"] == "invalid"


@pytest.mark.asyncio
async def test_worker_recovers_stale_locks_only_once():
    service = _Service(items=[])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        sleep=AsyncMock(),
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")
    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.recover_calls == 1


@pytest.mark.asyncio
async def test_mark_email_failed_schedules_incremental_retry():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result(first={"send_attempt_count": 0}))

    with patch.object(
        svc,
        "_load_email",
        new_callable=AsyncMock,
        return_value={
            "id": "email-001",
            "created_at": datetime.now(UTC),
            "enrollment_id": "enrollment-001",
            "tenant_contact_id": "contact-001",
            "plan_id": "plan-001",
        },
    ), patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock):
        result = await svc.mark_email_failed(
            conn,
            email_id="email-001",
            payload={"domain_id": "domain-a", "reason": "timeout"},
        )

    assert result["status"] == "retry_scheduled"
    assert result["send_attempt_count"] == 1
    assert result["retry_seconds"] == 15 * 60


@pytest.mark.asyncio
async def test_mark_email_failed_exhausts_after_fourth_temporary_failure():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result(first={"send_attempt_count": 3}))

    with patch.object(
        svc,
        "_load_email",
        new_callable=AsyncMock,
        return_value={
            "id": "email-001",
            "created_at": datetime.now(UTC),
            "enrollment_id": "enrollment-001",
            "tenant_contact_id": "contact-001",
            "plan_id": "plan-001",
        },
    ), patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock):
        result = await svc.mark_email_failed(
            conn,
            email_id="email-001",
            payload={"domain_id": "domain-a", "reason": "timeout"},
        )

    assert result["status"] == "failed"
    assert result["send_attempt_count"] == 4


@pytest.mark.asyncio
async def test_mark_email_failed_updates_invalid_contact_for_422():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result(first={"send_attempt_count": 0}))

    with patch.object(
        svc,
        "_load_email",
        new_callable=AsyncMock,
        return_value={
            "id": "email-001",
            "created_at": datetime.now(UTC),
            "enrollment_id": "enrollment-001",
            "tenant_contact_id": "contact-001",
            "plan_id": "plan-001",
        },
    ), patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock), patch.object(
        svc, "_update_contact_for_permanent_failure", new_callable=AsyncMock
    ) as update_contact:
        result = await svc.mark_email_failed(
            conn,
            email_id="email-001",
            payload={
                "domain_id": "domain-a",
                "reason": "invalid",
                "is_permanent": True,
                "status_code": 422,
                "error_category": "invalid",
            },
        )

    assert result["status"] == "failed"
    update_contact.assert_awaited_once()
    assert update_contact.await_args.kwargs["status_code"] == 422
    assert update_contact.await_args.kwargs["error_category"] == "invalid"


@pytest.mark.asyncio
async def test_mark_email_sent_resets_attempt_count_when_advancing():
    svc = TenantMessagingService()
    conn = AsyncMock()
    next_step = {"step_number": 2, "delay_days": 1}
    conn.execute = AsyncMock(
        side_effect=[
            MagicMock(),
            MagicMock(),
            MagicMock(),
            _result(first=next_step),
            MagicMock(),
            MagicMock(),
        ]
    )

    with patch.object(
        svc,
        "_load_email",
        new_callable=AsyncMock,
        return_value={
            "id": "email-001",
            "created_at": datetime.now(UTC),
            "plan_id": "plan-001",
            "step_number": 1,
            "tenant_contact_id": "contact-001",
            "enrollment_id": "enrollment-001",
        },
    ):
        await svc.mark_email_sent(
            conn,
            email_id="email-001",
            payload={"engagelab_message_id": "msg-001"},
        )

    sql_texts = "\n".join(str(call.args[0]) for call in conn.execute.call_args_list)
    assert "send_attempt_count = 0" in sql_texts


@pytest.mark.asyncio
async def test_claim_due_emails_uses_domain_filter_and_skips_blocking_candidate():
    svc = TenantMessagingService()
    conn = AsyncMock()
    rows = [
        _claim_row("enrollment-blocked", "blocked@example.com"),
        _claim_row("enrollment-ready", "ready@example.com"),
    ]
    conn.execute = AsyncMock(
        side_effect=[
            _result(all_rows=rows),
            _result(first={"id": "lock-001"}),
            MagicMock(),
            MagicMock(),
        ]
    )

    with patch.object(
        svc,
        "_step_condition_satisfied",
        new_callable=AsyncMock,
        side_effect=[False, True],
    ), patch.object(svc, "reserve_domain_quota", new_callable=AsyncMock):
        result = await svc.claim_due_emails(
            conn,
            service_instance="worker-1",
            limit=1,
            domain_id="11111111-1111-1111-1111-111111111111",
            timezone_config={"rules": {}, "default_rule": None, "countries": {}, "holidays": set()},
        )

    first_params = conn.execute.call_args_list[0].args[1]
    assert first_params["domain_id"] == "11111111-1111-1111-1111-111111111111"
    assert first_params["candidate_limit"] == 20
    assert result["items"][0]["enrollment_id"] == "enrollment-ready"
    assert result["items"][0]["domain_id"] == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_recover_stale_locks_releases_quota_without_email_id():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(
        return_value=_result(
            all_rows=[
                {
                    "enrollment_id": "enrollment-001",
                    "email_id": None,
                    "plan_id": "plan-001",
                }
            ]
        )
    )

    with patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock) as release_quota:
        result = await svc.recover_stale_locks(conn)

    assert result == {"recovered_count": 1, "enrollment_ids": ["enrollment-001"]}
    release_quota.assert_awaited_once()
    assert release_quota.await_args.kwargs["plan_id"] == "plan-001"


def _claim_row(enrollment_id: str, to_email: str) -> dict:
    return {
        "enrollment_id": enrollment_id,
        "plan_id": "plan-001",
        "plan_recipient_id": "recipient-001",
        "tenant_id": "tenant-001",
        "tenant_contact_id": "contact-001",
        "current_step": 1,
        "next_step_due_at": datetime.now(UTC),
        "domain_id": "11111111-1111-1111-1111-111111111111",
        "send_strategy": {"interval_seconds": [30, 120]},
        "sender_name": "Sales",
        "sender_email": "sales@example.com",
        "step_id": "step-001",
        "step_number": 1,
        "template_id": "template-001",
        "condition_type": "always",
        "delay_days": 0,
        "tenant_company_id": "company-001",
        "company_name": "Example",
        "country_iso3": None,
        "contact_name": "Buyer",
        "to_email": to_email,
        "subject": "Hello {{ company_name }}",
        "body_html": "<p>Hello {{ contact_name }}</p>",
        "body_text": "Hello {{ contact_name }}",
    }
