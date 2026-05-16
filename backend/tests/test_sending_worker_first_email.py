import pytest

from app.integrations.engagelab import EngageLabSendError
from app.workers.sending import SendingWorker


class _Tx:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Engine:
    def begin(self):
        return _Tx()


class _Provider:
    def __init__(self, *, result=None, error=None):
        self.result = result
        self.error = error
        self.payloads = []

    async def send_email(self, payload):
        self.payloads.append(payload)
        if self.error is not None:
            raise self.error
        return self.result


class _Service:
    def __init__(self, item):
        self.item = item
        self.sent_payloads = []
        self.failed_payloads = []

    async def claim_due_emails(self, conn, *, service_instance, limit):
        return {"items": [self.item]}

    async def mark_email_sent(self, conn, *, email_id, payload):
        self.sent_payloads.append((email_id, payload))
        return {"email_id": email_id, "status": "sent"}

    async def mark_email_failed(self, conn, *, email_id, payload):
        self.failed_payloads.append((email_id, payload))
        return {"email_id": email_id, "status": "failed", "reason": payload["reason"]}


def _claimed_email():
    return {
        "email_id": "email-123",
        "from_email": "aoqi@xapcb.com",
        "from_name": "Aoqi",
        "to_email": "aip.lazy@gmail.com",
        "to_name": "Smoke Test",
        "subject": "First email smoke test",
        "body_html": "<p>Hello</p>",
        "body_text": "Hello",
    }


@pytest.mark.asyncio
async def test_worker_sends_one_claimed_email_and_marks_it_sent():
    service = _Service(_claimed_email())
    provider = _Provider(result={"engagelab_message_id": "provider-msg-123"})
    worker = SendingWorker(service=service, provider=provider)

    result = await worker.run_once(_Engine(), service_instance="test-worker", limit=1)

    assert result["claimed_count"] == 1
    assert result["processed_count"] == 1
    assert provider.payloads == [
        {
            "from_email": "aoqi@xapcb.com",
            "from_name": "Aoqi",
            "to_email": "aip.lazy@gmail.com",
            "to_name": "Smoke Test",
            "subject": "First email smoke test",
            "body_html": "<p>Hello</p>",
            "body_text": "Hello",
            "idempotency_key": "email-123",
        }
    ]
    assert service.sent_payloads == [
        ("email-123", {"engagelab_message_id": "provider-msg-123"})
    ]
    assert service.failed_payloads == []
    assert result["items"] == [
        {"email_id": "email-123", "status": "sent", "provider_status": "sent"}
    ]


@pytest.mark.asyncio
async def test_worker_marks_email_failed_when_provider_rejects_send():
    service = _Service(_claimed_email())
    provider = _Provider(error=EngageLabSendError("发送失败，provider status=401"))
    worker = SendingWorker(service=service, provider=provider)

    result = await worker.run_once(_Engine(), service_instance="test-worker", limit=1)

    assert service.sent_payloads == []
    assert service.failed_payloads == [
        (
            "email-123",
            {
                "reason": "发送失败，provider status=401",
                "error_code": "ENGAGELAB_ERROR",
                "error_message": "发送失败，provider status=401",
            },
        )
    ]
    assert result["items"] == [
        {
            "email_id": "email-123",
            "status": "failed",
            "reason": "发送失败，provider status=401",
            "provider_status": "failed",
        }
    ]
