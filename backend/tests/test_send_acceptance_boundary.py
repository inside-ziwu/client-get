"""接单回写与拒发分类：成功回执不得重发，未知错误不得标无效或熔断。"""

import json
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import httpx
import pytest

from app.integrations.engagelab import (
    REQUEST_ID_MAX_LENGTH,
    EngageLabClient,
    EngageLabSendError,
    classify_send_error,
)
from app.services.tenant_messaging_service import TenantMessagingService
from app.workers.sending import RECEIPT_RETRY_DELAYS, SendingWorker, sanitize_round_result
from tests.test_sending_worker import _claimed_item, _Clock, _Engine, _Service, _settings


class _ScriptedProvider:
    def __init__(self, results):
        self.results = list(results)
        self.payloads = []

    async def send_email(self, payload):
        self.payloads.append(payload)
        outcome = self.results.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _long_id(length: int) -> str:
    local = "buyer" + ("x" * max(length - len("@example.com") - 20, 1))
    value = f"1447054895514_{local}.sc-10$buyer@example.com"
    if len(value) < length:
        value = value + ("a" * (length - len(value)))
    return value[:length]


@pytest.mark.asyncio
async def test_request_id_is_sent_without_truncation_or_legacy_key():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"email_ids": [_long_id(107)]})

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

    assert seen["body"]["request_id"] == "enrollment-001:step-001"
    assert "idempotency_key" not in seen["body"]
    assert result["engagelab_message_id"] == _long_id(107)
    assert len(result["engagelab_message_id"]) == 107


@pytest.mark.asyncio
async def test_request_id_over_128_is_omitted_not_truncated():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"email_ids": ["msg-001"]})

    client = EngageLabClient(settings=_settings(), transport=httpx.MockTransport(handler))
    key = "k" * (REQUEST_ID_MAX_LENGTH + 1)
    await client.send_email(
        {
            "from_email": "sales@example.com",
            "to_email": "buyer@example.com",
            "subject": "Hello",
            "body_html": "<p>Hello</p>",
            "idempotency_key": key,
        }
    )

    assert "request_id" not in seen["body"]
    assert "idempotency_key" not in seen["body"]
    assert key[:128] not in json.dumps(seen["body"])


@pytest.mark.asyncio
async def test_success_without_message_id_is_uncertain():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"email_ids": []})

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

    assert exc_info.value.outcome == "uncertain"
    assert "buyer@example.com" not in str(exc_info.value)


def test_verified_quota_code_is_quota_and_broad_chinese_text_is_not():
    quota = classify_send_error(
        EngageLabSendError(
            status_code=400,
            provider_code=30877,
            detail="mail failed to send. balance is not enough, please recharge soon",
        )
    )
    assert quota["error_class"] == "quota"
    assert quota["decision"] == "defer_quota"

    broad = classify_send_error(
        EngageLabSendError(status_code=400, provider_code=39999, detail="配额已达上限")
    )
    assert broad["error_class"] == "unknown"
    assert broad["is_permanent"] is False
    assert broad["error_category"] is None

    request_error = classify_send_error(
        EngageLabSendError(status_code=400, provider_code=30801, detail="From can not be empty")
    )
    assert request_error["error_class"] == "request_rejected"
    assert request_error["error_category"] is None

    bare_422 = classify_send_error(EngageLabSendError(status_code=422, detail="invalid"))
    assert bare_422["is_permanent"] is False
    assert bare_422["error_category"] is None


def test_sql_exception_text_is_not_a_provider_quota_or_rate_limit():
    internal = classify_send_error(
        EngageLabSendError(
            status_code=None,
            detail="value too long for type character varying(100)",
        )
    )
    assert internal["error_class"] != "quota"
    assert internal["error_class"] != "rate_limit"


@pytest.mark.asyncio
async def test_accepted_finalize_failure_does_not_resend_or_release():
    service = _Service()
    service.fail_error = AssertionError("must not mark failed")
    message_id = _long_id(107)
    provider = _ScriptedProvider([{"engagelab_message_id": message_id}])
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=_Clock(),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=[],
    )
    real_sent = service.mark_email_sent

    async def explode(conn, *, email_id, payload):
        raise RuntimeError("value too long for type character varying(100) buyer@example.com")

    service.mark_email_sent = explode
    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert len(provider.payloads) == 1
    assert service.acceptance_calls == [message_id]
    assert service.failed_payloads == []
    assert service.deferred_payloads == []
    assert worker.domain_quota_paused == {}
    assert worker.domain_rate_limit_hits == {}
    assert result["items"][0]["provider_status"] == "accepted_pending"
    assert result["items"][0]["message_id_length"] == 107
    dumped = json.dumps(result, default=str)
    assert message_id not in dumped
    assert "buyer@example.com" not in dumped
    assert "character varying" not in dumped
    service.mark_email_sent = real_sent


@pytest.mark.asyncio
async def test_receipt_write_failure_retries_then_blocks_resend():
    service = _Service()
    service.acceptance_error = RuntimeError("db unavailable credential=secret buyer@example.com")
    provider = _ScriptedProvider([{"engagelab_message_id": _long_id(101)}])
    sleep = AsyncMock()
    logs = []
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=_Clock(),
        sleep=sleep,
        random_between=lambda low, high: 0,
        log_sink=logs.append,
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert len(provider.payloads) == 1
    assert service.failed_payloads == []
    assert service.deferred_payloads == []
    assert result["items"][0]["error_class"] == "internal_finalize"
    assert [call.args[0] for call in sleep.await_args_list] == list(RECEIPT_RETRY_DELAYS)
    dumped = json.dumps({"logs": logs, "result": result}, default=str)
    assert "secret" not in dumped
    assert "buyer@example.com" not in dumped
    assert "db unavailable" not in dumped


@pytest.mark.asyncio
async def test_three_local_write_errors_do_not_open_quota_before_real_quota():
    clock = _Clock()
    service = _Service()
    message_id = _long_id(101)
    provider = _ScriptedProvider(
        [
            {"engagelab_message_id": message_id},
            {"engagelab_message_id": message_id},
            {"engagelab_message_id": message_id},
            EngageLabSendError(
                status_code=400,
                provider_code=30877,
                detail="balance is not enough",
            ),
        ]
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=[],
    )

    async def explode(conn, *, email_id, payload):
        raise RuntimeError("StringDataRightTruncationError")

    service.mark_email_sent = explode
    for _ in range(3):
        result = await worker.run_once(_Engine(), service_instance="worker-1")
        assert result["items"][0]["provider_status"] == "accepted_pending"
        assert "domain-a" not in worker.domain_quota_paused

    service.mark_email_sent = _Service.mark_email_sent.__get__(service, _Service)
    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert len(provider.payloads) == 4
    assert result["items"][0]["provider_status"] == "quota_deferred"
    assert len(service.deferred_payloads) == 1
    assert service.failed_payloads == []
    assert worker.domain_quota_paused["domain-a"] == datetime(2026, 5, 30, 16, 0, tzinfo=UTC)
    assert worker.enrollment_quota_defer_counts["enrollment-001"] == 1


@pytest.mark.asyncio
async def test_timeout_and_missing_id_do_not_retry_or_invalidate():
    service = _Service()
    provider = _ScriptedProvider(
        [
            httpx.ConnectError("connection reset"),
        ]
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=_Clock(),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=[],
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1")

    assert service.uncertain_calls == ["email-001"]
    assert service.failed_payloads == []
    assert result["items"][0]["provider_status"] == "uncertain"
    assert result["items"][0]["error_class"] == "outcome_uncertain"


@pytest.mark.asyncio
async def test_restart_finalizes_pending_without_sending():
    service = _Service(items=[])
    message_id = _long_id(512)
    service.pending_items = [
        {
            "email_id": "email-001",
            "tenant_id": "tenant-001",
            "enrollment_id": "enrollment-001",
            "step_id": "step-001",
            "provider_message_id": message_id,
        }
    ]
    provider = _ScriptedProvider([])
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=_Clock(),
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=[],
    )

    result = await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)

    assert provider.payloads == []
    assert service.sent_payloads == [{"engagelab_message_id": message_id}]
    assert result["finalized_count"] == 1
    assert message_id not in json.dumps(result)


@pytest.mark.asyncio
async def test_permanent_recipient_failures_do_not_pause_domain_before_next_send():
    clock = _Clock()
    service = _Service()
    provider = _ScriptedProvider(
        [
            EngageLabSendError(status_code=400, provider_code=1, detail="bad-1"),
            EngageLabSendError(status_code=400, provider_code=1, detail="bad-2"),
            EngageLabSendError(status_code=400, provider_code=1, detail="bad-3"),
            {"engagelab_message_id": "msg-ok"},
        ]
    )
    worker = SendingWorker(
        service=service,
        provider=provider,
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=[],
    )
    permanent = {
        "is_permanent": True,
        "error_type": "permanent",
        "error_category": "invalid",
        "error_class": "recipient_permanent",
        "decision": "stop_enrollment",
        "provider_code": 1,
        "http_status": 400,
        "retry_after": None,
    }

    from app.workers import sending as sending_module

    original = sending_module.classify_send_error
    sending_module.classify_send_error = lambda exc: permanent
    try:
        for index in range(3):
            service.items = [_claimed_item("domain-a") | {"enrollment_id": f"enrollment-{index}"}]
            await worker.run_once(_Engine(), service_instance="worker-1")
        service.items = [_claimed_item("domain-a") | {"enrollment_id": "enrollment-ok"}]
        result = await worker.run_once(_Engine(), service_instance="worker-1")
    finally:
        sending_module.classify_send_error = original

    assert len(service.failed_payloads) == 3
    assert all(payload["is_permanent"] is True for payload in service.failed_payloads)
    assert service.deferred_payloads == []
    assert worker.domain_quota_paused == {}
    assert result["items"][0]["provider_status"] == "sent"


@pytest.mark.asyncio
async def test_claim_sql_skips_held_dispatch_states_and_records_usage_date():
    svc = TenantMessagingService()
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=AsyncMock())
    from tests.test_sending_worker import _claim_row, _result

    rows = [_claim_row("enrollment-ready", "ready@example.com")]
    conn.execute = AsyncMock(side_effect=[_result(all_rows=rows), _result(first=None)])

    from unittest.mock import patch

    with (
        patch.object(svc, "_step_condition_satisfied", new_callable=AsyncMock, return_value=True),
        patch.object(svc, "reserve_domain_quota", new_callable=AsyncMock),
    ):
        await svc.claim_due_emails(
            conn,
            service_instance="worker-1",
            limit=1,
            domain_id="11111111-1111-1111-1111-111111111111",
            timezone_config={"rules": {}, "default_rule": None, "countries": {}, "holidays": set()},
            now_utc=datetime(2026, 10, 26, 16, 30, tzinfo=UTC),
        )

    sql = "\n".join(str(call.args[0]) for call in conn.execute.call_args_list)
    assert "accepted_pending" in sql
    assert "dispatching" in sql
    assert "uncertain" in sql
    assert "quota_usage_date" in sql
    assert "instance_id" in sql
    params = conn.execute.call_args_list[1].args[1]
    assert params["quota_usage_date"] == date(2026, 10, 27)


@pytest.mark.asyncio
async def test_422_status_alone_does_not_mark_contact_invalid():
    svc = TenantMessagingService()
    conn = AsyncMock()
    await svc._update_contact_for_permanent_failure(
        conn,
        tenant_id="tenant-001",
        tenant_contact_id="contact-001",
        status_code=422,
        error_category=None,
    )
    conn.execute.assert_not_awaited()


def test_round_result_strips_reason_and_raw_id():
    raw_id = _long_id(107)
    sanitized = sanitize_round_result(
        {
            "claimed_count": 1,
            "processed_count": 1,
            "items": [
                {
                    "email_id": "email-001",
                    "status": "failed",
                    "provider_status": "failed",
                    "reason": f"update failed {raw_id} buyer@example.com",
                    "message_id_length": 107,
                }
            ],
        }
    )
    dumped = json.dumps(sanitized)
    assert raw_id not in dumped
    assert "buyer@example.com" not in dumped
    assert sanitized["items"][0]["message_id_length"] == 107


@pytest.mark.asyncio
async def test_defer_releases_claim_day_quota_across_beijing_midnight():
    from tests.test_quota_defer_service import EMAIL_ID, RESUME_AT, FakeQuotaDeferConn

    conn = FakeQuotaDeferConn()
    conn.lock_usage_date = date(2026, 10, 26)
    await TenantMessagingService().defer_email_for_quota(
        conn,
        email_id=str(EMAIL_ID),
        resume_at=RESUME_AT,
        now_utc=datetime(2026, 10, 26, 16, 30, tzinfo=UTC),
    )
    _sql, params = conn.statements_containing("UPDATE domain_daily_usage")[0]
    assert params["usage_date"] == date(2026, 10, 26)


def test_repair_summary_does_not_treat_retries_as_provider_accepts():
    from app.services.accepted_send_repair import (
        candidate_sql,
        correlate_receipts,
        summarize_candidates,
    )

    rows = [
        {
            "instance_id": "b",
            "tenant_id": "tenant-1",
            "enrollment_id": "enroll-1",
            "step_id": "step-1",
            "email_id": "email-1",
            "lock_status": "failed",
        },
        {
            "instance_id": "b",
            "tenant_id": "tenant-1",
            "enrollment_id": "enroll-1",
            "step_id": "step-1",
            "email_id": "email-2",
            "lock_status": "failed",
        },
        {
            "instance_id": "default",
            "tenant_id": "tenant-a",
            "enrollment_id": "enroll-a",
            "step_id": "step-a",
            "email_id": "email-a",
            "lock_status": "released",
        },
    ]
    sql = candidate_sql(False)
    assert "%(start)s" not in sql
    assert sql.count("%s") == 4
    summary = summarize_candidates(rows)
    assert summary["multiple_failed_same_step"] == 1
    assert summary["single_failed_without_provider_id"] == 1
    assert summary["needs_verification"] == 2
    assert all(group["verdict"] == "needs_verification" for group in summary["groups"])

    raw_id = _long_id(107)
    correlated = correlate_receipts(
        summary,
        [{"email_id": "email-1", "message_id": raw_id, "accepted": True}],
    )
    dumped = json.dumps(correlated)
    assert raw_id not in dumped
    assert 107 in correlated["groups"][0]["receipt_id_lengths"]
