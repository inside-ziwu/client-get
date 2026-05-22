from app.services.tenant_messaging_service import TenantMessagingService


def test_body_text_fallback_extracts_text_from_html_when_missing():
    service = TenantMessagingService()

    result = service._body_text_with_fallback(
        None,
        "<p>Hello ClientGet</p><p>Line two</p>",
    )

    assert result == "Hello ClientGet\nLine two"


def test_body_text_fallback_treats_blank_text_as_missing():
    service = TenantMessagingService()

    result = service._body_text_with_fallback("   \n", "<p>Fallback</p>")

    assert result == "Fallback"


def test_body_text_fallback_keeps_existing_template_text():
    service = TenantMessagingService()

    result = service._body_text_with_fallback("Plain ClientGet", "<p>HTML ClientGet</p>")

    assert result == "Plain ClientGet"
