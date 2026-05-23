"""验证 tenant_messaging_service 和 webhook_service 已移除 visibility_status。"""

import inspect

from app.services.tenant_messaging_service import TenantMessagingService
from app.services.webhook_service import WebhookService


class TestMessagingNoVisibility:
    def test_no_visibility_in_messaging(self):
        import app.services.tenant_messaging_service as mod
        source = inspect.getsource(mod)
        assert "visibility_status" not in source

    def test_no_visibility_in_webhook(self):
        import app.services.webhook_service as mod
        source = inspect.getsource(mod)
        assert "visibility_status" not in source
