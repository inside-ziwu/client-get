import json
from decimal import Decimal

import pycountry
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.audit_service import AuditService


class TenantOpsService:
    ALLOWED_BUSINESS_STATUSES = {"new", "in_group", "in_plan", "contacted"}
    ALLOWED_DATA_STATUSES = {"ready", "missing_contacts", "insufficient_data"}

    def __init__(self) -> None:
        self.audit = AuditService()

    async def dashboard_funnel(self, conn: AsyncConnection, tenant_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT business_status, count(*) AS total
                FROM tenant_companies
                WHERE tenant_id = :tenant_id
                  AND visibility_status = 'visible'
                GROUP BY business_status
                """
            ),
            {"tenant_id": tenant_id},
        )
        counts = {row["business_status"]: row["total"] for row in result.mappings().all()}
        ordered = ["new", "in_group", "in_plan", "contacted"]
        return {
            "stages": [{"status": status, "count": counts.get(status, 0)} for status in ordered],
            "total": sum(counts.values()),
        }

    async def companies_filters(self, conn: AsyncConnection, tenant_id: str) -> dict:
        params = {"tenant_id": tenant_id}
        base_join = """
            FROM tenant_companies tc
            JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
            WHERE tc.tenant_id = :tenant_id AND tc.visibility_status = 'visible'
        """

        r1 = await conn.execute(text(f"""
            SELECT
              array_remove(array_agg(DISTINCT COALESCE(NULLIF(wc.country_iso3, ''), wc.country)), NULL) AS countries,
              array_remove(array_agg(DISTINCT tc.business_status), NULL) AS business_statuses,
              array_remove(array_agg(DISTINCT tc.data_status), NULL) AS data_statuses
            {base_join}
        """), params)
        row1 = r1.mappings().one()

        r2 = await conn.execute(text(f"""
            SELECT array_remove(array_agg(DISTINCT wc.sub_industry), NULL) AS sub_industries
            {base_join} AND wc.sub_industry IS NOT NULL
        """), params)
        row2 = r2.mappings().one()

        r3 = await conn.execute(text("""
            SELECT array_remove(array_agg(DISTINCT tag), NULL) AS product_tags
            FROM tenant_companies tc
            JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
            CROSS JOIN jsonb_array_elements_text(wc.product_tags) AS tag
            WHERE tc.tenant_id = :tenant_id AND tc.visibility_status = 'visible'
              AND wc.product_tags IS NOT NULL AND jsonb_typeof(wc.product_tags) = 'array'
        """), params)
        row3 = r3.mappings().one()

        r4 = await conn.execute(text(f"""
            SELECT array_remove(array_agg(DISTINCT wc.grade), NULL) AS grades
            {base_join} AND wc.grade IS NOT NULL
        """), params)
        row4 = r4.mappings().one()

        return {
            "countries": sorted(row1["countries"] or []),
            "business_statuses": list(row1["business_statuses"] or []),
            "data_statuses": list(row1["data_statuses"] or []),
            "sub_industries": sorted(row2["sub_industries"] or []),
            "product_tags": sorted(row3["product_tags"] or []),
            "grades": sorted(row4["grades"] or []),
        }

    async def export_companies(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT tc.id, wc.company_name AS name, wc.country_iso3 AS country, wc.domain, tc.business_status, tc.data_status, tc.model_score, tc.score
                FROM tenant_companies tc
                JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
                WHERE tc.tenant_id = :tenant_id
                  AND tc.visibility_status = 'visible'
                ORDER BY tc.created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "country": row["country"],
                "domain": row["domain"],
                "business_status": row["business_status"],
                "data_status": row["data_status"],
                "model_score": self._decimal_to_float(row["model_score"]),
                "score": self._decimal_to_float(row["score"]),
            }
            for row in result.mappings().all()
        ]

    async def create_company(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        website = payload.get("website")
        domain = self._normalize_domain(website or payload.get("domain"))
        company_name = payload["name"]
        country_iso3 = self._normalize_country_iso3(payload.get("country"))

        await conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": (domain or "") + company_name + country_iso3},
        )

        existing = None
        if domain:
            existing = await conn.execute(
                text(
                    """
                    SELECT id FROM waimaotong_clean_companies
                    WHERE domain = :domain AND domain IS NOT NULL AND domain != ''
                    LIMIT 1
                    """
                ),
                {"domain": domain},
            )
            existing = existing.scalar_one_or_none()

        if existing is None:
            row = await conn.execute(
                text(
                    """
                    SELECT id FROM waimaotong_clean_companies
                    WHERE company_name = :company_name AND country_iso3 = :country_iso3
                    LIMIT 1
                    """
                ),
                {"company_name": company_name, "country_iso3": country_iso3},
            )
            existing = row.scalar_one_or_none()

        if existing is not None:
            actual_clean_company_id = existing
        else:
            founded_year_raw = payload.get("founded_year")
            try:
                founded_year = int(founded_year_raw) if founded_year_raw not in (None, "") else None
            except (ValueError, TypeError):
                founded_year = None

            cc_insert = await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_clean_companies
                      (company_name, english_name, country_iso3, domain, website, industry, product_tags,
                       phone, employee_size, founded_year, full_address, description)
                    VALUES
                      (:company_name, :english_name, :country_iso3, :domain, :website, :industry,
                       CAST(:product_tags AS jsonb),
                       :phone, :employee_size, :founded_year, :full_address, :description)
                    RETURNING id
                    """
                ),
                {
                    "company_name": company_name,
                    "english_name": payload.get("english_name"),
                    "country_iso3": country_iso3,
                    "domain": domain,
                    "website": website or (f"https://{domain}" if domain else None),
                    "industry": payload.get("industry"),
                    "product_tags": json.dumps(payload.get("product_tags") or payload.get("tags") or []),
                    "phone": payload.get("phone"),
                    "employee_size": payload.get("employee_size"),
                    "founded_year": founded_year,
                    "full_address": payload.get("full_address"),
                    "description": payload.get("description"),
                },
            )
            actual_clean_company_id = cc_insert.scalar_one()
        data_status = "ready" if payload.get("contact_email") or payload.get("contacts") else "missing_contacts"
        tc_insert = await conn.execute(
            text(
                """
                INSERT INTO tenant_companies
                  (tenant_id, clean_company_id, business_status, data_status, visibility_status, note, tags)
                VALUES
                  (:tenant_id, :clean_company_id, 'new', :data_status, 'visible', :note, CAST(:tags AS text[]))
                ON CONFLICT (tenant_id, clean_company_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_company_id": actual_clean_company_id,
                "data_status": data_status,
                "note": payload.get("note"),
                "tags": payload.get("tags") or [],
            },
        )
        tc_row = tc_insert.mappings().first()
        if tc_row is None:
            tc_row = (
                await conn.execute(
                    text(
                        """
                        SELECT id FROM tenant_companies
                        WHERE tenant_id = :tenant_id AND clean_company_id = :clean_company_id
                        LIMIT 1
                        """
                    ),
                    {"tenant_id": tenant_id, "clean_company_id": actual_clean_company_id},
                )
            ).mappings().one()
        actual_tenant_company_id = tc_row["id"]
        await self._ensure_contact_from_payload(
            conn,
            tenant_id=tenant_id,
            tenant_company_id=actual_tenant_company_id,
            payload=payload,
        )
        company = await self.get_company(conn, tenant_id, str(actual_tenant_company_id))
        await self.audit.write(
            conn,
            action="create",
            entity_type="tenant_company",
            entity_id=None,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value=company,
        )
        return company

    async def batch_import_companies(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
        created = []
        for item in items:
            created.append(await self.create_company(conn, tenant_id=tenant_id, user_id=user_id, payload=item))
        return {"created_count": len(created), "items": created}

    async def get_company(self, conn: AsyncConnection, tenant_id: str, company_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT
                  tc.id,
                  tc.tenant_id,
                  tc.business_status,
                  tc.data_status,
                  tc.model_score,
                  tc.score,
                  tc.note,
                  tc.tags,
                  tc.created_at,
                  tc.updated_at,
                  wc.id AS clean_company_id,
                  wc.company_name,
                  wc.english_name,
                  wc.country_iso3 AS country,
                  wc.domain,
                  wc.industry,
                  wc.sub_industry,
                  wc.product_tags AS product_keywords,
                  NULL::numeric AS data_completeness
                FROM tenant_companies tc
                JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
                WHERE tc.tenant_id = :tenant_id
                  AND tc.id = CAST(CAST(:company_id AS text) AS bigint)
                  AND tc.visibility_status = 'visible'
                """
            ),
            {"tenant_id": tenant_id, "company_id": company_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="公司不存在", status_code=404)
        contacts = await self.company_contacts(conn, tenant_id, company_id)
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "clean_company_id": str(row["clean_company_id"]),
            "name": row["company_name"],
            "name_en": row["english_name"],
            "country": row["country"],
            "domain": row["domain"],
            "industry": row["industry"],
            "industry_tags": [row["sub_industry"]] if row["sub_industry"] else [],
            "product_keywords": row["product_keywords"],
            "data_completeness": self._decimal_to_float(row["data_completeness"]),
            "business_status": row["business_status"],
            "data_status": row["data_status"],
            "model_score": self._decimal_to_float(row["model_score"]),
            "score": self._decimal_to_float(row["score"]),
            "note": row["note"],
            "tags": row["tags"],
            "contacts": contacts,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    async def blacklist_company(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        company_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        company = await self.get_company(conn, tenant_id, company_id)
        blacklist_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO company_blacklist
                  (id, tenant_id, shared_company_id, match_domain, match_name_pattern, reason, blocked_by)
                VALUES
                  (:id, :tenant_id, :shared_company_id, :match_domain, :match_name_pattern, :reason, :blocked_by)
                """
            ),
            {
                "id": blacklist_id,
                "tenant_id": tenant_id,
                "shared_company_id": company["clean_company_id"],
                "match_domain": company["domain"],
                "match_name_pattern": company["name"],
                "reason": payload.get("reason", "manual blacklist"),
                "blocked_by": user_id,
            },
        )
        await self.audit.write(
            conn,
            action="create",
            entity_type="company_blacklist",
            entity_id=blacklist_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"company_id": company_id, "reason": payload.get("reason", "manual blacklist")},
        )
        return {"blacklisted": True, "company_id": company_id}

    async def company_contacts(self, conn: AsyncConnection, tenant_id: str, company_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT tc.id, tc.clean_company_id, tc.contact_status, tc.is_sendable, tc.created_at,
                       wcc.id AS clean_contact_id, wcc.name, wcc.email, wcc.phone, wcc.position
                FROM tenant_contacts tc
                LEFT JOIN waimaotong_clean_contacts wcc ON wcc.id = tc.clean_contact_id
                JOIN tenant_companies tco
                  ON tco.tenant_id = tc.tenant_id
                 AND tco.clean_company_id = tc.clean_company_id
                WHERE tc.tenant_id = :tenant_id
                  AND tco.id = CAST(CAST(:company_id AS text) AS bigint)
                ORDER BY tc.created_at ASC
                """
            ),
            {"tenant_id": tenant_id, "company_id": company_id},
        )
        return [
            {
                "id": str(row["id"]),
                "clean_contact_id": str(row["clean_contact_id"]) if row["clean_contact_id"] else None,
                "tenant_company_id": str(company_id),
                "name": row["name"],
                "email": row["email"],
                "phone": row["phone"],
                "position": row["position"],
                "is_valid_email": row["email"] is not None,
                "status": row["contact_status"],
                "is_default": False,
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def get_prospect(self, conn: AsyncConnection, tenant_id: str, prospect_id: str) -> dict:
        return await self.get_company(conn, tenant_id, prospect_id)

    async def update_prospect(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        prospect_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        business_status = payload.get("business_status")
        if business_status is not None:
            self._validate_business_status(business_status)

        score_adjustment = payload.get("score_adjustment")
        if score_adjustment is not None:
            if not isinstance(score_adjustment, int) or not (-20 <= score_adjustment <= 20):
                raise AppError(code="VALIDATION_ERROR", message="score_adjustment 须为 -20 ~ +20 的整数", status_code=422)

        before = await self.get_prospect(conn, tenant_id, prospect_id)
        await conn.execute(
            text(
                """
                UPDATE tenant_companies
                SET note = COALESCE(:note, note),
                    tags = CAST(:tags AS text[]),
                    business_status = COALESCE(:business_status, business_status),
                    score_adjustment = COALESCE(:score_adjustment, score_adjustment),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = CAST(CAST(:prospect_id AS text) AS bigint)
                """
            ),
            {
                "tenant_id": tenant_id,
                "prospect_id": prospect_id,
                "note": payload.get("note"),
                "tags": payload.get("tags", before["tags"]),
                "business_status": business_status,
                "score_adjustment": score_adjustment,
            },
        )
        after = await self.get_prospect(conn, tenant_id, prospect_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="tenant_company",
            entity_id=None,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def set_prospect_status(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        prospect_id: str,
        status: str,
        user_id: str,
    ) -> dict:
        raise AppError(code="UNSUPPORTED_OPERATION", message="旧 select/exclude 状态入口已停用", status_code=410)

    async def set_default_contact(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        contact_id: str,
        user_id: str,
    ) -> dict:
        raise AppError(code="UNSUPPORTED_OPERATION", message="当前联系人模型不支持默认联系人标记", status_code=410)

    async def list_groups(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, description, auto_rules, member_count, created_at, updated_at
                FROM groups
                WHERE tenant_id = :tenant_id AND deleted_at IS NULL
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "auto_rules": row["auto_rules"],
                "member_count": row["member_count"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def create_group(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        group_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO groups (id, tenant_id, name, description, auto_rules, member_count)
                VALUES (:id, :tenant_id, :name, :description, CAST(:auto_rules AS jsonb), 0)
                """
            ),
            {
                "id": group_id,
                "tenant_id": tenant_id,
                "name": payload["name"],
                "description": payload.get("description"),
                "auto_rules": self._to_json(payload.get("auto_rules", {})),
            },
        )
        group = await self.get_group(conn, tenant_id, group_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="group",
            entity_id=group_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value=group,
        )
        return group

    async def get_group(self, conn: AsyncConnection, tenant_id: str, group_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, name, description, auto_rules, member_count, created_at, updated_at
                FROM groups
                WHERE tenant_id = :tenant_id AND id = :group_id AND deleted_at IS NULL
                """
            ),
            {"tenant_id": tenant_id, "group_id": group_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="分组不存在", status_code=404)
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"],
            "auto_rules": row["auto_rules"],
            "member_count": row["member_count"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    async def update_group(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        group_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        before = await self.get_group(conn, tenant_id, group_id)
        await conn.execute(
            text(
                """
                UPDATE groups
                SET name = COALESCE(:name, name),
                    description = COALESCE(:description, description),
                    auto_rules = CAST(:auto_rules AS jsonb),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :group_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "group_id": group_id,
                "name": payload.get("name"),
                "description": payload.get("description"),
                "auto_rules": self._to_json(payload.get("auto_rules", before["auto_rules"])),
            },
        )
        after = await self.get_group(conn, tenant_id, group_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="group",
            entity_id=group_id,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_group(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        group_id: str,
        user_id: str,
    ) -> None:
        before = await self.get_group(conn, tenant_id, group_id)
        await conn.execute(
            text(
                """
                UPDATE groups
                SET deleted_at = now(), updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :group_id
                """
            ),
            {"tenant_id": tenant_id, "group_id": group_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="group",
            entity_id=group_id,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
        )

    async def list_group_members(self, conn: AsyncConnection, tenant_id: str, group_id: str) -> list[dict]:
        await self.get_group(conn, tenant_id, group_id)
        result = await conn.execute(
            text(
                """
                SELECT gm.id, gm.group_id, gm.tenant_company_id, gm.tenant_contact_id, gm.added_by, gm.created_at,
                       wc.company_name AS company_name, wcc.email AS contact_email, wcc.name AS contact_name
                FROM group_members gm
                JOIN tenant_companies tc ON tc.id = gm.tenant_company_id
                JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
                LEFT JOIN tenant_contacts tco ON tco.id = gm.tenant_contact_id
                LEFT JOIN waimaotong_clean_contacts wcc ON wcc.id = tco.clean_contact_id
                WHERE gm.tenant_id = :tenant_id
                  AND gm.group_id = :group_id
                  AND tc.visibility_status = 'visible'
                ORDER BY gm.created_at ASC
                """
            ),
            {"tenant_id": tenant_id, "group_id": group_id},
        )
        return [
            {
                "id": str(row["id"]),
                "group_id": str(row["group_id"]),
                "tenant_company_id": str(row["tenant_company_id"]),
                "tenant_contact_id": str(row["tenant_contact_id"]) if row["tenant_contact_id"] else None,
                "added_by": row["added_by"],
                "company_name": row["company_name"],
                "contact_name": row["contact_name"],
                "contact_email": row["contact_email"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def add_group_members(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        group_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        await self.get_group(conn, tenant_id, group_id)
        overrides = payload.get("tenant_contact_overrides", {})
        added = 0
        for company_id in payload.get("tenant_company_ids", []):
            await self._assert_visible_tenant_company(conn, tenant_id, company_id)
            contact_id = overrides.get(company_id) or await self._select_default_contact_id(conn, tenant_id, company_id)
            await conn.execute(
                text(
                    """
                    UPDATE tenant_companies
                    SET business_status = 'in_group',
                        updated_at = now()
                    WHERE tenant_id = :tenant_id
                      AND id = :tenant_company_id
                      AND visibility_status = 'visible';
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "tenant_company_id": int(company_id),
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO group_members
                      (id, tenant_id, group_id, tenant_company_id, tenant_contact_id, added_by)
                    VALUES
                      (:id, :tenant_id, :group_id, :tenant_company_id, :tenant_contact_id, 'manual')
                    ON CONFLICT (group_id, tenant_company_id) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "group_id": group_id,
                    "tenant_company_id": int(company_id),
                    "tenant_contact_id": int(contact_id) if contact_id is not None else None,
                },
            )
            added += 1
        await self._refresh_group_member_count(conn, tenant_id, group_id)
        members = await self.list_group_members(conn, tenant_id, group_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="group_members",
            entity_id=group_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"member_count": len(members)},
        )
        return {"added_count": added, "members": members}

    async def remove_group_members(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        group_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        await self.get_group(conn, tenant_id, group_id)
        removed = 0
        for company_id in payload.get("tenant_company_ids", []):
            result = await conn.execute(
                text(
                    """
                    DELETE FROM group_members
                    WHERE tenant_id = :tenant_id AND group_id = :group_id AND tenant_company_id = :tenant_company_id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "group_id": group_id,
                    "tenant_company_id": int(company_id),
                },
            )
            removed += result.rowcount or 0
            if result.rowcount:
                await conn.execute(
                    text(
                        """
                        UPDATE tenant_companies tc
                        SET business_status = 'new',
                            updated_at = now()
                        WHERE tc.tenant_id = :tenant_id
                          AND tc.id = :tenant_company_id
                          AND tc.business_status = 'in_group'
                          AND NOT EXISTS (
                            SELECT 1
                            FROM group_members gm
                            WHERE gm.tenant_id = :tenant_id
                              AND gm.tenant_company_id = tc.id
                          )
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "tenant_company_id": int(company_id),
                    },
                )
        await self._refresh_group_member_count(conn, tenant_id, group_id)
        members = await self.list_group_members(conn, tenant_id, group_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="group_members",
            entity_id=group_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"member_count": len(members)},
        )
        return {"removed_count": removed, "members": members}

    async def list_domains(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, domain, verification_status, warmup_level, daily_limit, total_sent,
                       bounce_rate, complaint_rate, open_rate, created_at, updated_at
                FROM domain_warmup_status
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "domain": row["domain"],
                "verification_status": row["verification_status"],
                "warmup_level": row["warmup_level"],
                "daily_limit": row["daily_limit"],
                "total_sent": row["total_sent"],
                "bounce_rate": self._decimal_to_float(row["bounce_rate"]),
                "complaint_rate": self._decimal_to_float(row["complaint_rate"]),
                "open_rate": self._decimal_to_float(row["open_rate"]),
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def get_domain(self, conn: AsyncConnection, tenant_id: str, domain_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, domain, verification_status, spf_record, dkim_record, dmarc_record,
                       dns_verified_at, dns_last_checked_at, warmup_level, daily_limit, total_sent,
                       bounce_rate, complaint_rate, open_rate, level_changed_at, created_at, updated_at
                FROM domain_warmup_status
                WHERE tenant_id = :tenant_id AND id = :domain_id
                """
            ),
            {"tenant_id": tenant_id, "domain_id": domain_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="域名不存在", status_code=404)
        return {
            "id": str(row["id"]),
            "domain": row["domain"],
            "verification_status": row["verification_status"],
            "spf_record": row["spf_record"],
            "dkim_record": row["dkim_record"],
            "dmarc_record": row["dmarc_record"],
            "dns_verified_at": row["dns_verified_at"].isoformat() if row["dns_verified_at"] else None,
            "dns_last_checked_at": row["dns_last_checked_at"].isoformat() if row["dns_last_checked_at"] else None,
            "warmup_level": row["warmup_level"],
            "daily_limit": row["daily_limit"],
            "total_sent": row["total_sent"],
            "bounce_rate": self._decimal_to_float(row["bounce_rate"]),
            "complaint_rate": self._decimal_to_float(row["complaint_rate"]),
            "open_rate": self._decimal_to_float(row["open_rate"]),
            "level_changed_at": row["level_changed_at"].isoformat() if row["level_changed_at"] else None,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    async def get_domain_history(self, conn: AsyncConnection, tenant_id: str, domain_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, warmup_level, daily_limit, total_sent, bounce_rate, complaint_rate, open_rate,
                       change_type, change_reason, snapshot_at, created_at
                FROM domain_warmup_history
                WHERE tenant_id = :tenant_id AND warmup_status_id = :domain_id
                ORDER BY snapshot_at DESC
                """
            ),
            {"tenant_id": tenant_id, "domain_id": domain_id},
        )
        return [
            {
                "id": str(row["id"]),
                "warmup_level": row["warmup_level"],
                "daily_limit": row["daily_limit"],
                "total_sent": row["total_sent"],
                "bounce_rate": self._decimal_to_float(row["bounce_rate"]),
                "complaint_rate": self._decimal_to_float(row["complaint_rate"]),
                "open_rate": self._decimal_to_float(row["open_rate"]),
                "change_type": row["change_type"],
                "change_reason": row["change_reason"],
                "snapshot_at": row["snapshot_at"].isoformat(),
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def ai_usage_summary(self, conn: AsyncConnection, tenant_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT usage_type,
                       count(*) AS total_calls,
                       COALESCE(sum(actual_cost), 0) AS total_cost,
                       COALESCE(sum(total_tokens), 0) AS total_tokens
                FROM ai_usage_logs
                WHERE tenant_id = :tenant_id AND status = 'completed'
                GROUP BY usage_type
                ORDER BY usage_type
                """
            ),
            {"tenant_id": tenant_id},
        )
        items = [
            {
                "usage_type": row["usage_type"],
                "total_calls": row["total_calls"],
                "total_cost": self._decimal_to_float(row["total_cost"]),
                "total_tokens": row["total_tokens"],
            }
            for row in result.mappings().all()
        ]
        return {"items": items}

    async def ai_usage_trend(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT date(created_at) AS usage_date,
                       count(*) AS total_calls,
                       COALESCE(sum(actual_cost), 0) AS total_cost
                FROM ai_usage_logs
                WHERE tenant_id = :tenant_id AND status = 'completed'
                GROUP BY date(created_at)
                ORDER BY usage_date DESC
                LIMIT 30
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "usage_date": row["usage_date"].isoformat(),
                "total_calls": row["total_calls"],
                "total_cost": self._decimal_to_float(row["total_cost"]),
            }
            for row in result.mappings().all()
        ]

    async def list_notifications(self, conn: AsyncConnection, tenant_id: str, user_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, title, content, category, entity_type, entity_id, is_read, read_at, created_at
                FROM notifications
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "content": row["content"],
                "category": row["category"],
                "entity_type": row["entity_type"],
                "entity_id": str(row["entity_id"]) if row["entity_id"] else None,
                "is_read": row["is_read"],
                "read_at": row["read_at"].isoformat() if row["read_at"] else None,
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def mark_notification_read(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        notification_id: str,
    ) -> dict:
        await conn.execute(
            text(
                """
                UPDATE notifications
                SET is_read = true, read_at = now()
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND id = :notification_id
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "notification_id": notification_id},
        )
        return {"id": notification_id, "is_read": True}

    async def mark_all_notifications_read(self, conn: AsyncConnection, *, tenant_id: str, user_id: str) -> dict:
        await conn.execute(
            text(
                """
                UPDATE notifications
                SET is_read = true, read_at = now()
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND is_read = false
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        return {"all_read": True}

    async def _ensure_contact_from_payload(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        tenant_company_id: int,
        payload: dict,
    ) -> None:
        contacts = payload.get("contacts") or []
        if not contacts and payload.get("contact_email"):
            contacts = [
                {
                    "name": payload.get("contact_name"),
                    "email": payload.get("contact_email"),
                    "title": payload.get("contact_title"),
                }
            ]
        for index, contact in enumerate(contacts):
            company_result = await conn.execute(
                text(
                    """
                    SELECT tc.clean_company_id, wc.sys_company_id
                    FROM tenant_companies tc
                    JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
                    WHERE tc.id = :tenant_company_id
                    """
                ),
                {"tenant_company_id": tenant_company_id},
            )
            company_row = company_result.mappings().one()

            email = contact.get("email") or None
            if email:
                existing = await conn.execute(
                    text(
                        """
                        SELECT id FROM waimaotong_clean_contacts
                        WHERE sys_company_id = :sys_company_id AND email = :email
                        LIMIT 1
                        """
                    ),
                    {"sys_company_id": company_row["sys_company_id"], "email": email},
                )
                clean_contact_id = existing.scalar_one_or_none()
            else:
                clean_contact_id = None

            if clean_contact_id is None:
                insert_result = await conn.execute(
                    text(
                        """
                        INSERT INTO waimaotong_clean_contacts
                          (sys_company_id, name, email, position)
                        VALUES
                          (:sys_company_id, :name, :email, :position)
                        RETURNING id
                        """
                    ),
                    {
                        "sys_company_id": company_row["sys_company_id"],
                        "name": contact.get("name"),
                        "email": email,
                        "position": contact.get("title"),
                    },
                )
                clean_contact_id = insert_result.scalar_one()

            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_contacts
                      (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                    VALUES
                      (:tenant_id, :clean_contact_id, :clean_company_id, 'available', true)
                    ON CONFLICT (tenant_id, clean_contact_id) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "clean_contact_id": clean_contact_id,
                    "clean_company_id": company_row["clean_company_id"],
                },
            )

    async def _select_default_contact_id(self, conn: AsyncConnection, tenant_id: str, company_id: str) -> str | None:
        result = await conn.execute(
            text(
                """
                SELECT id
                FROM tenant_contacts
                WHERE tenant_id = :tenant_id
                  AND clean_company_id = (
                    SELECT clean_company_id
                    FROM tenant_companies
                    WHERE tenant_id = :tenant_id
                      AND id = CAST(CAST(:company_id AS text) AS bigint)
                  )
                ORDER BY created_at ASC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "company_id": company_id},
        )
        row = result.mappings().first()
        return str(row["id"]) if row else None

    async def _assert_visible_tenant_company(self, conn: AsyncConnection, tenant_id: str, company_id: str) -> None:
        result = await conn.execute(
            text(
                """
                SELECT 1
                FROM tenant_companies
                WHERE tenant_id = :tenant_id
                  AND id = CAST(CAST(:company_id AS text) AS bigint)
                  AND visibility_status = 'visible'
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "company_id": company_id},
        )
        if result.first() is None:
            raise AppError(code="NOT_FOUND", message="公司不存在", status_code=404)

    def _validate_business_status(self, value: str) -> None:
        if value not in self.ALLOWED_BUSINESS_STATUSES:
            raise AppError(code="VALIDATION_ERROR", message="business_status 不合法", status_code=422)

    async def _refresh_group_member_count(self, conn: AsyncConnection, tenant_id: str, group_id: str) -> None:
        count = (
            await conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM group_members
                    WHERE tenant_id = :tenant_id AND group_id = :group_id
                    """
                ),
                {"tenant_id": tenant_id, "group_id": group_id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                UPDATE groups
                SET member_count = :member_count, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :group_id
                """
            ),
            {"tenant_id": tenant_id, "group_id": group_id, "member_count": count},
        )

    def _normalize_domain(self, value: str | None) -> str | None:
        if not value:
            return None
        domain = value.replace("https://", "").replace("http://", "").strip("/").lower()
        return domain or None

    def _normalize_country_iso3(self, value: str | None) -> str:
        if not value or not value.strip():
            return "UNK"
        normalized = value.strip().upper()
        if len(normalized) == 3 and normalized.isalpha():
            country = pycountry.countries.get(alpha_3=normalized)
        elif len(normalized) == 2 and normalized.isalpha():
            country = pycountry.countries.get(alpha_2=normalized)
        else:
            country = None
        if country is None:
            raise AppError(code="VALIDATION_ERROR", message="国家需使用 ISO2 或 ISO3 代码", status_code=422)
        return country.alpha_3

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _decimal_to_float(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None
