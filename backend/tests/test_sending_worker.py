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
        self.deferred_payloads = []
        self.sent_payloads = []
        self.recover_calls = 0
        self.claim_calls = []
        self.defer_error: Exception | None = None
        self.fail_error: Exception | None = None
        self.failed_status = "retry_scheduled"

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
        if self.fail_error:
            raise self.fail_error
        self.failed_payloads.append(payload)
        return {"email_id": email_id, "status": self.failed_status, "send_attempt_count": 1}

    async def defer_email_for_quota(self, conn, *, email_id, resume_at, now_utc=None):
        if self.defer_error:
            raise self.defer_error
        self.deferred_payloads.append(
            {"email_id": email_id, "resume_at": resume_at, "now_utc": now_utc}
        )
        return {
            "email_id": email_id,
            "status": "deferred_for_quota",
            "resume_at": resume_at.isoformat(),
        }


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
async def test_quota_error_opens_circuit_defers_email_and_skips_domain_until_resume():
    """覆盖 AE5：配额错误触发域名熔断，后续轮次不领取、不调用服务商。"""
    clock = _Clock()
    logs = []
    service = _Service(items=[_claimed_item("domain-a")])
    provider = _Provider(
        error=EngageLabSendError("your account balance is not enough", status_code=400)
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=logs.append,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert result["items"][0]["provider_status"] == "quota_deferred"
    assert service.deferred_payloads[0]["email_id"] == "email-001"
    assert service.failed_payloads == []
    assert worker.domain_quota_paused["domain-a"] == datetime(2026, 5, 30, 16, 0, tzinfo=UTC)
    assert logs[-1]["event"] == "quota_circuit_open"
    assert logs[-1]["domain_id"] == "domain-a"
    assert logs[-1]["paused_until"] == datetime(2026, 5, 30, 16, 0, tzinfo=UTC)

    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=5)

    assert len(service.claim_calls) == 1
    assert len(provider.payloads) == 1
    assert logs[-1]["event"] == "all_domains_quota_paused"


@pytest.mark.asyncio
async def test_quota_deferred_run_once_result_is_json_safe():
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("余额不足", status_code=400)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    json.dumps(result)


@pytest.mark.asyncio
async def test_quota_circuit_closes_after_next_beijing_midnight():
    """覆盖 AE6：北京零点后下一轮领取被动恢复并记录 closed 日志。"""
    clock = _Clock()
    logs = []
    service = _Service(items=[_claimed_item("domain-a")])
    provider = _Provider(
        error=EngageLabSendError("your account balance is not enough", status_code=400)
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=logs.append,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")
    provider.error = None
    clock.value = datetime(2026, 5, 30, 16, 0, 1, tzinfo=UTC)

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert result["items"][0]["provider_status"] == "sent"
    assert "domain-a" not in worker.domain_quota_paused
    assert any(record["event"] == "quota_circuit_closed" for record in logs)


@pytest.mark.asyncio
async def test_quota_circuit_only_skips_triggering_domain():
    """覆盖 AE7：域名 A 熔断时，域名 B 仍可正常发送。"""
    clock = _Clock()
    service = _Service(domains=["domain-a", "domain-b"], items=[_claimed_item("domain-a")])
    provider = _Provider(
        error=EngageLabSendError("your account balance is not enough", status_code=400)
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")
    provider.error = None
    service.items = [_claimed_item("domain-b")]

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.claim_calls[1]["domain_id"] == "domain-b"
    assert provider.payloads[-1]["to_email"] == "buyer@example.com"


@pytest.mark.asyncio
async def test_worker_restart_rebuilds_quota_circuit_on_first_rejected_email():
    """覆盖 AE8：重启丢失熔断态后，首封配额错误重新熔断并 defer。"""
    clock = _Clock()
    service = _Service(items=[_claimed_item("domain-a")])
    provider = _Provider(
        error=EngageLabSendError("your account balance is not enough", status_code=400)
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")

    restarted_service = _Service(items=[_claimed_item("domain-a")])
    restarted_provider = _Provider(
        error=EngageLabSendError("your account balance is not enough", status_code=400)
    )
    restarted = SendingWorker(
        service=restarted_service,
        provider=restarted_provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    await restarted.run_once(_Engine(), service_instance="worker-1")

    assert restarted_service.deferred_payloads
    assert restarted_service.failed_payloads == []
    assert "domain-a" in restarted.domain_quota_paused


@pytest.mark.asyncio
async def test_single_rate_limit_uses_retry_chain_without_circuit():
    """覆盖 AE2：单次 429 走临时失败重试链，不熔断。"""
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("too many requests", status_code=429)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.failed_payloads[0]["is_permanent"] is False
    assert service.deferred_payloads == []
    assert worker.domain_quota_paused == {}


@pytest.mark.asyncio
async def test_third_rate_limit_in_ten_minutes_upgrades_to_quota_circuit():
    """覆盖 AE3：10 分钟内第 3 次限流升级为当天熔断。"""
    clock = _Clock()
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("too many requests", status_code=429)),
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")
    await worker.run_once(_Engine(), service_instance="worker-1")
    await worker.run_once(_Engine(), service_instance="worker-1")

    assert len(service.failed_payloads) == 2
    assert len(service.deferred_payloads) == 1
    assert "domain-a" in worker.domain_quota_paused


@pytest.mark.asyncio
async def test_rate_limit_window_drops_old_hits_before_upgrade():
    """覆盖 AE3：限流命中滑出 10 分钟窗口后不升级熔断。"""
    clock = _Clock()
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("too many requests", status_code=429)),
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )

    await worker.run_once(_Engine(), service_instance="worker-1")
    clock.advance(11 * 60)
    await worker.run_once(_Engine(), service_instance="worker-1")
    await worker.run_once(_Engine(), service_instance="worker-1")

    assert len(service.failed_payloads) == 3
    assert service.deferred_payloads == []
    assert worker.domain_quota_paused == {}


@pytest.mark.asyncio
async def test_fourth_consecutive_quota_error_downgrades_to_temporary_failure():
    """覆盖 AE13：连续 3 次 defer 后，第 4 次配额错误降级为临时失败。"""
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("余额不足", status_code=400)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )
    worker.enrollment_quota_defer_counts["enrollment-001"] = 3

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.deferred_payloads == []
    assert service.failed_payloads[0]["is_permanent"] is False
    # 降级路径不熔断域名：毒药防护——误判的永久错误不得连续多日封锁整域；
    # 真实额度耗尽时，下一封 count<3 的邮件会立即重新熔断。
    assert "domain-a" not in worker.domain_quota_paused
    assert "enrollment-001" not in worker.enrollment_quota_defer_counts


@pytest.mark.asyncio
async def test_successful_send_clears_quota_defer_count():
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )
    worker.enrollment_quota_defer_counts["enrollment-001"] = 2

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert "enrollment-001" not in worker.enrollment_quota_defer_counts


@pytest.mark.asyncio
async def test_temporary_failure_does_not_clear_quota_defer_count():
    service = _Service(items=[_claimed_item("domain-a")])
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("server unavailable", status_code=503)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )
    worker.enrollment_quota_defer_counts["enrollment-001"] = 3

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert worker.enrollment_quota_defer_counts["enrollment-001"] == 3


@pytest.mark.asyncio
async def test_terminal_temporary_failure_clears_quota_defer_count():
    service = _Service(items=[_claimed_item("domain-a")])
    service.failed_status = "failed"
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("server unavailable", status_code=503)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )
    worker.enrollment_quota_defer_counts["enrollment-001"] = 2

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert "enrollment-001" not in worker.enrollment_quota_defer_counts


@pytest.mark.asyncio
async def test_all_domains_quota_paused_sleeps_without_crashing():
    sleep = AsyncMock()
    clock = _Clock()
    logs = []
    service = _Service(domains=["domain-a", "domain-b"], items=[])
    provider = _Provider()
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=sleep,
        log_sink=logs.append,
    )
    paused_until = clock.value + timedelta(hours=1)
    worker.domain_quota_paused = {"domain-a": paused_until, "domain-b": paused_until}

    result = await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=5)

    assert result == {"claimed_count": 0, "processed_count": 0, "items": []}
    assert service.claim_calls == []
    assert provider.payloads == []
    sleep.assert_awaited_once_with(5)
    assert logs[-1]["event"] == "all_domains_quota_paused"


@pytest.mark.asyncio
async def test_quota_defer_error_falls_back_to_temporary_failure():
    service = _Service(items=[_claimed_item("domain-a")])
    service.defer_error = RuntimeError("defer failed")
    logs = []
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("余额不足", status_code=400)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=logs.append,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert result["items"][0]["provider_status"] == "failed"
    assert service.failed_payloads[0]["is_permanent"] is False
    assert service.failed_payloads[0]["status_code"] == 400
    assert service.deferred_payloads == []
    assert "domain-a" in worker.domain_quota_paused
    assert any(record["event"] == "quota_defer_failed" for record in logs)
    assert any(record["event"] == "send_failed" for record in logs)


@pytest.mark.asyncio
async def test_quota_defer_and_fallback_errors_do_not_escape_run_once():
    service = _Service(items=[_claimed_item("domain-a")])
    service.defer_error = RuntimeError("defer failed")
    service.fail_error = RuntimeError("fallback failed")
    logs = []
    worker = SendingWorker(
        service=service,
        provider=_Provider(error=EngageLabSendError("余额不足", status_code=400)),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=logs.append,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert result["items"][0]["provider_status"] == "failed"
    assert result["items"][0]["status"] == "quota_defer_fallback_failed"
    assert any(record["event"] == "quota_defer_fallback_failed" for record in logs)
    assert any(record["event"] == "send_failed" for record in logs)


@pytest.mark.asyncio
async def test_paused_domain_state_survives_running_domain_gap():
    clock = _Clock()
    service = _Service(domains=["domain-b"], items=[])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )
    worker.domain_quota_paused["domain-a"] = clock.value + timedelta(hours=1)

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert "domain-a" in worker.domain_quota_paused


@pytest.mark.asyncio
async def test_rate_limit_hits_survive_running_domain_gap_until_expired():
    clock = _Clock()
    service = _Service(domains=["domain-b"], items=[])
    worker = SendingWorker(
        service=service,
        provider=_Provider(),
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )
    worker.domain_rate_limit_hits["domain-a"] = [clock.value]

    await worker.run_once(_Engine(), service_instance="worker-1")

    assert worker.domain_rate_limit_hits["domain-a"] == [clock.value]



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

    with (
        patch.object(
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
        ),
        patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock),
    ):
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

    with (
        patch.object(
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
        ),
        patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock),
    ):
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

    with (
        patch.object(
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
        ),
        patch.object(svc, "_release_reserved_quota", new_callable=AsyncMock),
        patch.object(
            svc, "_update_contact_for_permanent_failure", new_callable=AsyncMock
        ) as update_contact,
    ):
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

    with (
        patch.object(
            svc,
            "_step_condition_satisfied",
            new_callable=AsyncMock,
            side_effect=[False, True],
        ),
        patch.object(svc, "reserve_domain_quota", new_callable=AsyncMock),
    ):
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
