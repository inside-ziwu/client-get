import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.keyword_service import (
    bind_tenant_keyword,
    get_or_create_keyword_master,
    lookup_keyword_master,
    normalize_keyword,
)
from app.workers.fan_out import hide_tenant_companies_for_cancelled_keyword, run_fan_out_for_tenant_keyword


class TenantSettingsService:
    async def list_keywords(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, keyword, keyword_normalized, status, created_at
                FROM collection_keywords
                WHERE tenant_id = :tenant_id AND status != 'deleted'
                ORDER BY created_at DESC
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
        await bind_tenant_keyword(
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

        keyword_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO collection_keywords
                  (id, tenant_id, keyword, keyword_normalized, status, created_by, keyword_master_id)
                VALUES
                  (:id, :tenant_id, :keyword, :keyword_normalized, 'active', :created_by, :keyword_master_id)
                """
            ),
            {
                "id": keyword_id,
                "tenant_id": tenant_id,
                "keyword": keyword,
                "keyword_normalized": keyword_normalized,
                "created_by": user_id,
                "keyword_master_id": keyword_master_id,
            },
        )
        return {
            "id": keyword_id,
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
                SELECT keyword, status
                FROM collection_keywords
                WHERE id = :keyword_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "keyword_id": keyword_id},
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
        await bind_tenant_keyword(
            conn,
            tenant_id=tenant_id,
            keyword_master_id=keyword_master_id,
            keyword_raw=keyword,
        )
        await run_fan_out_for_tenant_keyword(
            conn,
            tenant_id=tenant_id,
            keyword_master_id=keyword_master_id,
        )
        await conn.execute(
            text(
                """
                UPDATE collection_keywords
                SET keyword = :keyword,
                    keyword_normalized = :keyword_normalized,
                    keyword_master_id = :keyword_master_id,
                    status = :status,
                    updated_at = now()
                WHERE id = :keyword_id AND tenant_id = :tenant_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "keyword_id": keyword_id,
                "keyword": keyword,
                "keyword_normalized": keyword_normalized,
                "keyword_master_id": keyword_master_id,
                "status": status,
            },
        )
        return {
            "id": keyword_id,
            "keyword": keyword,
            "keyword_normalized": keyword_normalized,
            "status": status,
        }

    async def delete_keyword(self, conn: AsyncConnection, *, tenant_id: str, keyword_id: str) -> None:
        existing = await conn.execute(
            text(
                """
                SELECT keyword_master_id
                FROM collection_keywords
                WHERE id = :keyword_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "keyword_id": keyword_id},
        )
        row = existing.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="关键词不存在", status_code=404)

        await conn.execute(
            text(
                """
                UPDATE collection_keywords
                SET status = 'deleted', updated_at = now()
                WHERE id = :keyword_id AND tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id, "keyword_id": keyword_id},
        )
        if row["keyword_master_id"]:
            await conn.execute(
                text(
                    """
                    UPDATE tenant_keyword
                    SET status = 'deleted'
                    WHERE tenant_id = :tenant_id
                      AND keyword_master_id = :keyword_master_id
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": row["keyword_master_id"]},
            )
            await hide_tenant_companies_for_cancelled_keyword(
                conn,
                tenant_id=tenant_id,
                keyword_master_id=str(row["keyword_master_id"]),
            )

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
                    FROM collection_keywords
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
