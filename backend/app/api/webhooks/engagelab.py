import hashlib
import logging

from fastapi import APIRouter, Depends, Header

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import success_response
from app.db.pools import get_connection
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks-engagelab"])
service = WebhookService()


@router.get("/engagelab")
async def engagelab_webhook_verify() -> dict:
    """EngageLab URL 检测：GET 请求返回 200"""
    return success_response({"status": "ok"})


@router.post("/engagelab")
async def engagelab_webhook(
    payload: dict,
    x_webhook_timestamp: str | None = Header(default=None, alias="X-WebHook-Timestamp"),
    x_webhook_appkey: str | None = Header(default=None, alias="X-WebHook-AppKey"),
    x_webhook_signature: str | None = Header(default=None, alias="X-WebHook-Signature"),
    conn=Depends(get_connection),
) -> dict:
    settings = get_settings()

    # EngageLab 签名验证：md5(timestamp + appkey + APP_KEY)
    if not x_webhook_timestamp or not x_webhook_signature:
        raise AppError(code="FORBIDDEN", message="缺少 webhook 签名头", status_code=403)

    app_key = settings.engagelab_webhook_secret
    raw = f"{x_webhook_timestamp}{x_webhook_appkey or ''}{app_key}"
    expected = hashlib.md5(raw.encode()).hexdigest()

    if expected != x_webhook_signature:
        logger.warning("Webhook 签名校验失败: expected=%s, got=%s", expected, x_webhook_signature)
        raise AppError(code="FORBIDDEN", message="Webhook 签名校验失败", status_code=403)

    data = await service.process_engagelab_event(conn, payload)
    return success_response(data)
