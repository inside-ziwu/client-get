import base64
import json
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class EngageLabSendError(Exception):
    pass


class EngageLabClient:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.transport = transport

    def _build_auth_header(self) -> str:
        """
        构建认证头值。

        优先使用 HTTP Basic Auth（ENGAGELAB_API_USER + ENGAGELAB_CREDENTIAL）：
        - 格式：Basic base64(api_user:credential)
        - 参考：aoqi-ai/sysdev-ft-marketing 实现方式

        向后兼容：若未配置 Basic Auth 凭证，则回退到旧 Bearer/自定义 scheme
        （ENGAGELAB_API_KEY + ENGAGELAB_AUTH_SCHEME）
        """
        if self.settings.engagelab_api_user and self.settings.engagelab_credential:
            # HTTP Basic Auth：base64(api_user:credential)
            raw = f"{self.settings.engagelab_api_user}:{self.settings.engagelab_credential}"
            encoded = base64.b64encode(raw.encode()).decode()
            return f"Basic {encoded}"

        # 向后兼容旧配置（Bearer 或自定义 scheme）
        api_key = self.settings.engagelab_api_key or ""
        if self.settings.engagelab_auth_scheme:
            return f"{self.settings.engagelab_auth_scheme} {api_key}"
        return api_key

    def _validate_config(self) -> None:
        """校验必需配置项是否存在"""
        if not self.settings.engagelab_base_url:
            raise EngageLabSendError("未配置 ENGAGELAB_BASE_URL")

        # Basic Auth 模式：检查 api_user + credential
        if self.settings.engagelab_api_user or self.settings.engagelab_credential:
            if not (self.settings.engagelab_api_user and self.settings.engagelab_credential):
                raise EngageLabSendError(
                    "ENGAGELAB_API_USER 和 ENGAGELAB_CREDENTIAL 必须同时配置"
                )
            return

        # 旧模式：检查 api_key
        if not self.settings.engagelab_api_key:
            raise EngageLabSendError(
                "未配置 EngageLab 认证凭证，请配置 "
                "ENGAGELAB_API_USER+ENGAGELAB_CREDENTIAL 或 ENGAGELAB_API_KEY"
            )

    async def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_config()

        auth_value = self._build_auth_header()
        headers = {
            "Content-Type": "application/json",
            self.settings.engagelab_auth_header: auth_value,
        }

        request_body = self._build_request_body(payload)

        async with httpx.AsyncClient(
            base_url=self.settings.engagelab_base_url,
            timeout=self.settings.engagelab_timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.post(
                self.settings.engagelab_send_path,
                headers=headers,
                json=request_body,
            )
        if response.status_code >= 400:
            raise EngageLabSendError(
                f"发送失败，provider status={response.status_code}: "
                f"{self._sanitize_provider_text(response.text)}"
            )

        data = self._safe_json(response)
        message_id = self._extract_message_id(data, response)
        if not message_id:
            raise EngageLabSendError("provider 返回成功但缺少 message_id")
        return {
            "engagelab_message_id": message_id,
            "provider_response": data,
        }

    def _build_request_body(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = {
            "html": payload["body_html"],
            "text": payload.get("body_text") or "",
        }
        return {
            "from": payload["from_email"],
            "to": [payload["to_email"]],
            "body": {
                "subject": payload["subject"],
                "content": content,
                "settings": {
                    "send_mode": 0,
                    "return_email_id": True,
                    "open_tracking": True,
                    "click_tracking": bool(payload.get("click_tracking", False)),
                    "unsubscribe_tracking": bool(payload.get("unsubscribe_tracking", False)),
                },
            },
        }

    def _safe_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            return {"raw_text": response.text}
        if isinstance(data, dict):
            return data
        return {"data": data}

    def _extract_message_id(self, data: dict[str, Any], response: httpx.Response) -> str | None:
        candidates = [
            data.get("message_id"),
            data.get("engagelab_message_id"),
            data.get("email_id"),
            data.get("id"),
            self._first_value(data.get("email_ids")),
        ]
        nested = data.get("data")
        if isinstance(nested, dict):
            candidates.extend(
                [
                    nested.get("message_id"),
                    nested.get("engagelab_message_id"),
                    nested.get("email_id"),
                    nested.get("id"),
                    self._first_value(nested.get("email_ids")),
                ]
            )
        candidates.append(response.headers.get("X-Message-Id"))
        for candidate in candidates:
            if candidate:
                return str(candidate)
        return None

    def _first_value(self, value: Any) -> Any:
        if isinstance(value, list) and value:
            return value[0]
        return None

    def _sanitize_provider_text(self, text: str) -> str:
        sanitized = text
        for secret in (
            self.settings.engagelab_credential,
            self.settings.engagelab_api_key,
        ):
            if secret:
                sanitized = sanitized.replace(secret, "[redacted]")
        try:
            parsed = json.loads(sanitized)
        except ValueError:
            return sanitized[:1000]
        return json.dumps(parsed, ensure_ascii=False)[:1000]
