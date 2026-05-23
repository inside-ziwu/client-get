from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.services.company_filter_sql import append_employee_count_range
from app.services.tenant_ai_provider_service import TenantAiProviderService


class TenantQueryService:
    def __init__(self) -> None:
        self.ai_provider = TenantAiProviderService()

    def _parse_clean_company_id(self, clean_company_id: str | int) -> int:
        try:
            return int(clean_company_id)
        except (TypeError, ValueError):
            raise AppError(code="NOT_FOUND", message="公司不存在", status_code=404) from None

    def _parse_filter_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise AppError(code="INVALID_FILTER", message="日期筛选格式应为 YYYY-MM-DD", status_code=400) from None

    async def dashboard_overview(self, conn: AsyncConnection, tenant_id: str, is_admin: bool) -> dict:
        counts = await conn.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM tenant_companies WHERE tenant_id = :tenant_id) AS total_companies,
                  (SELECT count(*) FROM tenant_companies WHERE tenant_id = :tenant_id AND score IS NOT NULL) AS scored_companies,
                  (SELECT count(*) FROM sending_plans WHERE tenant_id = :tenant_id AND deleted_at IS NULL) AS total_plans,
                  (SELECT count(*) FROM sending_plans WHERE tenant_id = :tenant_id AND status = 'running' AND deleted_at IS NULL) AS running_plans,
                  (SELECT count(*) FROM notifications WHERE tenant_id = :tenant_id AND is_read = false) AS unread_notifications
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = counts.mappings().one()
        return {
            "total_companies": row["total_companies"],
            "scored_companies": row["scored_companies"],
            "total_plans": row["total_plans"],
            "running_plans": row["running_plans"],
            "unread_notifications": row["unread_notifications"],
            "is_admin": is_admin,
        }

    async def companies(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        *,
        # C5：10 项筛选参数
        keyword: str | None = None,
        country_iso3: str | None = None,
        countries: list[str] | None = None,
        industry_tags: list[str] | None = None,
        sub_industries: list[str] | None = None,
        product_tags: list[str] | None = None,
        source_type: str | None = None,
        sources: list[str] | None = None,
        incorporation_date_from: str | None = None,
        incorporation_date_to: str | None = None,
        reg_capital_min: float | None = None,
        reg_capital_max: float | None = None,
        employee_num: str | None = None,
        trade_amount_min: float | None = None,
        trade_amount_max: float | None = None,
        trade_count_min: int | None = None,
        trade_count_max: int | None = None,
        business_status: str | None = None,
        data_status: str | None = None,
        score_min: float | None = None,
        score_max: float | None = None,
        contacts_count_min: int | None = None,
        contacts_count_max: int | None = None,
        contact_count_min: int | None = None,
        contact_count_max: int | None = None,
        founded_year_from: int | None = None,
        founded_year_to: int | None = None,
        employee_scales: list[str] | None = None,
        employee_count_min: int | None = None,
        employee_count_max: int | None = None,
        pcb_supplier_presence: str | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        limit: int = 50,
        cursor: str | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        rows, _total = await self.companies_page(
            conn,
            tenant_id,
            keyword=keyword,
            country_iso3=country_iso3,
            countries=countries,
            industry_tags=industry_tags,
            sub_industries=sub_industries,
            product_tags=product_tags,
            source_type=source_type,
            sources=sources,
            incorporation_date_from=incorporation_date_from,
            incorporation_date_to=incorporation_date_to,
            reg_capital_min=reg_capital_min,
            reg_capital_max=reg_capital_max,
            employee_num=employee_num,
            trade_amount_min=trade_amount_min,
            trade_amount_max=trade_amount_max,
            trade_count_min=trade_count_min,
            trade_count_max=trade_count_max,
            business_status=business_status,
            data_status=data_status,
            score_min=score_min,
            score_max=score_max,
            contacts_count_min=contacts_count_min,
            contacts_count_max=contacts_count_max,
            contact_count_min=contact_count_min,
            contact_count_max=contact_count_max,
            founded_year_from=founded_year_from,
            founded_year_to=founded_year_to,
            employee_scales=employee_scales,
            employee_count_min=employee_count_min,
            employee_count_max=employee_count_max,
            pcb_supplier_presence=pcb_supplier_presence,
            min_score=min_score,
            max_score=max_score,
            limit=limit,
            cursor=cursor,
            offset=offset,
        )
        return rows

    async def companies_page(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        *,
        keyword: str | None = None,
        country_iso3: str | None = None,
        countries: list[str] | None = None,
        industry_tags: list[str] | None = None,
        sub_industries: list[str] | None = None,
        product_tags: list[str] | None = None,
        source_type: str | None = None,
        sources: list[str] | None = None,
        incorporation_date_from: str | None = None,
        incorporation_date_to: str | None = None,
        reg_capital_min: float | None = None,
        reg_capital_max: float | None = None,
        employee_num: str | None = None,
        trade_amount_min: float | None = None,
        trade_amount_max: float | None = None,
        trade_count_min: int | None = None,
        trade_count_max: int | None = None,
        business_status: str | None = None,
        data_status: str | None = None,
        score_min: float | None = None,
        score_max: float | None = None,
        contacts_count_min: int | None = None,
        contacts_count_max: int | None = None,
        contact_count_min: int | None = None,
        contact_count_max: int | None = None,
        founded_year_from: int | None = None,
        founded_year_to: int | None = None,
        employee_scales: list[str] | None = None,
        employee_count_min: int | None = None,
        employee_count_max: int | None = None,
        pcb_supplier_presence: str | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        grade: str | None = None,
        group_id: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
        offset: int | None = None,
    ) -> tuple[list[dict], int]:
        where_clauses = [
            "tc.tenant_id = :tenant_id",
        ]
        params: dict = {"tenant_id": tenant_id, "limit": limit}
        if offset is not None:
            params["offset"] = offset

        if keyword:
            where_clauses.append("(wc.company_name ILIKE :keyword OR wc.domain ILIKE :keyword OR wc.website ILIKE :keyword)")
            params["keyword"] = f"%{keyword}%"

        if min_score is not None:
            where_clauses.append("tc.score >= :min_score")
            params["min_score"] = min_score
        if max_score is not None:
            where_clauses.append("tc.score <= :max_score")
            params["max_score"] = max_score
        if score_min is not None:
            where_clauses.append("tc.score >= :score_min")
            params["score_min"] = score_min
        if score_max is not None:
            where_clauses.append("tc.score <= :score_max")
            params["score_max"] = score_max

        if business_status:
            where_clauses.append("tc.business_status = :business_status")
            params["business_status"] = business_status
        if data_status:
            where_clauses.append("tc.data_status = :data_status")
            params["data_status"] = data_status

        if country_iso3:
            where_clauses.append("COALESCE(NULLIF(wc.country_iso3, ''), wc.country) = :country_iso3")
            params["country_iso3"] = country_iso3
        if countries:
            placeholders = ", ".join(f":country_{i}" for i in range(len(countries)))
            where_clauses.append(f"COALESCE(NULLIF(wc.country_iso3, ''), wc.country) IN ({placeholders})")
            for i, c in enumerate(countries):
                params[f"country_{i}"] = c

        if industry_tags:
            where_clauses.append("(wc.industry = ANY(:industry_tags) OR wc.sub_industry = ANY(:industry_tags))")
            params["industry_tags"] = industry_tags
        if sub_industries:
            where_clauses.append("(wc.industry = ANY(:sub_industries) OR wc.sub_industry = ANY(:sub_industries))")
            params["sub_industries"] = sub_industries

        if product_tags:
            where_clauses.append("wc.product_tags && :product_tags")
            params["product_tags"] = product_tags

        if trade_amount_min is not None:
            where_clauses.append("wc.trade_amount_3y_usd >= :trade_amount_min")
            params["trade_amount_min"] = trade_amount_min
        if trade_amount_max is not None:
            where_clauses.append("wc.trade_amount_3y_usd <= :trade_amount_max")
            params["trade_amount_max"] = trade_amount_max
        if trade_count_min is not None:
            where_clauses.append("wc.trade_count >= :trade_count_min")
            params["trade_count_min"] = trade_count_min
        if trade_count_max is not None:
            where_clauses.append("wc.trade_count <= :trade_count_max")
            params["trade_count_max"] = trade_count_max

        if source_type:
            where_clauses.append("wc.data_source_tags && ARRAY[:source_type]::text[]")
            params["source_type"] = source_type
        if sources:
            where_clauses.append("wc.data_source_tags && :sources")
            params["sources"] = sources

        effective_contact_count_min = contact_count_min if contact_count_min is not None else contacts_count_min
        effective_contact_count_max = contact_count_max if contact_count_max is not None else contacts_count_max
        if effective_contact_count_min is not None:
            where_clauses.append("wc.contacts_count >= :contact_count_min")
            params["contact_count_min"] = effective_contact_count_min
        if effective_contact_count_max is not None:
            where_clauses.append("wc.contacts_count <= :contact_count_max")
            params["contact_count_max"] = effective_contact_count_max

        if founded_year_from is not None:
            where_clauses.append("wc.founded_year >= :founded_year_from")
            params["founded_year_from"] = founded_year_from
        if founded_year_to is not None:
            where_clauses.append("wc.founded_year <= :founded_year_to")
            params["founded_year_to"] = founded_year_to

        if grade:
            where_clauses.append("wc.grade = :grade")
            params["grade"] = grade

        if employee_scales:
            placeholders = ", ".join(f":emp_scale_{i}" for i in range(len(employee_scales)))
            where_clauses.append(f"wc.employee_size IN ({placeholders})")
            for i, s in enumerate(employee_scales):
                params[f"emp_scale_{i}"] = s

        append_employee_count_range(
            where_clauses,
            params,
            employee_count_min=employee_count_min,
            employee_count_max=employee_count_max,
            alias="wc",
            column="employee_size",
        )

        if cursor:
            where_clauses.append("wc.id < :cursor")
            params["cursor"] = self._parse_clean_company_id(cursor)

        group_join_sql = ""
        if group_id:
            group_join_sql = "JOIN group_members gm ON gm.tenant_company_id = tc.id AND gm.group_id = :group_id"
            params["group_id"] = group_id

        where_sql = " AND ".join(where_clauses)

        total_result = await conn.execute(
            text(
                f"""
                SELECT COUNT(*) AS total
                FROM waimaotong_clean_companies wc
                JOIN tenant_companies tc
                  ON tc.clean_company_id = wc.id
                 AND tc.tenant_id = :tenant_id
                {group_join_sql}
                WHERE {where_sql}
                """
            ),
            params,
        )
        total = int(total_result.scalar_one())

        offset_sql = "OFFSET :offset" if offset is not None else ""
        result = await conn.execute(
            text(
                f"""
                SELECT
                  wc.id,
                  tc.id AS tc_id,
                  wc.company_name,
                  COALESCE(NULLIF(wc.country_iso3, ''), wc.country) AS country_iso3,
                  wc.website,
                  COALESCE(NULLIF(wc.domain, ''), wc.website) AS domain,
                  wc.industry,
                  wc.sub_industry,
                  wc.employee_size,
                  wc.contacts_count,
                  wc.product_tags,
                  wc.grade,
                  wc.score AS wmt_score,
                  wc.english_name,
                  wc.founded_year,
                  wc.phone,
                  wc.trade_amount_3y_usd,
                  wc.trade_count,
                  wc.description,
                  wc.data_source_tags,
                  wc.company_size,
                  tc.business_status,
                  tc.data_status,
                  tc.model_score,
                  tc.score,
                  tc.note,
                  tc.tags,
                  wc.created_at,
                  wc.updated_at
                FROM waimaotong_clean_companies wc
                JOIN tenant_companies tc
                  ON tc.clean_company_id = wc.id
                 AND tc.tenant_id = :tenant_id
                {group_join_sql}
                WHERE {where_sql}
                ORDER BY wc.id DESC
                LIMIT :limit
                {offset_sql}
                """
            ),
            params,
        )
        rows = [
            {
                "id": str(row["id"]),
                "tc_id": str(row["tc_id"]),
                "name": row["company_name"],
                "name_en": row["english_name"],
                "country_iso3": row["country_iso3"],
                "website": row["website"],
                "domain": row["domain"],
                "industry_desc": row["industry"],
                "industry_tags": [row["sub_industry"]] if row["sub_industry"] else [],
                "sub_industry": row["sub_industry"],
                "employee_num": row["employee_size"],
                "contacts_count": row["contacts_count"],
                "product_tags": list(row["product_tags"]) if row["product_tags"] else [],
                "grade": row["grade"],
                "wmt_score": float(row["wmt_score"]) if row["wmt_score"] is not None else None,
                "founded_year": row["founded_year"],
                "phone": row["phone"],
                "trade_amount_3y_usd": float(row["trade_amount_3y_usd"]) if row["trade_amount_3y_usd"] is not None else None,
                "trade_count": row["trade_count"],
                "description": row["description"],
                "data_source_tags": list(row["data_source_tags"] or []),
                "company_size": row["company_size"],
                "business_status": row["business_status"],
                "data_status": row["data_status"],
                "model_score": float(row["model_score"]) if row["model_score"] is not None else None,
                "score": float(row["score"]) if row["score"] is not None else None,
                "note": row["note"],
                "tags": list(row["tags"] or []),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in result.mappings().all()
        ]
        return rows, total

    async def v3_company_detail(self, conn: AsyncConnection, tenant_id: str, clean_company_id: str) -> dict:
        company_id = self._parse_clean_company_id(clean_company_id)
        result = await conn.execute(
            text(
                """
                SELECT
                  wc.id,
                  wc.company_name,
                  wc.english_name,
                  COALESCE(NULLIF(wc.country_iso3, ''), wc.country) AS country_iso3,
                  wc.website,
                  COALESCE(NULLIF(wc.domain, ''), wc.website) AS domain,
                  wc.founded_year,
                  wc.employee_size,
                  wc.industry,
                  wc.sub_industry,
                  wc.product_tags,
                  wc.grade,
                  wc.score AS wmt_score,
                  wc.trade_amount_3y_usd,
                  wc.trade_count,
                  wc.contacts_count,
                  wc.data_source_tags,
                  wc.full_address,
                  wc.description,
                  wc.phone,
                  wc.company_size,
                  wc.score_details,
                  wc.company_type_analysis,
                  wc.email_priority,
                  wc.sales_approach,
                  wc.match_reasons,
                  wc.potential_needs,
                  wc.recommended_products,
                  wc.risk_factors,
                  wc.main_business,
                  wc.trade_summary,
                  wc.created_at,
                  wc.updated_at,
                  tc.id AS tc_id,
                  tc.business_status,
                  tc.data_status,
                  tc.model_score,
                  tc.score,
                  tc.note,
                  tc.tags,
                  tc.score_adjustment,
                  tc.created_at AS tenant_created_at,
                  tc.updated_at AS tenant_updated_at
                FROM waimaotong_clean_companies wc
                JOIN tenant_companies tc
                  ON tc.clean_company_id = wc.id
                 AND tc.tenant_id = :tenant_id
                WHERE wc.id = :clean_company_id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "clean_company_id": company_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="公司不存在", status_code=404)

        return {
            "id": str(row["id"]),
            "tc_id": str(row["tc_id"]),
            "name": row["company_name"],
            "name_en": row["english_name"],
            "country_iso3": row["country_iso3"],
            "website": row["website"],
            "domain": row["domain"],
            "founded_year": row["founded_year"],
            "employee_num": row["employee_size"],
            "industry_desc": row["industry"],
            "sub_industry": row["sub_industry"],
            "industry_tags": [row["sub_industry"]] if row["sub_industry"] else [],
            "product_tags": list(row["product_tags"] or []),
            "grade": row["grade"],
            "wmt_score": float(row["wmt_score"]) if row["wmt_score"] is not None else None,
            "trade_amount_3y_usd": float(row["trade_amount_3y_usd"]) if row["trade_amount_3y_usd"] is not None else None,
            "trade_count": row["trade_count"],
            "contacts_count": row["contacts_count"],
            "phone": row["phone"],
            "company_size": row["company_size"],
            "full_address": row["full_address"],
            "description": row["description"],
            "sources": list(row["data_source_tags"] or []),
            "matched_keywords": [],
            "business_status": row["business_status"],
            "data_status": row["data_status"],
            "model_score": float(row["model_score"]) if row["model_score"] is not None else None,
            "score": float(row["score"]) if row["score"] is not None else None,
            "note": row["note"],
            "tags": list(row["tags"] or []),
            "score_adjustment": row["score_adjustment"],
            "score_details": row["score_details"],
            "company_type_analysis": row["company_type_analysis"],
            "email_priority": row["email_priority"],
            "sales_approach": row["sales_approach"],
            "match_reasons": row["match_reasons"],
            "potential_needs": row["potential_needs"],
            "recommended_products": row["recommended_products"],
            "risk_factors": row["risk_factors"],
            "main_business": row["main_business"],
            "trade_summary": row["trade_summary"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "tenant_created_at": row["tenant_created_at"].isoformat() if row["tenant_created_at"] else None,
            "tenant_updated_at": row["tenant_updated_at"].isoformat() if row["tenant_updated_at"] else None,
        }

    async def v3_company_contacts(self, conn: AsyncConnection, tenant_id: str, clean_company_id: str) -> list[dict]:
        company_id = self._parse_clean_company_id(clean_company_id)
        await self.v3_company_detail(conn, tenant_id, company_id)
        result = await conn.execute(
            text(
                """
                SELECT
                  wcc.id,
                  wcc.name,
                  wcc.position,
                  wcc.department,
                  wcc.email,
                  wcc.phone,
                  wcc.mobile,
                  wcc.email_status,
                  wcc.linkedin,
                  wcc.whatsapp,
                  wcc.confidence,
                  wcc.created_at,
                  tc.contact_status,
                  tc.is_sendable,
                  tc.created_at AS tenant_created_at,
                  tc.updated_at AS tenant_updated_at
                FROM waimaotong_clean_contacts wcc
                LEFT JOIN tenant_contacts tc
                  ON tc.clean_contact_id = wcc.id
                 AND tc.tenant_id = :tenant_id
                WHERE wcc.sys_company_id = (
                    SELECT sys_company_id FROM waimaotong_clean_companies WHERE id = :company_id
                )
                OR wcc.id IN (
                    SELECT clean_contact_id FROM tenant_contacts
                    WHERE tenant_id = :tenant_id AND clean_company_id = :company_id
                )
                ORDER BY wcc.created_at ASC
                """
            ),
            {"tenant_id": tenant_id, "company_id": company_id},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "position": row["position"],
                "department": row["department"],
                "email": str(row["email"]) if row["email"] is not None else None,
                "phone": row["phone"] or row["mobile"],
                "email_status": row["email_status"],
                "linkedin": row["linkedin"],
                "whatsapp": row["whatsapp"],
                "confidence": row["confidence"],
                "tenant_contact_state": {
                    "contact_status": row["contact_status"],
                    "is_sendable": row["is_sendable"],
                    "created_at": row["tenant_created_at"].isoformat() if row["tenant_created_at"] else None,
                    "updated_at": row["tenant_updated_at"].isoformat() if row["tenant_updated_at"] else None,
                },
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": None,
            }
            for row in result.mappings().all()
        ]

    async def prospects(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        *,
        keyword: str | None = None,
        countries: list[str] | None = None,
        sub_industries: list[str] | None = None,
        product_tags: list[str] | None = None,
        sources: list[str] | None = None,
        employee_count_min: int | None = None,
        employee_count_max: int | None = None,
        trade_amount_min: float | None = None,
        trade_amount_max: float | None = None,
        trade_count_min: int | None = None,
        trade_count_max: int | None = None,
        contact_count_min: int | None = None,
        contact_count_max: int | None = None,
        founded_year_from: int | None = None,
        founded_year_to: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        where_clauses = [
            "tc.tenant_id = :tenant_id",
        ]
        params: dict = {"tenant_id": tenant_id, "limit": limit}

        if keyword:
            where_clauses.append(
                "(wc.company_name ILIKE :keyword OR wc.domain ILIKE :keyword OR wc.website ILIKE :keyword)"
            )
            params["keyword"] = f"%{keyword}%"
        if countries:
            where_clauses.append("wc.country_iso3 = ANY(:countries)")
            params["countries"] = countries
        if sub_industries:
            where_clauses.append(
                "(wc.industry = ANY(:sub_industries) OR wc.sub_industry = ANY(:sub_industries))"
            )
            params["sub_industries"] = sub_industries
        if product_tags:
            where_clauses.append("wc.product_tags && :product_tags")
            params["product_tags"] = product_tags
        if sources:
            where_clauses.append("wc.data_source_tags && :sources")
            params["sources"] = sources
        append_employee_count_range(
            where_clauses,
            params,
            employee_count_min=employee_count_min,
            employee_count_max=employee_count_max,
            alias="wc",
            column="employee_size",
        )
        if trade_amount_min is not None:
            where_clauses.append("wc.trade_amount_3y_usd >= :trade_amount_min")
            params["trade_amount_min"] = trade_amount_min
        if trade_amount_max is not None:
            where_clauses.append("wc.trade_amount_3y_usd <= :trade_amount_max")
            params["trade_amount_max"] = trade_amount_max
        if trade_count_min is not None:
            where_clauses.append("wc.trade_count >= :trade_count_min")
            params["trade_count_min"] = trade_count_min
        if trade_count_max is not None:
            where_clauses.append("wc.trade_count <= :trade_count_max")
            params["trade_count_max"] = trade_count_max
        if contact_count_min is not None:
            where_clauses.append("wc.contacts_count >= :contact_count_min")
            params["contact_count_min"] = contact_count_min
        if contact_count_max is not None:
            where_clauses.append("wc.contacts_count <= :contact_count_max")
            params["contact_count_max"] = contact_count_max
        if founded_year_from is not None:
            where_clauses.append("wc.founded_year >= :founded_year_from")
            params["founded_year_from"] = founded_year_from
        if founded_year_to is not None:
            where_clauses.append("wc.founded_year <= :founded_year_to")
            params["founded_year_to"] = founded_year_to

        where_sql = " AND ".join(where_clauses)
        result = await conn.execute(
            text(
                f"""
                SELECT
                  tc.id,
                  wc.company_name,
                  wc.country_iso3,
                  tc.score,
                  tc.model_score,
                  tc.business_status,
                  tc.data_status,
                  tc.created_at
                FROM tenant_companies tc
                JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
                WHERE {where_sql}
                ORDER BY
                  tc.score DESC NULLS LAST,
                  tc.created_at DESC
                LIMIT :limit
                """
            ),
            params,
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["company_name"],
                "country_iso3": row["country_iso3"],
                "score": float(row["score"]) if row["score"] is not None else None,
                "model_score": float(row["model_score"]) if row["model_score"] is not None else None,
                "business_status": row["business_status"],
                "data_status": row["data_status"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def email_templates(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, category, source_type, is_ai_generated, created_at
                FROM email_templates
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
                "category": row["category"],
                "source_type": row["source_type"],
                "is_ai_generated": row["is_ai_generated"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def sending_plans(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, status, total_recipients, sent_count, created_at
                FROM sending_plans
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
                "status": row["status"],
                "total_recipients": row["total_recipients"],
                "sent_count": row["sent_count"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def email_stats(self, conn: AsyncConnection, tenant_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT
                  count(*) AS total,
                  count(*) FILTER (WHERE status = 'sent') AS sent,
                  count(*) FILTER (WHERE status = 'delivered') AS delivered,
                  count(*) FILTER (WHERE status = 'opened') AS opened,
                  count(*) FILTER (WHERE status = 'clicked') AS clicked,
                  count(*) FILTER (WHERE status = 'replied') AS replied,
                  count(*) FILTER (WHERE status = 'bounced') AS bounced,
                  count(*) FILTER (WHERE status = 'unsubscribed') AS unsubscribed
                FROM emails
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.mappings().one()
        return dict(row)

    async def ai_capabilities(self, conn: AsyncConnection, tenant_id: str, roles: list[str]) -> dict:
        provider_state = await self.ai_provider.get_config(conn, tenant_id=tenant_id, refresh_if_stale=True)
        balance = provider_state["balance"]
        can_mutate_ai = any(role in {"admin", "operator"} for role in roles)
        is_configured = provider_state["is_configured"]
        status = balance["status"]
        is_available = status == "available"
        return {
            "provider": {
                "provider": "openrouter",
                "is_configured": is_configured,
                "balance_status": status,
                "balance_source": balance["source"],
                "balance_amount": balance["amount"],
                "checked_at": balance["checked_at"],
                "message": balance["message"],
            },
            "features": [
                {
                    "feature": "email_generate",
                    "available": can_mutate_ai and is_available,
                    "reason": None if can_mutate_ai and is_available else self._capability_reason(can_mutate_ai, is_configured, status),
                },
                {
                    "feature": "email_analysis",
                    "available": can_mutate_ai and is_available,
                    "reason": None if can_mutate_ai and is_available else self._capability_reason(can_mutate_ai, is_configured, status),
                },
                {
                    "feature": "intelligence_summary",
                    "available": is_available,
                    "reason": None if is_available else self._provider_reason(is_configured, status),
                },
            ],
        }

    def _capability_reason(self, can_mutate_ai: bool, is_configured: bool, status: str) -> str:
        if not can_mutate_ai:
            return "insufficient_permission"
        return self._provider_reason(is_configured, status)

    def _provider_reason(self, is_configured: bool, status: str) -> str:
        if not is_configured:
            return "not_configured"
        if status == "insufficient_balance":
            return "insufficient_balance"
        if status == "unknown":
            return "balance_unknown"
        if status == "invalid_api_key":
            return "invalid_api_key"
        if status == "provider_error":
            return "provider_error"
        return "unavailable"
