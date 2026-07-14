from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.services.intelligence_service import IntelligenceService
from app.services.tenant_messaging_service import TenantMessagingService


class InternalOpsService:
    def __init__(self) -> None:
        self.messaging = TenantMessagingService()
        self.intelligence = IntelligenceService()

    async def claim_due_emails(self, conn: AsyncConnection, payload: dict) -> dict:
        return await self.messaging.claim_due_emails(
            conn,
            service_instance=payload.get("service_instance", "sending-service"),
            limit=payload.get("limit", 20),
            domain_id=payload.get("domain_id"),
        )

    async def mark_email_sent(self, conn: AsyncConnection, *, email_id: str, payload: dict) -> dict:
        return await self.messaging.mark_email_sent(conn, email_id=email_id, payload=payload)

    async def mark_email_failed(self, conn: AsyncConnection, *, email_id: str, payload: dict) -> dict:
        return await self.messaging.mark_email_failed(conn, email_id=email_id, payload=payload)

    async def reserve_domain_quota(self, conn: AsyncConnection, payload: dict) -> dict:
        if "domain_id" not in payload:
            raise AppError(code="VALIDATION_ERROR", message="缺少 domain_id", status_code=422)
        return await self.messaging.reserve_domain_quota(
            conn,
            domain_id=payload["domain_id"],
            count=payload.get("count", 1),
        )

    async def publish_article(self, conn: AsyncConnection, payload: dict) -> dict:
        return await self.intelligence.publish_article(conn, payload=payload)
