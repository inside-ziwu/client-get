from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.services.webhook_service import WebhookService


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


class FakeWebhookConn:
    def __init__(self, *, duplicate: bool = False):
        self.duplicate = duplicate
        self.executions = []
        self.email = {
            "id": UUID("019f1d2a-8b67-72d0-a3b4-fbdd82e394cd"),
            "created_at": datetime(2026, 7, 1, 10, 12, 35, tzinfo=timezone.utc),
            "tenant_id": UUID("019dc238-c4c9-7de8-842f-8d46731481c1"),
            "enrollment_id": None,
            "tenant_contact_id": None,
            "to_email": "a.aubrey@kingfield-electronics.co.uk",
            "status": "sent",
            "open_count": 0,
            "first_opened_at": None,
        }

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.executions.append((sql, params or {}))

        if "FROM emails" in sql:
            return FakeResult(self.email)

        if "INSERT INTO email_events" in sql:
            if self.duplicate:
                return FakeResult(None)
            return FakeResult({"id": UUID("019f1d2a-e641-7da8-89b8-8ca2528ce76c")})

        return FakeResult(None)

    @property
    def inserted_provider_event_id(self) -> str:
        for sql, params in self.executions:
            if "INSERT INTO email_events" in sql:
                return params["provider_event_id"]
        raise AssertionError("未执行 email_events 插入")


def make_open_payload(message_id: str, occurred_at: int = 1782900776339) -> dict:
    return {
        "server": "email",
        "subject": "A Reliable PCB Manufacturing Partner for Your Future Projects",
        "response": {
            "event": "open",
            "response_data": {
                "email_id": message_id,
                "message": "open email",
            },
        },
        "itime": occurred_at,
    }


@pytest.mark.asyncio
async def test_engagelab_webhook_keeps_long_provider_event_id():
    message_id = (
        "1782900756909_131594_22975_835.sc-10_43_4_215-inbound0$"
        "a.aubrey@kingfield-electronics.co.uk"
    )
    payload = make_open_payload(message_id)
    expected_provider_event_id = f"{message_id}_open_{payload['itime']}"

    conn = FakeWebhookConn()

    result = await WebhookService().process_engagelab_event(conn, payload)

    assert len(expected_provider_event_id) > 100
    assert result == {
        "status": "processed",
        "provider_event_id": expected_provider_event_id,
    }
    assert conn.inserted_provider_event_id == expected_provider_event_id


@pytest.mark.asyncio
async def test_engagelab_webhook_treats_duplicate_long_provider_event_id_as_duplicate():
    message_id = (
        "1782900756909_131594_22975_835.sc-10_43_4_215-inbound0$"
        "a.aubrey@kingfield-electronics.co.uk"
    )
    payload = make_open_payload(message_id)
    expected_provider_event_id = f"{message_id}_open_{payload['itime']}"

    conn = FakeWebhookConn(duplicate=True)

    result = await WebhookService().process_engagelab_event(conn, payload)

    assert len(expected_provider_event_id) > 100
    assert result == {
        "status": "duplicate",
        "provider_event_id": expected_provider_event_id,
    }
    assert conn.inserted_provider_event_id == expected_provider_event_id
