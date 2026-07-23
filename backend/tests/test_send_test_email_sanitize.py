"""test-send 链路必须与正式发送同序 sanitize。

背景：2026-07-23 发现 test-send 是全后端唯一绕过 sanitize 的发送出口——
历史入库的 &amp; 存量污染经它原样发出（正式链路 claim 有 sanitize 动态修正）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tenant_messaging_service import TenantMessagingService

DIRTY_TPL = {
    "id": "tpl-1",
    "subject": "PCB Partner for LED &amp; Automotive",
    "body_html": "<p>Fabrication &amp; Assembly</p>",
    "body_text": "Fabrication &amp; Assembly\nISO &amp; IATF certified",
}


def _conn():
    email_result = MagicMock()
    email_result.scalar_one_or_none.return_value = "me@test.com"
    tpl_result = MagicMock()
    tpl_result.mappings.return_value.first.return_value = dict(DIRTY_TPL)
    domain_result = MagicMock()
    domain_result.mappings.return_value.first.return_value = {"sender_email": "s@mail.test"}
    conn = AsyncMock()
    conn.execute.side_effect = [email_result, tpl_result, domain_result]
    return conn


class TestSendTestEmailSanitize:
    @pytest.mark.asyncio
    async def test_legacy_amp_pollution_corrected_before_send(self):
        with patch("app.services.tenant_messaging_service.EngageLabClient") as client_cls:
            client_cls.return_value.send_email = AsyncMock()
            result = await TenantMessagingService().send_test_email(
                _conn(), "t-1", "u-1", "tpl-1"
            )
            payload = client_cls.return_value.send_email.await_args.args[0]

        assert result["success"] is True
        # 纯文本语境：&amp; 还原为 &
        assert payload["subject"] == "PCB Partner for LED & Automotive"
        assert "&amp;" not in payload["body_text"]
        assert "Fabrication & Assembly" in payload["body_text"]
        # HTML 语境：实体保持（正确行为）
        assert "&amp;" in payload["body_html"]
