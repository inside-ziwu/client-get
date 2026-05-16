import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


class InternalIdempotencyService:
    async def load(
        self,
        conn: AsyncConnection,
        *,
        service_name: str,
        request_id: str,
        endpoint: str,
    ) -> dict | None:
        result = await conn.execute(
            text(
                """
                SELECT response_body
                FROM service_idempotency_keys
                WHERE service_name = :service_name
                  AND request_id = :request_id
                  AND endpoint = :endpoint
                """
            ),
            {
                "service_name": service_name,
                "request_id": request_id,
                "endpoint": endpoint,
            },
        )
        row = result.mappings().first()
        return row["response_body"] if row else None

    async def save(
        self,
        conn: AsyncConnection,
        *,
        service_name: str,
        request_id: str,
        endpoint: str,
        response_body: dict,
    ) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO service_idempotency_keys
                  (id, service_name, request_id, endpoint, response_status, response_body)
                VALUES
                  (gen_random_uuid(), :service_name, :request_id, :endpoint, 200, CAST(:response_body AS jsonb))
                ON CONFLICT (service_name, request_id, endpoint) DO NOTHING
                """
            ),
            {
                "service_name": service_name,
                "request_id": request_id,
                "endpoint": endpoint,
                "response_body": json.dumps(response_body, ensure_ascii=False),
            },
        )

