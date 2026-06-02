import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.services.keyword_service import (
    bind_tenant_keyword,
    get_or_create_keyword_master,
    lookup_keyword_master,
    normalize_keyword,
)
from app.workers.fan_out import run_fan_out_for_tenant_keyword


class TenantSettingsService:
    async def list_keywords(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT tk.id, km.keyword, km.keyword_normalized, tk.status, tk.created_at
                FROM tenant_keyword tk
                JOIN keyword_master km ON km.id = tk.keyword_master_id
                WHERE tk.tenant_id = :tenant_id AND tk.status != 'deleted'
                ORDER BY tk.created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "keyword": row["keyword"],
                "keyword_normalized": row["keyword_normalized"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def create_keyword(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        keyword = payload["keyword"].strip()
        keyword_normalized = normalize_keyword(keyword)
        existing_master = await lookup_keyword_master(conn, keyword_normalized)
        keyword_master_id = await get_or_create_keyword_master(
            conn,
            keyword=keyword,
            keyword_normalized=keyword_normalized,
        )
        tenant_keyword_id = await bind_tenant_keyword(
            conn,
            tenant_id=tenant_id,
            keyword_master_id=keyword_master_id,
            keyword_raw=keyword,
            created_by=user_id,
        )
        await run_fan_out_for_tenant_keyword(
            conn,
            tenant_id=tenant_id,
            keyword_master_id=keyword_master_id,
        )
        return {
            "id": str(tenant_keyword_id),
            "keyword": keyword,
            "keyword_normalized": keyword_normalized,
            "status": "active",
            "collection_hint": {
                "matched": existing_master is not None,
                "company_count": int((existing_master or {}).get("company_count") or 0),
                "tenant_count": int((existing_master or {}).get("tenant_count") or 0),
            },
        }

    async def update_keyword(self, conn: AsyncConnection, *, tenant_id: str, keyword_id: str, payload: dict) -> dict:
        existing = await conn.execute(
            text(
                """
                SELECT tk.id, km.keyword, tk.status, tk.keyword_master_id
                FROM tenant_keyword tk
                JOIN keyword_master km ON km.id = tk.keyword_master_id
                WHERE tk.id = :keyword_id AND tk.tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "keyword_id": int(keyword_id)},
        )
        row = existing.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="关键词不存在", status_code=404)
        keyword = (payload.get("keyword") or row["keyword"]).strip()
        keyword_normalized = normalize_keyword(keyword)
        status = payload.get("status") or row["status"]
        keyword_master_id = await get_or_create_keyword_master(
            conn,
            keyword=keyword,
            keyword_normalized=keyword_normalized,
        )
        await conn.execute(
            text(
                """
                UPDATE tenant_keyword
                SET keyword_master_id = :keyword_master_id,
                    keyword_raw = :keyword,
                    status = :status
                WHERE id = :keyword_id AND tenant_id = :tenant_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "keyword_id": int(keyword_id),
                "keyword": keyword,
                "keyword_master_id": keyword_master_id,
                "status": status,
            },
        )
        await run_fan_out_for_tenant_keyword(
            conn,
            tenant_id=tenant_id,
            keyword_master_id=keyword_master_id,
        )
        return {
            "id": keyword_id,
            "keyword": keyword,
            "keyword_normalized": keyword_normalized,
            "status": status,
        }

    async def delete_keyword(self, conn: AsyncConnection, *, tenant_id: str, keyword_id: str) -> None:
        result = await conn.execute(
            text(
                """
                UPDATE tenant_keyword
                SET status = 'deleted'
                WHERE id = :keyword_id AND tenant_id = :tenant_id
                RETURNING id
                """
            ),
            {"tenant_id": tenant_id, "keyword_id": int(keyword_id)},
        )
        if result.first() is None:
            raise AppError(code="NOT_FOUND", message="关键词不存在", status_code=404)

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
        dimensions = payload.get("dimensions") or row["dimensions"]
        grade_thresholds = payload.get("grade_thresholds") or row["grade_thresholds"]
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
        keyword_count = (
            await conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM tenant_keyword
                    WHERE tenant_id = :tenant_id AND status = 'active'
                    """
                ),
                {"tenant_id": tenant_id},
            )
        ).scalar_one()
        if keyword_count < 1:
            raise AppError(code="VALIDATION_ERROR", message="至少需要一个有效关键词才能完成向导", status_code=422)
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
