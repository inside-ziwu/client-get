import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.ids import new_uuid


class AuditService:
    async def write(
        self,
        conn: AsyncConnection,
        *,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        platform_user_id: str | None = None,
        old_value: dict | list | None = None,
        new_value: dict | list | None = None,
    ) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO audit_logs
                  (id, tenant_id, user_id, platform_user_id, action, entity_type, entity_id, old_value, new_value)
                VALUES
                  (:id, :tenant_id, :user_id, :platform_user_id, :action, :entity_type, :entity_id,
                   CAST(:old_value AS jsonb), CAST(:new_value AS jsonb))
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": tenant_id,
                "user_id": user_id,
                "platform_user_id": platform_user_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "old_value": self._to_json(old_value),
                "new_value": self._to_json(new_value),
            },
        )

    def _to_json(self, value: dict | list | None) -> str:
        if value is None:
            return "null"
        return json.dumps(value, ensure_ascii=False)
