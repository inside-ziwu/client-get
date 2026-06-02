from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.crypto import decrypt_secret
from app.core.errors import AppError
from app.services.intelligence_service import IntelligenceService
from app.services.tenant_messaging_service import TenantMessagingService


class InternalOpsService:
    def __init__(self) -> None:
        self.messaging = TenantMessagingService()
        self.intelligence = IntelligenceService()

    async def list_collection_credentials(self, conn: AsyncConnection, source_type: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, account_no, username, credentials_encrypted, rotation_order, daily_quota, current_day_used, is_active
                FROM data_source_credentials
                WHERE source_type = :source_type AND is_active = true
                ORDER BY rotation_order ASC, created_at ASC
                """
            ),
            {"source_type": source_type},
        )
        return [
            {
                "id": str(row["id"]),
                "account_no": row["account_no"],
                "username": row["username"],
                "secret": decrypt_secret(row["credentials_encrypted"]),
                "rotation_order": row["rotation_order"],
                "daily_quota": row["daily_quota"],
                "current_day_used": row["current_day_used"],
                "is_active": row["is_active"],
            }
            for row in result.mappings().all()
        ]

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
