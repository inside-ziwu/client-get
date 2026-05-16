from fastapi import APIRouter, Depends, Header

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import success_response
from app.db.pools import get_connection
from app.services.webhook_service import WebhookService

router = APIRouter(tags=["webhooks-engagelab"])
service = WebhookService()


@router.post("/engagelab")
async def engagelab_webhook(
    payload: dict,
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    conn=Depends(get_connection),
) -> dict:
    settings = get_settings()
    if webhook_secret != settings.engagelab_webhook_secret:
        raise AppError(code="FORBIDDEN", message="Webhook secret 校验失败", status_code=403)
    data = await service.process_engagelab_event(conn, payload)
    return success_response(data)

