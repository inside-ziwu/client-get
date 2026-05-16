import base64

import httpx
import pytest

from app.core.config import Settings
from app.integrations.engagelab import EngageLabClient, EngageLabSendError


def _settings(**overrides):
    values = {
        "engagelab_base_url": "https://email.api.engagelab.cc",
        "engagelab_api_user": "xinanpcb",
        "engagelab_credential": "test-secret",
        "engagelab_api_key": None,
    }
    values.update(overrides)
    return Settings(**values)


def _internal_payload(**overrides):
    payload = {
        "from_email": "aoqi@xapcb.com",
        "from_name": "Aoqi",
        "to_email": "aip.lazy@gmail.com",
        "to_name": "Smoke Test",
        "subject": "First email smoke test",
        "body_html": "<p>Hello</p>",
        "body_text": "Hello",
        "idempotency_key": "email-123",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_send_email_uses_basic_auth_from_api_user_and_credential():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(200, json={"message_id": "msg-123"})

    client = EngageLabClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),
    )

    await client.send_email(_internal_payload())

    expected = base64.b64encode(b"xinanpcb:test-secret").decode()
    assert captured["authorization"] == f"Basic {expected}"


@pytest.mark.asyncio
async def test_send_email_posts_reference_payload_shape():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = request.read()
        return httpx.Response(200, json={"message_id": "msg-123"})

    client = EngageLabClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),
    )

    await client.send_email(_internal_payload())

    assert httpx.Response(200, content=captured["payload"]).json() == {
        "from": "aoqi@xapcb.com",
        "to": ["aip.lazy@gmail.com"],
        "body": {
            "subject": "First email smoke test",
            "content": {
                "html": "<p>Hello</p>",
                "text": "Hello",
            },
            "settings": {
                "send_mode": 0,
                "return_email_id": True,
                "open_tracking": True,
                "click_tracking": False,
                "unsubscribe_tracking": False,
            },
        },
    }


@pytest.mark.asyncio
async def test_send_email_uses_current_default_send_path():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"message_id": "msg-123"})

    client = EngageLabClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),
    )

    await client.send_email(_internal_payload())

    assert captured["url"] == "https://email.api.engagelab.cc/v1/mail/send"


@pytest.mark.asyncio
async def test_send_email_normalizes_likely_provider_message_id_fields():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"email_id": "provider-email-123"})

    client = EngageLabClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = await client.send_email(_internal_payload())

    assert result["engagelab_message_id"] == "provider-email-123"


@pytest.mark.asyncio
async def test_send_email_normalizes_official_email_ids_response():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"email_ids": ["provider-email-456"]})

    client = EngageLabClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),
    )

    result = await client.send_email(_internal_payload())

    assert result["engagelab_message_id"] == "provider-email-456"


@pytest.mark.asyncio
async def test_provider_failure_error_keeps_status_context_without_leaking_credential():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": "invalid credential test-secret"},
        )

    client = EngageLabClient(
        settings=_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EngageLabSendError) as exc_info:
        await client.send_email(_internal_payload())

    message = str(exc_info.value)
    assert "provider status=401" in message
    assert "test-secret" not in message
