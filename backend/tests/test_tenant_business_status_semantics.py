from uuid import uuid4

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.main import create_app
from app.security.jwt import create_access_token
from app.services.scoring_service import ScoringService
from app.services.admin_collection_service import AdminCollectionService
from app.services.tenant_messaging_service import TenantMessagingService
from app.services.tenant_ops_service import TenantOpsService
from app.services.tenant_query_service import TenantQueryService
from app.services.webhook_service import WebhookService
from tests.helpers import make_engine


async def _tenant(conn, slug_prefix: str = "status-semantics") -> str:
    tenant_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
            VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
            """
        ),
        {"tenant_id": tenant_id, "slug": f"{slug_prefix}-{uuid4().hex[:8]}"},
    )
    return tenant_id


async def _user(conn, tenant_id: str) -> str:
    user_id = str(new_uuid())
    await conn.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
            VALUES (:user_id, :tenant_id, :email, 'hash', '测试用户', 'active', false)
            """
        ),
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": f"user-{uuid4().hex[:8]}@example.com",
        },
    )
    return user_id


async def _tenant_and_token(slug_prefix: str = "status-semantics") -> tuple[str, str, str]:
    tenant_id = str(new_uuid())
    user_id = str(new_uuid())
    slug = f"{slug_prefix}-{uuid4().hex[:8]}"
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO tenants (id, name, slug, industry, status, settings, needs_onboarding)
                    VALUES (:tenant_id, :slug, :slug, 'PCB', 'active', '{}'::jsonb, false)
                    """
                ),
                {"tenant_id": tenant_id, "slug": slug},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                    VALUES (:user_id, :tenant_id, :email, 'hash', '测试用户', 'active', false)
                    """
                ),
                {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "email": f"user-{uuid4().hex[:8]}@example.com",
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO user_roles (id, tenant_id, user_id, role)
                    VALUES (:id, :tenant_id, :user_id, 'admin')
                    """
                ),
                {"id": str(new_uuid()), "tenant_id": tenant_id, "user_id": user_id},
            )
    finally:
        await engine.dispose()
    token = create_access_token(
        {
            "sub": user_id,
            "kind": "tenant",
            "tid": tenant_id,
            "slug": slug,
            "roles": ["admin"],
        }
    )
    return tenant_id, slug, token


async def _tenant_company(
    conn,
    tenant_id: str,
    *,
    name: str | None = None,
    country_iso3: str = "USA",
    website: str | None = None,
    industry_desc: str = "PCB manufacturing",
    industry_tags: list[str] | None = None,
    product_tags: list[str] | None = None,
    employee_num: str | None = None,
    pcb_suppliers: list[str] | None = None,
    contacts_count: int | None = None,
    business_status: str = "new",
    data_status: str = "ready",
    visibility_status: str = "visible",
    model_score: int | None = None,
    score: int | None = None,
) -> int:
    clean_company_id = (
        await conn.execute(
            text(
                """
                INSERT INTO clean_companies
                  (name, name_normalized, country_iso3, website, industry_desc, industry_tags,
                   product_tags, employee_num, pcb_suppliers, contacts_count)
                VALUES
                  (:name, :name_normalized, :country_iso3, :website, :industry_desc, :industry_tags,
                   :product_tags, :employee_num, :pcb_suppliers, :contacts_count)
                RETURNING id
                """
            ),
            {
                "name": name or f"Status Semantics {uuid4().hex}",
                "name_normalized": f"status-semantics-{uuid4().hex}",
                "country_iso3": country_iso3,
                "website": website or f"https://{uuid4().hex}.example.com",
                "industry_desc": industry_desc,
                "industry_tags": industry_tags or ["PCB manufacturing"],
                "product_tags": product_tags or ["pcb"],
                "employee_num": employee_num,
                "pcb_suppliers": pcb_suppliers or [],
                "contacts_count": contacts_count,
            },
        )
    ).scalar_one()
    return (
        await conn.execute(
            text(
                """
                INSERT INTO tenant_companies
                  (tenant_id, clean_company_id, business_status, data_status, visibility_status, model_score, score)
                VALUES
                  (:tenant_id, :clean_company_id, :business_status, :data_status, :visibility_status, :model_score, :score)
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_company_id": clean_company_id,
                "business_status": business_status,
                "data_status": data_status,
                "visibility_status": visibility_status,
                "model_score": model_score,
                "score": score,
            },
        )
    ).scalar_one()


async def _contact(
    conn,
    tenant_id: str,
    tenant_company_id: int,
    *,
    name: str = "Contact",
    position: str = "Buyer",
    email: str | None = None,
    phone: str | None = None,
) -> int:
    clean_company_id = (
        await conn.execute(
            text("SELECT clean_company_id FROM tenant_companies WHERE id = :id"),
            {"id": tenant_company_id},
        )
    ).scalar_one()
    clean_contact_id = (
        await conn.execute(
            text(
                """
                INSERT INTO clean_contacts (clean_company_id, name, position, email, phone)
                VALUES (:clean_company_id, :name, :position, :email, :phone)
                RETURNING id
                """
            ),
            {
                "clean_company_id": clean_company_id,
                "name": name,
                "position": position,
                "email": email or f"{uuid4().hex}@example.com",
                "phone": phone,
            },
        )
    ).scalar_one()
    return (
        await conn.execute(
            text(
                """
                INSERT INTO tenant_contacts
                  (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                VALUES
                  (:tenant_id, :clean_contact_id, :clean_company_id, 'available', true)
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "clean_contact_id": clean_contact_id,
                "clean_company_id": clean_company_id,
            },
        )
    ).scalar_one()


async def _clean_company_id(conn, tenant_company_id: int) -> int:
    return (
        await conn.execute(
            text("SELECT clean_company_id FROM tenant_companies WHERE id = :id"),
            {"id": tenant_company_id},
        )
    ).scalar_one()


async def _business_status(conn, tenant_company_id: int) -> str:
    return (
        await conn.execute(
            text("SELECT business_status FROM tenant_companies WHERE id = :id"),
            {"id": tenant_company_id},
        )
    ).scalar_one()


async def test_scoring_persists_score_without_mutating_business_status() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "score-stage")
            tenant_company_id = await _tenant_company(conn, tenant_id, business_status="in_group")
            template_id = str(new_uuid())
            template_version_id = str(new_uuid())
            score_result = {
                "tenant_id": tenant_id,
                "tenant_company_id": str(tenant_company_id),
                "template_id": template_id,
                "template_version_id": template_version_id,
                "total_score": 82,
                "grade": "A",
                "dimension_scores": [],
                "llm_pending": False,
                "llm_score": None,
                "llm_reasoning": None,
                "llm_model_id": None,
                "llm_usage_log_id": None,
            }
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_templates (id, tenant_id, name, industry, dimensions, grade_thresholds)
                    VALUES (:id, :tenant_id, '模板', 'PCB', '[]'::jsonb, '{}'::jsonb)
                    """
                ),
                {"id": template_id, "tenant_id": tenant_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_template_versions (id, tenant_id, template_id, version, dimensions, grade_thresholds)
                    VALUES (:id, :tenant_id, :template_id, 1, '[]'::jsonb, '{}'::jsonb)
                    """
                ),
                {"id": template_version_id, "tenant_id": tenant_id, "template_id": template_id},
            )

            result = await ScoringService().persist_score_result(conn, score_result=score_result)

            assert result["grade"] == "A"
            assert result["total_score"] == 82
            assert await _business_status(conn, tenant_company_id) == "in_group"
    finally:
        await engine.dispose()


async def test_llm_pending_score_does_not_mutate_business_status() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "pending-stage")
            tenant_company_id = await _tenant_company(conn, tenant_id, business_status="new")
            template_id = str(new_uuid())
            template_version_id = str(new_uuid())
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_templates (id, tenant_id, name, industry, dimensions, grade_thresholds)
                    VALUES (:id, :tenant_id, '模板', 'PCB', '[]'::jsonb, '{}'::jsonb)
                    """
                ),
                {"id": template_id, "tenant_id": tenant_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_template_versions (id, tenant_id, template_id, version, dimensions, grade_thresholds)
                    VALUES (:id, :tenant_id, :template_id, 1, '[]'::jsonb, '{}'::jsonb)
                    """
                ),
                {"id": template_version_id, "tenant_id": tenant_id, "template_id": template_id},
            )

            await ScoringService().persist_score_result(
                conn,
                score_result={
                    "tenant_id": tenant_id,
                    "tenant_company_id": str(tenant_company_id),
                    "template_id": template_id,
                    "template_version_id": template_version_id,
                    "total_score": 0,
                    "grade": "D",
                    "dimension_scores": [{"type": "llm", "pending": True}],
                    "llm_pending": True,
                    "llm_score": None,
                    "llm_reasoning": None,
                    "llm_model_id": None,
                    "llm_usage_log_id": None,
                },
            )

            assert await _business_status(conn, tenant_company_id) == "new"
    finally:
        await engine.dispose()


async def test_manual_company_creation_uses_v3_status_semantics() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "manual-company")
            user_id = await _user(conn, tenant_id)
            company = await TenantOpsService().create_company(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "name": f"Manual Company {uuid4().hex}",
                    "country": "USA",
                    "website": "https://manual.example.com",
                    "industry": "PCB",
                    "tags": ["manual"],
                },
            )
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, business_status, data_status, visibility_status
                        FROM tenant_companies
                        WHERE id = :id
                        """
                    ),
                    {"id": int(company["id"])},
                )
            ).mappings().one()

            assert isinstance(row["id"], int)
            assert row["business_status"] == "new"
            assert row["data_status"] in {"ready", "missing_contacts", "insufficient_data"}
            assert row["visibility_status"] == "visible"
    finally:
        await engine.dispose()


async def test_manual_company_creation_normalizes_country_inputs() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "manual-country")
            user_id = await _user(conn, tenant_id)
            service = TenantOpsService()

            countries = {
                "US": "USA",
                "DE": "DEU",
                "JP": "JPN",
                "CN": "CHN",
                "USA": "USA",
                None: "UNK",
            }
            for country, expected_country_iso3 in countries.items():
                payload = {
                    "name": f"Manual Country {country or 'empty'} {uuid4().hex}",
                    "website": f"https://manual-country-{uuid4().hex}.example.com",
                    "industry": "PCB",
                }
                if country is not None:
                    payload["country"] = country

                company = await service.create_company(
                    conn,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    payload=payload,
                )

                assert company["country"] == expected_country_iso3
    finally:
        await engine.dispose()


async def test_manual_company_creation_rejects_unknown_country_without_guessing() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "manual-bad-country")
            user_id = await _user(conn, tenant_id)

            with pytest.raises(AppError) as exc_info:
                await TenantOpsService().create_company(
                    conn,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    payload={
                        "name": f"Manual Bad Country {uuid4().hex}",
                        "country": "United States",
                        "website": "https://manual-bad-country.example.com",
                    },
                )

            assert exc_info.value.status_code == 422
            assert "国家" in exc_info.value.message
    finally:
        await engine.dispose()


async def test_manual_company_creation_with_contact_email_succeeds() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "manual-contact")
            user_id = await _user(conn, tenant_id)

            company = await TenantOpsService().create_company(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "name": f"Manual Contact {uuid4().hex}",
                    "country": "USA",
                    "website": "https://manual-contact.example.com",
                    "contact_name": "Alice",
                    "contact_email": "alice@example.com",
                    "contact_title": "Buyer",
                },
            )

            contacts = await TenantOpsService().company_contacts(conn, tenant_id, company["id"])

            assert company["data_status"] == "ready"
            assert len(contacts) == 1
            assert contacts[0]["email"] == "alice@example.com"
    finally:
        await engine.dispose()


async def test_manual_company_creation_is_idempotent_for_existing_visible_company() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "manual-idempotent")
            user_id = await _user(conn, tenant_id)
            payload = {
                "name": f"Manual Idempotent {uuid4().hex}",
                "country": "USA",
                "website": "https://manual-idempotent.example.com",
            }

            service = TenantOpsService()
            first = await service.create_company(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=payload,
            )
            second = await service.create_company(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload=payload,
            )

            assert second["id"] == first["id"]
    finally:
        await engine.dispose()


async def test_manual_company_creation_api_accepts_country_and_contact_email() -> None:
    _, slug, token = await _tenant_and_token("manual-api")

    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                f"/t/{slug}/api/v1/companies",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": f"Manual Api {uuid4().hex}",
                    "country": "US",
                    "website": "https://manual-api.example.com",
                    "contact_name": "Alice",
                    "contact_email": "alice@example.com",
                    "contact_title": "Buyer",
                },
            )

    assert response.status_code == 200, response.text
    company = response.json()["data"]
    assert company["country"] == "USA"
    assert company["data_status"] == "ready"
    assert company["business_status"] == "new"
    assert company["contacts"][0]["email"] == "alice@example.com"


async def test_legacy_select_and_exclude_are_disabled() -> None:
    engine = make_engine()
    ops = TenantOpsService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "legacy-actions")
            user_id = await _user(conn, tenant_id)
            tenant_company_id = await _tenant_company(conn, tenant_id, business_status="new")

            for status in ("selected", "excluded"):
                with pytest.raises(AppError):
                    await ops.set_prospect_status(
                        conn,
                        tenant_id=tenant_id,
                        prospect_id=str(tenant_company_id),
                        status=status,
                        user_id=user_id,
                    )

            assert await _business_status(conn, tenant_company_id) == "new"
    finally:
        await engine.dispose()


async def test_invalid_business_status_update_is_rejected_before_database_constraint() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "invalid-status")
            user_id = await _user(conn, tenant_id)
            tenant_company_id = await _tenant_company(conn, tenant_id, business_status="new")

            with pytest.raises(AppError) as exc_info:
                await TenantOpsService().update_prospect(
                    conn,
                    tenant_id=tenant_id,
                    prospect_id=str(tenant_company_id),
                    user_id=user_id,
                    payload={"business_status": "archived"},
                )

            assert exc_info.value.status_code == 422
            assert await _business_status(conn, tenant_company_id) == "new"
    finally:
        await engine.dispose()


async def test_dashboard_and_filters_only_include_visible_companies() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "visible-metrics")
            await _tenant_company(conn, tenant_id, business_status="new", visibility_status="visible", model_score=80, score=80)
            await _tenant_company(conn, tenant_id, business_status="contacted", visibility_status="hidden", model_score=95, score=95)

            overview = await TenantQueryService().dashboard_overview(conn, tenant_id, is_admin=False)
            funnel = await TenantOpsService().dashboard_funnel(conn, tenant_id)
            filters = await TenantOpsService().companies_filters(conn, tenant_id)

            assert overview["total_companies"] == 1
            assert overview["scored_companies"] == 1
            assert funnel["total"] == 1
            assert {stage["status"] for stage in funnel["stages"]} == {"new", "in_group", "in_plan", "contacted"}
            assert {stage["status"]: stage["count"] for stage in funnel["stages"]}["new"] == 1
            assert "contacted" not in filters["business_statuses"]
    finally:
        await engine.dispose()


async def test_prospects_use_v3_contract_without_legacy_fields() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "prospects-v3")
            tenant_company_id = await _tenant_company(conn, tenant_id, model_score=86, score=84)

            prospects = await TenantQueryService().prospects(conn, tenant_id)

            assert prospects == [
                {
                    "id": str(tenant_company_id),
                    "name": prospects[0]["name"],
                    "country_iso3": "USA",
                    "score": 84.0,
                    "model_score": 86.0,
                    "business_status": "new",
                    "data_status": "ready",
                    "created_at": prospects[0]["created_at"],
                }
            ]
            assert "grade" not in prospects[0]
            assert "total_score" not in prospects[0]
            assert "is_precise_customer" not in prospects[0]
    finally:
        await engine.dispose()


async def test_scoring_context_uses_current_v3_company_columns() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "score-context")
            tenant_company_id = await _tenant_company(conn, tenant_id, model_score=70, score=70)

            context = await ScoringService()._load_company_context(conn, str(tenant_company_id))  # noqa: SLF001

            assert context["industry_desc"] == "PCB manufacturing"
            assert context["product_tags"] == ["pcb"]
            assert context["country_iso3"] == "USA"
            assert "is_precise_customer" not in context
            assert "domain" not in context
            assert "product_keywords" not in context
    finally:
        await engine.dispose()


async def test_companies_filter_ignores_removed_grade_contract() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "companies-no-grade")
            await _tenant_company(conn, tenant_id, model_score=70, score=70)

            companies = await TenantQueryService().companies(conn, tenant_id, score_min=60)

            assert len(companies) == 1
            assert companies[0]["score"] == 70.0
            assert companies[0]["model_score"] == 70.0
            assert "grade" not in companies[0]
            assert "total_score" not in companies[0]
    finally:
        await engine.dispose()


async def test_companies_filter_employee_count_range_matches_stored_employee_interval() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "employee-range")
            matching_id = await _tenant_company(
                conn,
                tenant_id,
                name="Matching Employee Range",
                employee_num="51-200",
            )
            await _tenant_company(
                conn,
                tenant_id,
                name="Too Small Employee Range",
                employee_num="1-50",
            )

            companies = await TenantQueryService().companies(
                conn,
                tenant_id,
                employee_count_min=100,
                employee_count_max=150,
            )

            assert [company["id"] for company in companies] == [str(await _clean_company_id(conn, matching_id))]
    finally:
        await engine.dispose()


async def test_companies_filter_pcb_supplier_presence_uses_shared_has_none_semantics() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "pcb-presence")
            has_supplier_id = await _tenant_company(
                conn,
                tenant_id,
                name="Has PCB Supplier",
                pcb_suppliers=["Supplier A"],
            )
            no_supplier_id = await _tenant_company(
                conn,
                tenant_id,
                name="No PCB Supplier",
                pcb_suppliers=[],
            )

            has_rows = await TenantQueryService().companies(
                conn,
                tenant_id,
                pcb_supplier_presence="has",
            )
            none_rows = await TenantQueryService().companies(
                conn,
                tenant_id,
                pcb_supplier_presence="none",
            )

            assert [company["id"] for company in has_rows] == [str(await _clean_company_id(conn, has_supplier_id))]
            assert [company["id"] for company in none_rows] == [str(await _clean_company_id(conn, no_supplier_id))]
    finally:
        await engine.dispose()


async def test_admin_and_tenant_base_filters_share_semantics_with_tenant_visibility_cut() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            unique_name = f"Shared Filter {uuid4().hex[:8]}"
            tenant_id = await _tenant(conn, "shared-filters")
            visible_id = await _tenant_company(
                conn,
                tenant_id,
                name=f"Visible {unique_name}",
                country_iso3="USA",
                industry_desc="EMS",
                industry_tags=["EMS"],
                product_tags=["rigid"],
                employee_num="51-200",
                pcb_suppliers=["Supplier A"],
                contacts_count=6,
                visibility_status="visible",
            )
            hidden_id = await _tenant_company(
                conn,
                tenant_id,
                name=f"Hidden {unique_name}",
                country_iso3="USA",
                industry_desc="EMS",
                industry_tags=["EMS"],
                product_tags=["rigid"],
                employee_num="51-200",
                pcb_suppliers=["Supplier A"],
                contacts_count=6,
                visibility_status="hidden",
            )
            for tenant_company_id in (visible_id, hidden_id):
                clean_company_id = await _clean_company_id(conn, tenant_company_id)
                await conn.execute(
                    text(
                        """
                        UPDATE clean_companies
                        SET incorporation_date = '2018-01-01',
                            trade_amount_3y_usd = 5000,
                            trade_count = 5
                        WHERE id = :id
                        """
                    ),
                    {"id": clean_company_id},
                )
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_company_sources (clean_company_id, source_type, source_company_id)
                        VALUES (:id, 'tendata', :source_company_id)
                        """
                    ),
                    {"id": clean_company_id, "source_company_id": clean_company_id},
                )

            filter_kwargs = {
                "keyword": unique_name,
                "countries": ["USA"],
                "sub_industries": ["EMS"],
                "product_tags": ["rigid"],
                "sources": ["tendata"],
                "employee_count_min": 100,
                "employee_count_max": 150,
                "trade_amount_min": 1000,
                "trade_amount_max": 9000,
                "trade_count_min": 2,
                "trade_count_max": 8,
                "contact_count_min": 4,
                "contact_count_max": 10,
                "founded_year_from": 2010,
                "founded_year_to": 2020,
                "pcb_supplier_presence": "has",
            }

            admin_rows, admin_total = await AdminCollectionService().list_v3_clean_companies(
                conn,
                page=1,
                page_size=20,
                **filter_kwargs,
            )
            tenant_rows = await TenantQueryService().companies(conn, tenant_id, **filter_kwargs)

            visible_clean_id = str(await _clean_company_id(conn, visible_id))
            hidden_clean_id = str(await _clean_company_id(conn, hidden_id))
            assert admin_total == 2
            assert {row["id"] for row in admin_rows} == {visible_clean_id, hidden_clean_id}
            assert [row["id"] for row in tenant_rows] == [visible_clean_id]
    finally:
        await engine.dispose()


async def test_tenant_company_contact_contract_uses_current_clean_contact_fields() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "company-contact-contract")
            tenant_company_id = await _tenant_company(conn, tenant_id, model_score=70, score=70)
            clean_company_id = await _clean_company_id(conn, tenant_company_id)
            await _contact(
                conn,
                tenant_id,
                tenant_company_id,
                name="Alice Buyer",
                position="Procurement Director",
                email="alice.buyer@example.com",
                phone="+1-555-0100",
            )
            await conn.execute(
                text("UPDATE clean_companies SET contacts_count = 1 WHERE id = :id"),
                {"id": clean_company_id},
            )

            companies = await TenantQueryService().companies(conn, tenant_id)
            detail = await TenantQueryService().v3_company_detail(conn, tenant_id, str(clean_company_id))
            contacts = await TenantQueryService().v3_company_contacts(conn, tenant_id, str(clean_company_id))

            assert companies[0]["contacts_count"] == 1
            assert detail["contacts_count"] == 1
            assert contacts == [
                {
                    "id": contacts[0]["id"],
                    "name": "Alice Buyer",
                    "position": "Procurement Director",
                    "email": "alice.buyer@example.com",
                    "phone": "+1-555-0100",
                    "tenant_contact_state": {
                        "contact_status": "available",
                        "is_sendable": True,
                        "created_at": contacts[0]["tenant_contact_state"]["created_at"],
                        "updated_at": contacts[0]["tenant_contact_state"]["updated_at"],
                    },
                    "created_at": contacts[0]["created_at"],
                    "updated_at": contacts[0]["updated_at"],
                }
            ]
            assert "contact_name" not in contacts[0]
            assert "contact_title" not in contacts[0]
            assert "full_name" not in contacts[0]
    finally:
        await engine.dispose()


async def test_tenant_company_contact_contract_preserves_zero_contacts_count() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "company-zero-contacts")
            tenant_company_id = await _tenant_company(conn, tenant_id, model_score=70, score=70)
            clean_company_id = await _clean_company_id(conn, tenant_company_id)
            await conn.execute(
                text("UPDATE clean_companies SET contacts_count = 0 WHERE id = :id"),
                {"id": clean_company_id},
            )

            companies = await TenantQueryService().companies(conn, tenant_id)
            detail = await TenantQueryService().v3_company_detail(conn, tenant_id, str(clean_company_id))

            assert companies[0]["contacts_count"] == 0
            assert detail["contacts_count"] == 0
    finally:
        await engine.dispose()


async def test_filter_recipients_do_not_accept_grade_and_use_country_iso3() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "recipients-no-grade")
            tenant_company_id = await _tenant_company(conn, tenant_id, model_score=70, score=70)
            await _contact(conn, tenant_id, tenant_company_id)

            rows = await TenantMessagingService()._recipients_from_filter(  # noqa: SLF001
                conn,
                tenant_id,
                {"grade": "999", "country": "USA"},
            )

            assert len(rows) == 1
            assert str(rows[0]["tenant_company_id"]) == str(tenant_company_id)
            assert rows[0]["country"] == "USA"
    finally:
        await engine.dispose()


async def test_group_membership_updates_business_status_and_last_group_removal_reverts_only_in_group() -> None:
    engine = make_engine()
    ops = TenantOpsService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "groups")
            user_id = await _user(conn, tenant_id)
            tenant_company_id = await _tenant_company(conn, tenant_id, business_status="new")
            await _contact(conn, tenant_id, tenant_company_id)
            group_a = await ops.create_group(conn, tenant_id=tenant_id, user_id=user_id, payload={"name": "A"})
            group_b = await ops.create_group(conn, tenant_id=tenant_id, user_id=user_id, payload={"name": "B"})

            await ops.add_group_members(
                conn,
                tenant_id=tenant_id,
                group_id=group_a["id"],
                user_id=user_id,
                payload={"tenant_company_ids": [str(tenant_company_id)]},
            )
            assert await _business_status(conn, tenant_company_id) == "in_group"

            await ops.add_group_members(
                conn,
                tenant_id=tenant_id,
                group_id=group_b["id"],
                user_id=user_id,
                payload={"tenant_company_ids": [str(tenant_company_id)]},
            )
            await ops.remove_group_members(
                conn,
                tenant_id=tenant_id,
                group_id=group_a["id"],
                user_id=user_id,
                payload={"tenant_company_ids": [str(tenant_company_id)]},
            )
            assert await _business_status(conn, tenant_company_id) == "in_group"

            await ops.remove_group_members(
                conn,
                tenant_id=tenant_id,
                group_id=group_b["id"],
                user_id=user_id,
                payload={"tenant_company_ids": [str(tenant_company_id)]},
            )
            assert await _business_status(conn, tenant_company_id) == "new"

            await ops.add_group_members(
                conn,
                tenant_id=tenant_id,
                group_id=group_a["id"],
                user_id=user_id,
                payload={"tenant_company_ids": [str(tenant_company_id)]},
            )
            await conn.execute(
                text("UPDATE tenant_companies SET business_status = 'in_plan' WHERE id = :id"),
                {"id": tenant_company_id},
            )
            await ops.remove_group_members(
                conn,
                tenant_id=tenant_id,
                group_id=group_a["id"],
                user_id=user_id,
                payload={"tenant_company_ids": [str(tenant_company_id)]},
            )
            assert await _business_status(conn, tenant_company_id) == "in_plan"
    finally:
        await engine.dispose()


async def test_business_status_constraint_rejects_archived() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "constraint")
            with pytest.raises(Exception):
                await _tenant_company(conn, tenant_id, business_status="archived")
    finally:
        await engine.dispose()


async def test_delivered_webhook_advances_company_to_contacted_but_sent_does_not() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "delivered")
            user_id = await _user(conn, tenant_id)
            tenant_company_id = await _tenant_company(conn, tenant_id, business_status="in_plan")
            tenant_contact_id = await _contact(conn, tenant_id, tenant_company_id)
            sent_message_id = f"sent-{uuid4().hex}"
            delivered_message_id = f"delivered-{uuid4().hex}"
            direct_sent_email_id = str(new_uuid())
            plan_id = str(new_uuid())
            template_id = str(new_uuid())
            step_id = str(new_uuid())
            recipient_id = str(new_uuid())
            enrollment_id = str(new_uuid())

            await conn.execute(
                text(
                    """
                    INSERT INTO domain_warmup_status
                      (id, tenant_id, domain, verification_status)
                    VALUES
                      (:id, :tenant_id, 'example.com', 'verified')
                    """
                ),
                {"id": str(new_uuid()), "tenant_id": tenant_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO sending_plans
                      (id, tenant_id, created_by, name, status, recipient_source, recipient_config, sender_email)
                    VALUES
                      (:id, :tenant_id, :user_id, 'Plan', 'running', 'manual', '{}'::jsonb, 'from@example.com')
                    """
                ),
                {"id": plan_id, "tenant_id": tenant_id, "user_id": user_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO email_templates
                      (id, tenant_id, name, category, subject, body_html)
                    VALUES
                      (:id, :tenant_id, 'Template', 'outreach', 'Subject', '<p>Body</p>')
                    """
                ),
                {"id": template_id, "tenant_id": tenant_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO sequence_steps
                      (id, tenant_id, plan_id, step_number, template_id, delay_days, condition_type)
                    VALUES
                      (:id, :tenant_id, :plan_id, 1, :template_id, 0, 'always')
                    """
                ),
                {"id": step_id, "tenant_id": tenant_id, "plan_id": plan_id, "template_id": template_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO sending_plan_recipients
                      (id, tenant_id, plan_id, tenant_company_id, tenant_contact_id, source_type, locked_at)
                    VALUES
                      (:id, :tenant_id, :plan_id, :tenant_company_id, :tenant_contact_id, 'manual', now())
                    """
                ),
                {
                    "id": recipient_id,
                    "tenant_id": tenant_id,
                    "plan_id": plan_id,
                    "tenant_company_id": tenant_company_id,
                    "tenant_contact_id": tenant_contact_id,
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO sequence_enrollments
                      (id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id, current_step, status)
                    VALUES
                      (:id, :tenant_id, :plan_id, :recipient_id, :tenant_contact_id, 1, 'active')
                    """
                ),
                {
                    "id": enrollment_id,
                    "tenant_id": tenant_id,
                    "plan_id": plan_id,
                    "recipient_id": recipient_id,
                    "tenant_contact_id": tenant_contact_id,
                },
            )
            for message_id in (sent_message_id, delivered_message_id):
                await conn.execute(
                    text(
                        """
                        INSERT INTO emails
                          (id, tenant_id, tenant_contact_id, from_email, to_email, subject, body_html, status, engagelab_message_id)
                        VALUES
                          (:id, :tenant_id, :tenant_contact_id, 'from@example.com', 'to@example.com', 'Subject', '<p>Body</p>', 'sent', :message_id)
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "tenant_id": tenant_id,
                        "tenant_contact_id": tenant_contact_id,
                        "message_id": message_id,
                    },
                )
            await conn.execute(
                text(
                    """
                    INSERT INTO emails
                      (id, tenant_id, plan_id, step_id, step_number, template_id, enrollment_id,
                       tenant_contact_id, from_email, to_email, subject, body_html, status)
                    VALUES
                      (:id, :tenant_id, :plan_id, :step_id, 1, :template_id, :enrollment_id,
                       :tenant_contact_id, 'from@example.com', 'to@example.com', 'Subject', '<p>Body</p>', 'queued')
                    """
                ),
                {
                    "id": direct_sent_email_id,
                    "tenant_id": tenant_id,
                    "plan_id": plan_id,
                    "step_id": step_id,
                    "template_id": template_id,
                    "enrollment_id": enrollment_id,
                    "tenant_contact_id": tenant_contact_id,
                },
            )

            await TenantMessagingService().mark_email_sent(
                conn,
                email_id=direct_sent_email_id,
                payload={"engagelab_message_id": f"direct-{uuid4().hex}"},
            )
            assert await _business_status(conn, tenant_company_id) == "in_plan"

            await WebhookService().process_engagelab_event(
                conn,
                {"event_id": f"evt-{uuid4().hex}", "message_id": sent_message_id, "event": "sent"},
            )
            assert await _business_status(conn, tenant_company_id) == "in_plan"

            await WebhookService().process_engagelab_event(
                conn,
                {"event_id": f"evt-{uuid4().hex}", "message_id": delivered_message_id, "event": "delivered"},
            )
            assert await _business_status(conn, tenant_company_id) == "contacted"
    finally:
        await engine.dispose()
