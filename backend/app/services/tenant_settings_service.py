import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid


class TenantSettingsService:
    async def get_scoring_templates(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, is_active, dimensions, grade_thresholds, version, created_at, updated_at
                FROM scoring_templates
                WHERE tenant_id = :tenant_id
                ORDER BY is_active DESC, updated_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "is_active": row["is_active"],
                "dimensions": row["dimensions"],
                "grade_thresholds": row["grade_thresholds"],
                "version": row["version"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def update_scoring_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        template_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT name, dimensions, grade_thresholds, version
                FROM scoring_templates
                WHERE id = :template_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "template_id": template_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="评分模板不存在", status_code=404)
        name = payload.get("name") or row["name"]
        grade_thresholds = payload.get("grade_thresholds") or row["grade_thresholds"]
        # 租户只能修改 dimensions 中的 score 值，不能改 condition/value/min/max/key/name
        incoming_dims = payload.get("dimensions")
        existing_dims = row["dimensions"]
        if isinstance(existing_dims, str):
            import json as _json
            existing_dims = _json.loads(existing_dims)
        if incoming_dims and isinstance(incoming_dims, list):
            for i, dim in enumerate(existing_dims):
                if i >= len(incoming_dims):
                    break
                incoming_conditions = incoming_dims[i].get("conditions") or incoming_dims[i].get("rules") or []
                existing_conditions = dim.get("conditions") or dim.get("rules") or []
                for j, cond in enumerate(existing_conditions):
                    if j < len(incoming_conditions):
                        cond["score"] = incoming_conditions[j].get("score", cond.get("score", 0))
        dimensions = existing_dims
        version = row["version"] + 1
        await conn.execute(
            text(
                """
                UPDATE scoring_templates
                SET name = :name,
                    dimensions = CAST(:dimensions AS jsonb),
                    grade_thresholds = CAST(:grade_thresholds AS jsonb),
                    version = :version,
                    updated_at = now()
                WHERE id = :template_id AND tenant_id = :tenant_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "template_id": template_id,
                "name": name,
                "dimensions": self._to_json(dimensions),
                "grade_thresholds": self._to_json(grade_thresholds),
                "version": version,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO scoring_template_versions
                  (id, tenant_id, template_id, version, dimensions, grade_thresholds, changed_by, change_reason)
                VALUES
                  (:id, :tenant_id, :template_id, :version, CAST(:dimensions AS jsonb), CAST(:grade_thresholds AS jsonb), :changed_by, 'tenant update')
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": tenant_id,
                "template_id": template_id,
                "version": version,
                "dimensions": self._to_json(dimensions),
                "grade_thresholds": self._to_json(grade_thresholds),
                "changed_by": user_id,
            },
        )
        return {"id": template_id, "name": name, "dimensions": dimensions, "grade_thresholds": grade_thresholds, "version": version}

    async def get_contact_rules(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, is_active, rules, version, updated_at
                FROM contact_rules
                WHERE tenant_id = :tenant_id
                ORDER BY is_active DESC, updated_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "is_active": row["is_active"],
                "rules": row["rules"],
                "version": row["version"],
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def update_contact_rules(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        rule_id: str,
        payload: dict,
    ) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT name, version
                FROM contact_rules
                WHERE id = :rule_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "rule_id": rule_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="联系人规则不存在", status_code=404)
        name = payload.get("name") or row["name"]
        version = row["version"] + 1
        await conn.execute(
            text(
                """
                UPDATE contact_rules
                SET name = :name,
                    rules = CAST(:rules AS jsonb),
                    version = :version,
                    updated_at = now()
                WHERE id = :rule_id AND tenant_id = :tenant_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "rule_id": rule_id,
                "name": name,
                "rules": self._to_json(payload["rules"]),
                "version": version,
            },
        )
        return {"id": rule_id, "name": name, "rules": payload["rules"], "version": version}

    async def complete_onboarding(self, conn: AsyncConnection, *, tenant_id: str) -> None:
        # 引导页仅作提示,不设进入门槛(2026-07-03 移除关键词前置校验,
        # 见 openspec change update-onboarding-remove-keyword-gate)
        await conn.execute(
            text(
                """
                UPDATE tenants
                SET needs_onboarding = false,
                    updated_at = now()
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)
