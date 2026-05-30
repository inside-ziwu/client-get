import base64
import json
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class EngageLabSendError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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
        """构建 HTTP Basic Auth 认证头：Basic base64(api_user:credential)"""
        raw = f"{self.settings.engagelab_api_user}:{self.settings.engagelab_credential}"
        encoded = base64.b64encode(raw.encode()).decode()
        return f"Basic {encoded}"

    def _validate_config(self) -> None:
        """校验必需配置项是否存在"""
        if not self.settings.engagelab_base_url:
            raise EngageLabSendError("未配置 ENGAGELAB_BASE_URL")
        if not (self.settings.engagelab_api_user and self.settings.engagelab_credential):
            raise EngageLabSendError(
                "ENGAGELAB_API_USER 和 ENGAGELAB_CREDENTIAL 必须同时配置"
            )

    async def query_email_status(
        self, send_date: str, email_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """查询邮件投递状态（GET /v1/email_status），自动分批（每批 20 个 ID）"""
        self._validate_config()
        headers = {"Authorization": self._build_auth_header()}
        results: list[dict[str, Any]] = []

        if email_ids:
            # API 限制每次最多 20 个 email_ids
            for i in range(0, len(email_ids), 20):
                batch_ids = email_ids[i : i + 20]
                batch_results = await self._fetch_status_page(
                    headers, send_date, ";".join(batch_ids)
                )
                results.extend(batch_results)
        else:
            results = await self._fetch_status_page(headers, send_date, None)

        return results

    async def _fetch_status_page(
        self, headers: dict, send_date: str, email_ids_param: str | None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"send_date": send_date}
        if email_ids_param:
            params["email_ids"] = email_ids_param

        results: list[dict[str, Any]] = []
        offset = 0
        limit = 100

        async with httpx.AsyncClient(
            base_url=self.settings.engagelab_base_url,
            timeout=self.settings.engagelab_timeout_seconds,
            transport=self.transport,
        ) as client:
            while True:
                params["offset"] = str(offset)
                params["limit"] = limit
                response = await client.get(
                    "/v1/email_status", headers=headers, params=params
                )
                if response.status_code >= 400:
                    raise EngageLabSendError(
                        f"查询失败，status={response.status_code}: "
                        f"{self._sanitize_provider_text(response.text)}",
                        status_code=response.status_code,
                    )
                data = self._safe_json(response)
                batch = data.get("result", [])
                results.extend(batch)
                total = int(data.get("total", 0))
                if offset + limit >= total or not batch:
                    break
                offset += limit

        return results

    async def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_config()

        auth_value = self._build_auth_header()
        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_value,
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
                f"{self._sanitize_provider_text(response.text)}",
                status_code=response.status_code,
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
        body = {
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
        if payload.get("idempotency_key"):
            body["idempotency_key"] = payload["idempotency_key"]
        return body

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
        ):
            if secret:
                sanitized = sanitized.replace(secret, "[redacted]")
        try:
            parsed = json.loads(sanitized)
        except ValueError:
            return sanitized[:1000]
        return json.dumps(parsed, ensure_ascii=False)[:1000]
