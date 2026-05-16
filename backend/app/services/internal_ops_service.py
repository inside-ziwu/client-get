import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.crypto import decrypt_secret
from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.collection_service import CollectionService
from app.services.intelligence_service import IntelligenceService
from app.services.scoring_service import ScoringService
from app.services.tenant_messaging_service import TenantMessagingService


class InternalOpsService:
    def __init__(self) -> None:
        self.collection = CollectionService()
        self.messaging = TenantMessagingService()
        self.scoring = ScoringService()
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

    async def batch_upsert_competitors(self, conn: AsyncConnection, *, task_id: str, competitors: list[dict]) -> dict:
        tenant_keyword_map = await self._load_task_tenant_keywords(conn, task_id)
        count = 0
        for competitor in competitors:
            for tenant_id in tenant_keyword_map:
                await conn.execute(
                    text(
                        """
                        INSERT INTO competitor_companies
                          (id, tenant_id, company_name, domain, reason, source_type, raw_data)
                        VALUES
                          (:id, :tenant_id, :company_name, :domain, :reason, :source_type, CAST(:raw_data AS jsonb))
                        ON CONFLICT (tenant_id, company_name) DO UPDATE
                        SET domain = COALESCE(excluded.domain, competitor_companies.domain),
                            reason = COALESCE(excluded.reason, competitor_companies.reason),
                            raw_data = excluded.raw_data
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "tenant_id": tenant_id,
                        "company_name": competitor["company_name"],
                        "domain": competitor.get("domain"),
                        "reason": competitor.get("reason"),
                        "source_type": competitor.get("source_type", "lixiaoyun"),
                        "raw_data": json.dumps(competitor.get("raw_data", {}), ensure_ascii=False),
                    },
                )
                count += 1
        return {"task_id": task_id, "count": count}

    async def trigger_scoring(self, conn: AsyncConnection, payload: dict) -> dict:
        return await self.scoring.trigger_scoring(
            conn,
            tenant_id=payload.get("tenant_id"),
            tenant_company_ids=payload.get("tenant_company_ids"),
            pending_only=payload.get("pending_only", False),
            mode=payload.get("mode", "inline"),
        )

    async def claim_scoring_jobs(self, conn: AsyncConnection, payload: dict) -> dict:
        return await self.scoring.claim_jobs(
            conn,
            service_instance=payload.get("service_instance", "scoring-service"),
            limit=payload.get("limit", 20),
            lease_seconds=payload.get("lease_seconds", 300),
        )

    async def submit_scoring_job(self, conn: AsyncConnection, *, job_id: str, payload: dict) -> dict:
        return await self.scoring.submit_job_result(
            conn,
            job_id=job_id,
            lease_id=payload["lease_id"],
            score_result=payload.get("result"),
            error=payload.get("error"),
            retryable=payload.get("retryable", False),
        )

    async def claim_due_emails(self, conn: AsyncConnection, payload: dict) -> dict:
        return await self.messaging.claim_due_emails(
            conn,
            service_instance=payload.get("service_instance", "sending-service"),
            limit=payload.get("limit", 20),
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

    async def _load_task_tenant_keywords(self, conn: AsyncConnection, task_id: str) -> dict[str, str]:
        result = await conn.execute(
            text(
                """
                SELECT tenant_id, keyword_id
                FROM collection_task_keywords
                WHERE task_id = :task_id
                """
            ),
            {"task_id": task_id},
        )
        rows = result.mappings().all()
        if not rows:
            raise AppError(code="NOT_FOUND", message="collection task 或其关键词绑定不存在", status_code=404)
        return {str(row["tenant_id"]): str(row["keyword_id"]) for row in rows}
