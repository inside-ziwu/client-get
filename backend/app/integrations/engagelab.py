import base64
import json
from typing import Any

import httpx

from app.core.config import Settings, get_settings

# 官方 POST /v1/mail/send：request_id 最长 128，1 小时内重复提交返回上次结果。
# https://www.engagelab.com/docs/email/rest-api/deliverlies
REQUEST_ID_MAX_LENGTH = 128

# 2026-07-02 生产原文：HTTP 400 + {"code": 30877, "message": "...balance is not enough..."}.
# 见 docs/solutions/integration-issues/engagelab-quota-exhaustion-cascade.md。
# 不把其余 308xx 推断成额度或收件人无效。
VERIFIED_QUOTA_CODE = 30877
VERIFIED_QUOTA_PHRASES = (
    "balance is not enough",
    "recharge soon",
    "余额不足",
)

# 官方错误示例，属于请求参数，不是收件人无效，也不能当额度熔断。
REQUEST_PARAMETER_CODES = frozenset({30801, 30893})

# 发送接口没有已核实的「接单前地址不存在」业务码。webhook 的 invalid_email
# 发生在接单之后，不能拿来在发送分类里把联系人标 invalid。有出处之前保持为空。
RECIPIENT_PERMANENT_CODES: frozenset[int] = frozenset()
RECIPIENT_POLICY_CODES: frozenset[int] = frozenset()

RATE_LIMIT_PHRASES = ("rate limit", "too many requests")


class EngageLabSendError(Exception):
    def __init__(
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        provider_code: int | None = None,
        http_status: int | None = None,
        retry_after: str | None = None,
        outcome: str = "rejected",
        detail: str | None = None,
    ) -> None:
        self.http_status = http_status if http_status is not None else status_code
        self.status_code = self.http_status
        self.provider_code = provider_code
        self.retry_after = retry_after
        self.outcome = outcome
        self.detail = message if detail is None else detail
        super().__init__(self.safe_text())

    def safe_text(self) -> str:
        return f"engagelab_{self.outcome}:{self.http_status}:{self.provider_code}"


def classify_send_error(exc: EngageLabSendError) -> dict[str, Any]:
    """把结构化拒发分成可执行决策。不读 SQL 异常，也不把 400/422 整段当成无效地址。"""
    if exc.outcome == "uncertain":
        return _decision(
            error_type="uncertain",
            error_class="outcome_uncertain",
            decision="isolate",
            is_permanent=False,
            error_category=None,
            exc=exc,
        )

    code = exc.provider_code
    status_code = exc.http_status
    is_client_error = status_code is not None and 400 <= status_code < 500
    detail = (exc.detail or "").casefold()

    if code == VERIFIED_QUOTA_CODE or (
        is_client_error and any(phrase.casefold() in detail for phrase in VERIFIED_QUOTA_PHRASES)
    ):
        return _decision(
            error_type="quota",
            error_class="quota",
            decision="defer_quota",
            is_permanent=False,
            error_category="quota",
            exc=exc,
        )
    if code in RECIPIENT_PERMANENT_CODES:
        return _decision(
            error_type="permanent",
            error_class="recipient_permanent",
            decision="stop_enrollment",
            is_permanent=True,
            error_category="invalid",
            exc=exc,
        )
    if code in RECIPIENT_POLICY_CODES:
        return _decision(
            error_type="permanent",
            error_class="recipient_policy",
            decision="stop_enrollment",
            is_permanent=True,
            error_category="policy",
            exc=exc,
        )
    if status_code == 429 or (
        is_client_error and any(phrase in detail for phrase in RATE_LIMIT_PHRASES)
    ):
        return _decision(
            error_type="rate_limit",
            error_class="rate_limit",
            decision="retry",
            is_permanent=False,
            error_category=None,
            exc=exc,
        )
    if code in REQUEST_PARAMETER_CODES:
        return _decision(
            error_type="temporary",
            error_class="request_rejected",
            decision="retry",
            is_permanent=False,
            error_category=None,
            exc=exc,
        )
    if status_code in {401, 403}:
        return _decision(
            error_type="temporary",
            error_class="auth",
            decision="retry",
            is_permanent=False,
            error_category=None,
            exc=exc,
        )
    return _decision(
        error_type="temporary",
        error_class="unknown",
        decision="retry",
        is_permanent=False,
        error_category=None,
        exc=exc,
    )


def _decision(
    *,
    error_type: str,
    error_class: str,
    decision: str,
    is_permanent: bool,
    error_category: str | None,
    exc: EngageLabSendError,
) -> dict[str, Any]:
    return {
        "is_permanent": is_permanent,
        "error_type": error_type,
        "error_category": error_category,
        "error_class": error_class,
        "decision": decision,
        "provider_code": exc.provider_code,
        "http_status": exc.http_status,
        "retry_after": _safe_retry_after(exc.retry_after),
    }


def _safe_retry_after(value: str | None) -> str | None:
    if not value or "@" in value or len(value) > 40:
        return None
    return value


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
            raise EngageLabSendError("未配置 ENGAGELAB_BASE_URL", outcome="rejected")
        if not (self.settings.engagelab_api_user and self.settings.engagelab_credential):
            raise EngageLabSendError(
                "ENGAGELAB_API_USER 和 ENGAGELAB_CREDENTIAL 必须同时配置",
                outcome="rejected",
            )

    async def query_email_status(
        self, send_date: str, email_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """查询邮件投递状态（GET /v1/email_status），自动分批（每批 20 个 ID）"""
        self._validate_config()
        headers = {"Authorization": self._build_auth_header()}
        results: list[dict[str, Any]] = []

        if email_ids:
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
                response = await client.get("/v1/email_status", headers=headers, params=params)
                if response.status_code >= 400:
                    code, detail, retry_after = self._parse_provider_error(response)
                    raise EngageLabSendError(
                        outcome="rejected",
                        status_code=response.status_code,
                        provider_code=code,
                        retry_after=retry_after,
                        detail=detail or "",
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
            code, detail, retry_after = self._parse_provider_error(response)
            raise EngageLabSendError(
                outcome="rejected",
                status_code=response.status_code,
                provider_code=code,
                retry_after=retry_after,
                detail=detail or "",
            )

        data = self._safe_json(response)
        message_id = self._extract_message_id(data, response)
        if not message_id:
            raise EngageLabSendError(
                outcome="uncertain",
                status_code=response.status_code,
                detail="",
            )
        return {
            "engagelab_message_id": message_id,
            "provider_response": data,
        }

    def _build_request_body(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = {
            "html": payload["body_html"],
            "text": payload.get("body_text") or "",
        }
        body: dict[str, Any] = {
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
        # 本地幂等键只映射到官方 request_id。超长不截断、不改名发送 idempotency_key。
        # request_id 只覆盖约 1 小时；跨日防重由 email_send_locks 承担。
        request_id = payload.get("idempotency_key")
        if isinstance(request_id, str) and 0 < len(request_id) <= REQUEST_ID_MAX_LENGTH:
            body["request_id"] = request_id
        return body

    def _safe_json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            return {}
        if isinstance(data, dict):
            return data
        return {"data": data}

    def _parse_provider_error(
        self, response: httpx.Response
    ) -> tuple[int | None, str | None, str | None]:
        retry_after = response.headers.get("Retry-After")
        if retry_after and ("@" in retry_after or len(retry_after) > 40):
            retry_after = None
        try:
            data = response.json()
        except ValueError:
            return None, None, retry_after
        if not isinstance(data, dict):
            return None, None, retry_after
        code = data.get("code")
        if isinstance(code, str) and code.isdigit():
            code = int(code)
        if not isinstance(code, int):
            code = None
        message = data.get("message") if isinstance(data.get("message"), str) else None
        return code, message, retry_after

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
        for secret in (self.settings.engagelab_credential,):
            if secret:
                sanitized = sanitized.replace(secret, "[redacted]")
        try:
            parsed = json.loads(sanitized)
        except ValueError:
            return sanitized[:1000]
        return json.dumps(parsed, ensure_ascii=False)[:1000]
