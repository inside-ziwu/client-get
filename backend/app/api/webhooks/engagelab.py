import hashlib
import json
import logging

from fastapi import APIRouter, Depends, Header, Request

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
    request: Request,
    x_webhook_timestamp: str | None = Header(default=None, alias="X-WebHook-Timestamp"),
    x_webhook_appkey: str | None = Header(default=None, alias="X-WebHook-AppKey"),
    x_webhook_signature: str | None = Header(default=None, alias="X-WebHook-Signature"),
    conn=Depends(get_connection),
) -> dict:
    settings = get_settings()

    # 读取原始请求体并记录日志（调试阶段）
    raw_body = await request.body()
    logger.info("EngageLab webhook 原始请求体: %s", raw_body[:2000].decode("utf-8", errors="replace"))
    logger.info(
        "EngageLab webhook 请求头: timestamp=%s, appkey=%s, signature=%s",
        x_webhook_timestamp, x_webhook_appkey, x_webhook_signature,
    )

    # EngageLab 签名验证：md5(timestamp + appkey + APP_KEY)
    if not x_webhook_timestamp or not x_webhook_signature:
        raise AppError(code="FORBIDDEN", message="缺少 webhook 签名头", status_code=403)

    app_key = settings.engagelab_webhook_secret
    raw = f"{x_webhook_timestamp}{x_webhook_appkey or ''}{app_key}"
    expected = hashlib.md5(raw.encode()).hexdigest()

    if expected != x_webhook_signature:
        logger.warning("Webhook 签名校验失败: expected=%s, got=%s", expected, x_webhook_signature)
        raise AppError(code="FORBIDDEN", message="Webhook 签名校验失败", status_code=403)

    # 解析 JSON 请求体（兼容数组和对象两种格式）
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("Webhook JSON 解析失败: %s", raw_body[:500])
        raise AppError(code="VALIDATION_ERROR", message="无法解析 webhook 请求体", status_code=400)

    # EngageLab 可能发送单个事件（dict）或批量事件（list）
    events = body if isinstance(body, list) else [body]
    results = []

    for event_payload in events:
        if not isinstance(event_payload, dict):
            logger.warning("跳过非 dict 事件: %s", type(event_payload))
            continue
        try:
            data = await service.process_engagelab_event(conn, event_payload)
            results.append(data)
            logger.info("EngageLab 事件处理成功: %s", data)
        except Exception as e:
            logger.error("EngageLab 事件处理失败: %s, payload=%s", str(e), json.dumps(event_payload, ensure_ascii=False)[:500])
            results.append({"status": "error", "error": str(e)})

    return success_response({"processed": len(results), "results": results})
