from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.ids import new_uuid


class AiUsageLogService:
    async def create_pending(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        model_id: str,
        usage_type: str,
        estimated_cost: Decimal,
        idempotency_key: str,
        user_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> str:
        existing = await conn.execute(
            text(
                """
                SELECT id
                FROM ai_usage_logs
                WHERE tenant_id = :tenant_id AND idempotency_key = :idempotency_key
                """
            ),
            {"tenant_id": tenant_id, "idempotency_key": idempotency_key},
        )
        row = existing.mappings().first()
        if row is not None:
            return str(row["id"])

        usage_log_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO ai_usage_logs
                  (id, tenant_id, user_id, model_id, usage_type, entity_type, entity_id, estimated_cost, status, idempotency_key)
                VALUES
                  (:id, :tenant_id, :user_id, :model_id, :usage_type, :entity_type, :entity_id, :estimated_cost, 'pending', :idempotency_key)
                """
            ),
            {
                "id": usage_log_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "model_id": model_id,
                "usage_type": usage_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "estimated_cost": estimated_cost,
                "idempotency_key": idempotency_key,
            },
        )
        return usage_log_id

    async def complete(
        self,
        conn: AsyncConnection,
        *,
        usage_log_id: str,
        provider_request_id: str | None,
        provider_response: dict,
        actual_cost: Decimal,
        response_usage: dict,
    ) -> None:
        await conn.execute(
            text(
                """
                UPDATE ai_usage_logs
                SET status = 'completed',
                    provider_request_id = :provider_request_id,
                    provider_response = CAST(:provider_response AS jsonb),
                    actual_cost = :actual_cost,
                    input_tokens = :input_tokens,
                    output_tokens = :output_tokens,
                    total_tokens = :total_tokens,
                    error_code = NULL,
                    error_message = NULL
                WHERE id = :usage_log_id
                """
            ),
            {
                "usage_log_id": usage_log_id,
                "provider_request_id": provider_request_id,
                "provider_response": self._to_json(provider_response),
                "actual_cost": actual_cost,
                "input_tokens": response_usage.get("input_tokens", 0),
                "output_tokens": response_usage.get("output_tokens", 0),
                "total_tokens": response_usage.get("total_tokens", 0),
            },
        )

    async def fail(
        self,
        conn: AsyncConnection,
        *,
        usage_log_id: str,
        error_code: str,
        error_message: str,
        provider_response: dict | None = None,
    ) -> None:
        await conn.execute(
            text(
                """
                UPDATE ai_usage_logs
                SET status = 'failed',
                    provider_response = CAST(:provider_response AS jsonb),
                    error_code = :error_code,
                    error_message = :error_message
                WHERE id = :usage_log_id
                """
            ),
            {
                "usage_log_id": usage_log_id,
                "provider_response": self._to_json(provider_response or {}),
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    def _to_json(self, value: dict) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)
