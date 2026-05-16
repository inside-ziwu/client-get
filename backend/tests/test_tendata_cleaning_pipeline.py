import json
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.cleanup_service import CleanupService
from app.services.collection_service import CollectionService
from app.services.keyword_service import get_or_create_keyword_master, normalize_keyword
from app.services.scoring_service import ScoringService
from app.services.tenant_messaging_service import TenantMessagingService
from app.services.tenant_ops_service import TenantOpsService
from app.services.tenant_query_service import TenantQueryService
from app.services.tenant_settings_service import TenantSettingsService
from app.workers import fan_out
from app.workers.fan_out import run_fan_out_for_tenant_keyword
from tests.helpers import make_engine


async def _keyword_master(conn, keyword: str) -> str:
    return str(
        await get_or_create_keyword_master(
            conn,
            keyword=keyword,
            keyword_normalized=normalize_keyword(keyword),
        )
    )


async def _tenant(conn, slug_prefix: str = "td-clean") -> str:
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


async def _raw_tendata(conn, *, keyword_master_id: str | None, source_id: str, **values) -> int:
    result = await conn.execute(
        text(
            """
            INSERT INTO tendata_raw_companies
              (keyword_master_id, source_id, collection_type, name, country_iso3, website,
               employee_num, industry_desc, product_tags, pcb_suppliers, trade_amount_3y_usd,
               trade_count, contacts_count, aliases, raw_payload, created_at)
            VALUES
              (:keyword_master_id, :source_id, 'reverse_lookup', :name, :country_iso3, :website,
               :employee_num, :industry_desc, :product_tags, :pcb_suppliers, :trade_amount_3y_usd,
               :trade_count, :contacts_count, :aliases, CAST(:raw_payload AS jsonb), :created_at)
            RETURNING id
            """
        ),
        {
            "keyword_master_id": keyword_master_id,
            "source_id": source_id,
            "name": values.get("name"),
            "country_iso3": values.get("country_iso3"),
            "website": values.get("website"),
            "employee_num": values.get("employee_num"),
            "industry_desc": values.get("industry_desc"),
            "product_tags": values.get("product_tags"),
            "pcb_suppliers": values.get("pcb_suppliers"),
            "trade_amount_3y_usd": values.get("trade_amount_3y_usd"),
            "trade_count": values.get("trade_count"),
            "contacts_count": values.get("contacts_count"),
            "aliases": values.get("aliases"),
            "raw_payload": json.dumps(values.get("raw_payload") or {}, ensure_ascii=False),
            "created_at": values.get("created_at", datetime(2026, 5, 1, tzinfo=timezone.utc)),
        },
    )
    return result.scalar_one()


async def _raw_tendata_contact(conn, *, raw_company_id: int, **values) -> int:
    result = await conn.execute(
        text(
            """
            INSERT INTO tendata_raw_contacts
              (raw_company_id, source_contact_id, name, position, email, phone, raw_payload, created_at)
            VALUES
              (:raw_company_id, :source_contact_id, :name, :position, :email, :phone,
               CAST(:raw_payload AS jsonb), :created_at)
            RETURNING id
            """
        ),
        {
            "raw_company_id": raw_company_id,
            "source_contact_id": values.get("source_contact_id"),
            "name": values.get("name"),
            "position": values.get("position"),
            "email": values.get("email"),
            "phone": values.get("phone"),
            "raw_payload": json.dumps(values.get("raw_payload") or {}, ensure_ascii=False),
            "created_at": values.get("created_at", datetime(2026, 5, 1, tzinfo=timezone.utc)),
        },
    )
    return result.scalar_one()


async def test_tendata_raw_requires_name_and_country_before_cleaning() -> None:
    engine = make_engine()
    service = CleanupService()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"identity {uuid4().hex}")
            missing_country = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-missing-country-{uuid4().hex}",
                name="Missing Country Buyer",
                country_iso3=None,
            )
            missing_name = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-missing-name-{uuid4().hex}",
                name=None,
                country_iso3="USA",
            )

            await service._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(missing_country))
            await service._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(missing_name))

            clean_count = (
                await conn.execute(
                    text("SELECT count(*) FROM clean_companies WHERE name IN ('Missing Country Buyer')")
                )
            ).scalar_one()
            statuses = (
                await conn.execute(
                    text(
                        """
                        SELECT source_id, enrichment_error
                        FROM tendata_raw_companies
                        WHERE id IN (:missing_country, :missing_name)
                        ORDER BY source_id
                        """
                    ),
                    {"missing_country": missing_country, "missing_name": missing_name},
                )
            ).mappings().all()

        assert clean_count == 0
        assert {row["enrichment_error"]["reason"] for row in statuses} == {"missing_identity"}
    finally:
        await engine.dispose()


async def test_tendata_cleaning_merges_by_normalized_name_country_and_uses_latest_summary() -> None:
    engine = make_engine()
    service = CleanupService()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"merge {uuid4().hex}")
            tenant_id = await _tenant(conn)
            company_name = f"Acme PCB LLC {uuid4().hex}"
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES (:tenant_id, :keyword_master_id, 'PCB', 'active')
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
            )
            old_raw = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-old-{uuid4().hex}",
                name=company_name,
                country_iso3="USA",
                website="https://old.example",
                employee_num="11-50",
                industry_desc="Old industry",
                product_tags=["pcb", "rigid"],
                pcb_suppliers=["Supplier A"],
                trade_amount_3y_usd=100,
                trade_count=1,
                contacts_count=1,
                aliases=["ACME"],
                created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            )
            new_raw = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-new-{uuid4().hex}",
                name=company_name,
                country_iso3="USA",
                website=None,
                employee_num="51-200",
                industry_desc="New industry",
                product_tags=["rigid", "flex"],
                pcb_suppliers=["Supplier A", "Supplier B"],
                trade_amount_3y_usd=50,
                trade_count=2,
                contacts_count=3,
                aliases=["ACME", "Acme Buyer"],
                created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
            )

            await service._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(new_raw))
            await service._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(old_raw))

            clean_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT id, website, employee_num, industry_desc, product_tags, pcb_suppliers,
                               trade_amount_3y_usd, trade_count, contacts_count, aliases
                        FROM clean_companies
                        WHERE name_normalized = normalize_company_name(:company_name)
                          AND country_iso3 = 'USA'
                        """
                    ),
                    {"company_name": company_name},
                )
            ).mappings().all()
            clean_id = clean_rows[0]["id"]
            keyword_count = (
                await conn.execute(
                    text("SELECT count(*) FROM clean_company_keywords WHERE clean_company_id = :clean_id"),
                    {"clean_id": clean_id},
                )
            ).scalar_one()
            tenant_row = (
                await conn.execute(
                    text(
                        """
                        SELECT visibility_status, business_status, data_status, model_score, score
                        FROM tenant_companies
                        WHERE tenant_id = :tenant_id AND clean_company_id = :clean_id
                        """
                    ),
                    {"tenant_id": tenant_id, "clean_id": clean_id},
                )
            ).mappings().one()

        assert len(clean_rows) == 1
        clean = clean_rows[0]
        assert clean["website"] == "old.example"
        assert clean["employee_num"] == "51-200"
        assert clean["industry_desc"] == "New industry"
        assert float(clean["trade_amount_3y_usd"]) == 50
        assert clean["trade_count"] == 2
        assert clean["contacts_count"] == 3
        assert set(clean["product_tags"]) == {"pcb", "rigid", "flex"}
        assert set(clean["pcb_suppliers"]) == {"Supplier A", "Supplier B"}
        assert set(clean["aliases"]) == {"ACME", "Acme Buyer"}
        assert keyword_count == 1
        assert tenant_row["visibility_status"] == "visible"
        assert tenant_row["business_status"] == "new"
        assert tenant_row["data_status"] == "missing_contacts"
        assert tenant_row["model_score"] is None
        assert tenant_row["score"] is None
    finally:
        await engine.dispose()


async def test_tendata_raw_without_keyword_updates_clean_but_does_not_materialize_tenant_company() -> None:
    engine = make_engine()
    service = CleanupService()
    try:
        async with engine.begin() as conn:
            raw_id = await _raw_tendata(
                conn,
                keyword_master_id=None,
                source_id=f"td-no-keyword-{uuid4().hex}",
                name="No Keyword Buyer",
                country_iso3="USA",
                product_tags=["pcb"],
            )

            await service._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(raw_id))

            clean_id = (
                await conn.execute(
                    text(
                        """
                        SELECT id
                        FROM clean_companies
                        WHERE name_normalized = normalize_company_name('No Keyword Buyer')
                          AND country_iso3 = 'USA'
                        """
                    )
                )
            ).scalar_one()
            keyword_count = (
                await conn.execute(
                    text("SELECT count(*) FROM clean_company_keywords WHERE clean_company_id = :clean_id"),
                    {"clean_id": clean_id},
                )
            ).scalar_one()
            tenant_count = (
                await conn.execute(
                    text("SELECT count(*) FROM tenant_companies WHERE clean_company_id = :clean_id"),
                    {"clean_id": clean_id},
                )
            ).scalar_one()
            raw_status = (
                await conn.execute(
                    text("SELECT enrichment_error FROM tendata_raw_companies WHERE id = :id"),
                    {"id": raw_id},
                )
            ).scalar_one()

        assert keyword_count == 0
        assert tenant_count == 0
        assert raw_status["reason"] == "missing_keyword_master_id"
    finally:
        await engine.dispose()


async def test_tendata_raw_persistence_retains_top_level_contacts_in_raw_payload() -> None:
    engine = make_engine()
    collection = CollectionService()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"raw contacts {uuid4().hex}")
            raw_id = await collection._upsert_tendata_raw(
                conn,
                task_id="legacy-task-id-is-ignored",
                row={
                    "keyword_master_id": keyword_master_id,
                    "source_id": f"td-contacts-{uuid4().hex}",
                    "collection_type": "reverse_lookup",
                    "name": "Raw Contact Buyer",
                    "country_iso3": "USA",
                    "contacts_count": 1,
                    "contacts": [
                        {
                            "name": "Ada Contact",
                            "position": "Purchasing Manager",
                            "email": "ada.contact@example.com",
                            "phone": "+1-555-0100",
                        }
                    ],
                    "raw_payload": {"brief": {"tid": "td-contact-brief"}},
                },
            )
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT contacts_count, contacts_status, raw_payload
                        FROM tendata_raw_companies
                        WHERE id = :id
                        """
                    ),
                    {"id": int(raw_id)},
                )
            ).mappings().one()

        assert row["contacts_count"] == 1
        assert row["contacts_status"] == "fetched"
        assert row["raw_payload"]["brief"] == {"tid": "td-contact-brief"}
        assert row["raw_payload"]["contacts"] == [
            {
                "name": "Ada Contact",
                "position": "Purchasing Manager",
                "email": "ada.contact@example.com",
                "phone": "+1-555-0100",
            }
        ]
    finally:
        await engine.dispose()


async def test_tendata_cleanup_materializes_raw_contacts_for_tenant_display() -> None:
    engine = make_engine()
    cleanup = CleanupService()
    query = TenantQueryService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "contacts")
            keyword_master_id = await _keyword_master(conn, f"contact display {uuid4().hex}")
            company_name = f"Contact Display Buyer {uuid4().hex}"
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES (:tenant_id, :keyword_master_id, 'PCB', 'active')
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
            )
            raw_id = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-clean-contact-{uuid4().hex}",
                name=company_name,
                country_iso3="USA",
                product_tags=["pcb"],
                contacts_count=1,
                raw_payload={
                    "contacts": [
                        {
                            "name": "Grace Buyer",
                            "position": "Sourcing Director",
                            "email": "grace.buyer@example.com",
                            "phone": "+1-555-0200",
                        }
                    ]
                },
            )

            await cleanup._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(raw_id))
            clean_row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, contacts_count
                        FROM clean_companies
                        WHERE name_normalized = normalize_company_name(:company_name)
                          AND country_iso3 = 'USA'
                        """
                    ),
                    {"company_name": company_name},
                )
            ).mappings().one()
            clean_contacts = (
                await conn.execute(
                    text(
                        """
                        SELECT name, position, email, phone
                        FROM clean_contacts
                        WHERE clean_company_id = :clean_company_id
                        """
                    ),
                    {"clean_company_id": clean_row["id"]},
                )
            ).mappings().all()
            tenant_row = (
                await conn.execute(
                    text(
                        """
                        SELECT data_status
                        FROM tenant_companies
                        WHERE tenant_id = :tenant_id
                          AND clean_company_id = :clean_company_id
                        """
                    ),
                    {"tenant_id": tenant_id, "clean_company_id": clean_row["id"]},
                )
            ).mappings().one()
            tenant_contacts = await query.v3_company_contacts(conn, tenant_id, str(clean_row["id"]))

        assert clean_row["contacts_count"] == 1
        assert [dict(row) for row in clean_contacts] == [
            {
                "name": "Grace Buyer",
                "position": "Sourcing Director",
                "email": "grace.buyer@example.com",
                "phone": "+1-555-0200",
            }
        ]
        assert tenant_row["data_status"] == "ready"
        assert tenant_contacts == [
            {
                "id": tenant_contacts[0]["id"],
                "name": "Grace Buyer",
                "position": "Sourcing Director",
                "email": "grace.buyer@example.com",
                "phone": "+1-555-0200",
                "tenant_contact_state": {
                    "contact_status": None,
                    "is_sendable": None,
                    "created_at": None,
                    "updated_at": None,
                },
                "created_at": tenant_contacts[0]["created_at"],
                "updated_at": tenant_contacts[0]["updated_at"],
            }
        ]
    finally:
        await engine.dispose()


async def test_tendata_cleanup_materializes_tendata_raw_contacts_for_tenant_display() -> None:
    engine = make_engine()
    cleanup = CleanupService()
    query = TenantQueryService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "td-raw-contacts")
            keyword_master_id = await _keyword_master(conn, f"td raw contact display {uuid4().hex}")
            company_name = f"Raw Contact Display Buyer {uuid4().hex}"
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES (:tenant_id, :keyword_master_id, 'PCB', 'active')
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
            )
            raw_id = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-raw-contact-{uuid4().hex}",
                name=company_name,
                country_iso3="USA",
                product_tags=["pcb"],
                contacts_count=1,
                raw_payload={},
            )
            await _raw_tendata_contact(
                conn,
                raw_company_id=raw_id,
                source_contact_id=f"tdc-{uuid4().hex}",
                name="Ada Raw Buyer",
                position="Procurement Director",
                email="ada.raw@example.com",
                phone="+1-555-0300",
            )

            await cleanup._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(raw_id))
            clean_row = (
                await conn.execute(
                    text(
                        """
                        SELECT id, contacts_count
                        FROM clean_companies
                        WHERE name_normalized = normalize_company_name(:company_name)
                          AND country_iso3 = 'USA'
                        """
                    ),
                    {"company_name": company_name},
                )
            ).mappings().one()
            source_row = (
                await conn.execute(
                    text(
                        """
                        SELECT clean_company_id
                        FROM clean_company_sources
                        WHERE source_type = 'tendata'
                          AND source_company_id = :raw_company_id
                        """
                    ),
                    {"raw_company_id": raw_id},
                )
            ).mappings().one()
            clean_contacts = (
                await conn.execute(
                    text(
                        """
                        SELECT name, position, email, phone
                        FROM clean_contacts
                        WHERE clean_company_id = :clean_company_id
                        """
                    ),
                    {"clean_company_id": clean_row["id"]},
                )
            ).mappings().all()
            tenant_contacts = await query.v3_company_contacts(conn, tenant_id, str(clean_row["id"]))

        assert source_row["clean_company_id"] == clean_row["id"]
        assert clean_row["contacts_count"] == 1
        assert [dict(row) for row in clean_contacts] == [
            {
                "name": "Ada Raw Buyer",
                "position": "Procurement Director",
                "email": "ada.raw@example.com",
                "phone": "+1-555-0300",
            }
        ]
        assert tenant_contacts[0]["name"] == "Ada Raw Buyer"
        assert tenant_contacts[0]["position"] == "Procurement Director"
        assert tenant_contacts[0]["email"] == "ada.raw@example.com"
        assert tenant_contacts[0]["phone"] == "+1-555-0300"
    finally:
        await engine.dispose()


async def test_tendata_raw_contacts_backfill_uses_source_mapping_and_is_idempotent() -> None:
    engine = make_engine()
    cleanup = CleanupService()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"td backfill {uuid4().hex}")
            raw_id = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-backfill-{uuid4().hex}",
                name=f"Backfill Buyer {uuid4().hex}",
                country_iso3="USA",
                contacts_count=2,
            )
            clean_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_companies (name, name_normalized, country_iso3, contacts_count)
                        VALUES (:name, :name_normalized, 'USA', 2)
                        RETURNING id
                        """
                    ),
                    {"name": "Mapped Backfill Buyer", "name_normalized": f"mapped-backfill-{uuid4().hex}"},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_company_sources
                      (clean_company_id, source_type, source_company_id, source_key)
                    VALUES (:clean_company_id, 'tendata', :raw_company_id, 'manual-test')
                    """
                ),
                {"clean_company_id": clean_id, "raw_company_id": raw_id},
            )
            await _raw_tendata_contact(
                conn,
                raw_company_id=raw_id,
                source_contact_id=f"tdc-{uuid4().hex}",
                name="First Backfill",
                position="Buyer",
                email="first.backfill@example.com",
            )
            await _raw_tendata_contact(
                conn,
                raw_company_id=raw_id,
                source_contact_id=f"tdc-{uuid4().hex}",
                name="Second Backfill",
                position="Director",
                email="second.backfill@example.com",
            )

            dry_run = await cleanup.backfill_tendata_raw_contacts(conn, dry_run=True, raw_company_id=raw_id)
            first_run = await cleanup.backfill_tendata_raw_contacts(conn, dry_run=False, raw_company_id=raw_id)
            second_run = await cleanup.backfill_tendata_raw_contacts(conn, dry_run=False, raw_company_id=raw_id)
            clean_contacts = (
                await conn.execute(
                    text(
                        """
                        SELECT name, position, email
                        FROM clean_contacts
                        WHERE clean_company_id = :clean_company_id
                        ORDER BY email
                        """
                    ),
                    {"clean_company_id": clean_id},
                )
            ).mappings().all()

        assert dry_run["candidate_contact_rows"] == 2
        assert dry_run["deduped_contact_rows"] == 2
        assert dry_run["inserted_or_updated_rows"] == 0
        assert first_run["candidate_contact_rows"] == 2
        assert first_run["deduped_contact_rows"] == 2
        assert first_run["inserted_or_updated_rows"] == 2
        assert second_run["candidate_contact_rows"] == 2
        assert second_run["deduped_contact_rows"] == 2
        assert second_run["inserted_or_updated_rows"] == 2
        assert [dict(row) for row in clean_contacts] == [
            {"name": "First Backfill", "position": "Buyer", "email": "first.backfill@example.com"},
            {"name": "Second Backfill", "position": "Director", "email": "second.backfill@example.com"},
        ]
    finally:
        await engine.dispose()


async def test_tendata_raw_contacts_backfill_skips_missing_email_and_dedupes_repeated_email() -> None:
    engine = make_engine()
    cleanup = CleanupService()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"td backfill dedupe {uuid4().hex}")
            raw_id = await _raw_tendata(
                conn,
                keyword_master_id=keyword_master_id,
                source_id=f"td-backfill-dedupe-{uuid4().hex}",
                name=f"Backfill Dedupe Buyer {uuid4().hex}",
                country_iso3="USA",
                contacts_count=3,
            )
            clean_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_companies (name, name_normalized, country_iso3, contacts_count)
                        VALUES (:name, :name_normalized, 'USA', 3)
                        RETURNING id
                        """
                    ),
                    {"name": "Mapped Dedupe Buyer", "name_normalized": f"mapped-dedupe-{uuid4().hex}"},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_company_sources
                      (clean_company_id, source_type, source_company_id, source_key)
                    VALUES (:clean_company_id, 'tendata', :raw_company_id, 'manual-test')
                    """
                ),
                {"clean_company_id": clean_id, "raw_company_id": raw_id},
            )
            await _raw_tendata_contact(
                conn,
                raw_company_id=raw_id,
                source_contact_id=f"tdc-{uuid4().hex}",
                name="No Email Contact",
                position="Ignored",
                email=None,
            )
            await _raw_tendata_contact(
                conn,
                raw_company_id=raw_id,
                source_contact_id=f"tdc-{uuid4().hex}",
                name="Sparse Duplicate",
                position=None,
                email="repeat@example.com",
                created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            )
            await _raw_tendata_contact(
                conn,
                raw_company_id=raw_id,
                source_contact_id=f"tdc-{uuid4().hex}",
                name="Complete Duplicate",
                position="Sourcing Lead",
                email="REPEAT@example.com",
                phone="+1-555-0400",
                created_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
            )

            result = await cleanup.backfill_tendata_raw_contacts(conn, dry_run=False, raw_company_id=raw_id)
            clean_contacts = (
                await conn.execute(
                    text(
                        """
                        SELECT name, position, email, phone
                        FROM clean_contacts
                        WHERE clean_company_id = :clean_company_id
                        """
                    ),
                    {"clean_company_id": clean_id},
                )
            ).mappings().all()

        assert result["candidate_contact_rows"] == 2
        assert result["deduped_contact_rows"] == 1
        assert [dict(row) for row in clean_contacts] == [
            {
                "name": "Complete Duplicate",
                "position": "Sourcing Lead",
                "email": "REPEAT@example.com",
                "phone": "+1-555-0400",
            }
        ]
    finally:
        await engine.dispose()


async def test_keyword_cancellation_hides_only_last_coverage_and_clears_private_state() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "cancel")
            keep_keyword = await _keyword_master(conn, f"keep {uuid4().hex}")
            cancel_keyword = await _keyword_master(conn, f"cancel {uuid4().hex}")
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES
                      (:tenant_id, :keep_keyword, 'keep', 'active'),
                      (:tenant_id, :cancel_keyword, 'cancel', 'active')
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "keep_keyword": keep_keyword,
                    "cancel_keyword": cancel_keyword,
                },
            )
            covered_by_two = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_companies (name, name_normalized, country_iso3)
                        VALUES (:name, :name_normalized, 'USA')
                        RETURNING id
                        """
                    ),
                    {"name": "Two Coverage Buyer", "name_normalized": f"two-{uuid4().hex}"},
                )
            ).scalar_one()
            last_coverage = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_companies (name, name_normalized, country_iso3)
                        VALUES (:name, :name_normalized, 'USA')
                        RETURNING id
                        """
                    ),
                    {"name": "Last Coverage Buyer", "name_normalized": f"last-{uuid4().hex}"},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_company_keywords (clean_company_id, keyword_master_id)
                    VALUES
                      (:covered_by_two, :keep_keyword),
                      (:covered_by_two, :cancel_keyword),
                      (:last_coverage, :cancel_keyword)
                    """
                ),
                {
                    "covered_by_two": covered_by_two,
                    "last_coverage": last_coverage,
                    "keep_keyword": keep_keyword,
                    "cancel_keyword": cancel_keyword,
                },
            )
            await run_fan_out_for_tenant_keyword(conn, tenant_id=tenant_id, keyword_master_id=keep_keyword)
            await run_fan_out_for_tenant_keyword(conn, tenant_id=tenant_id, keyword_master_id=cancel_keyword)
            last_tc = (
                await conn.execute(
                    text(
                        """
                        UPDATE tenant_companies
                        SET model_score = 80, score = 81, note = 'private', tags = ARRAY['hot'],
                            business_status = 'in_group'
                        WHERE tenant_id = :tenant_id AND clean_company_id = :clean_company_id
                        RETURNING id
                        """
                    ),
                    {"tenant_id": tenant_id, "clean_company_id": last_coverage},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO groups (id, tenant_id, name)
                    VALUES (:group_id, :tenant_id, '取消订阅测试组')
                    """
                ),
                {"group_id": str(new_uuid()), "tenant_id": tenant_id},
            )
            group_id = (
                await conn.execute(text("SELECT id FROM groups WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO group_members (id, tenant_id, group_id, tenant_company_id, added_by)
                    VALUES (:id, :tenant_id, :group_id, :tenant_company_id, 'manual')
                    """
                ),
                {"id": str(new_uuid()), "tenant_id": tenant_id, "group_id": group_id, "tenant_company_id": last_tc},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_jobs (id, tenant_id, tenant_company_id, status)
                    VALUES (:id, :tenant_id, :tenant_company_id, 'pending')
                    """
                ),
                {"id": str(new_uuid()), "tenant_id": tenant_id, "tenant_company_id": last_tc},
            )

            await conn.execute(
                text(
                    """
                    UPDATE tenant_keyword
                    SET status = 'deleted'
                    WHERE tenant_id = :tenant_id AND keyword_master_id = :cancel_keyword
                    """
                ),
                {"tenant_id": tenant_id, "cancel_keyword": cancel_keyword},
            )
            result = await fan_out.hide_tenant_companies_for_cancelled_keyword(
                conn,
                tenant_id=tenant_id,
                keyword_master_id=cancel_keyword,
            )

            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT clean_company_id, visibility_status, business_status, model_score, score, note, tags
                        FROM tenant_companies
                        WHERE tenant_id = :tenant_id
                        ORDER BY clean_company_id
                        """
                    ),
                    {"tenant_id": tenant_id},
                )
            ).mappings().all()
            group_count = (
                await conn.execute(text("SELECT count(*) FROM group_members WHERE tenant_company_id = :id"), {"id": last_tc})
            ).scalar_one()
            job_count = (
                await conn.execute(text("SELECT count(*) FROM scoring_jobs WHERE tenant_company_id = :id"), {"id": last_tc})
            ).scalar_one()

        by_clean = {row["clean_company_id"]: row for row in rows}
        assert result["hidden"] == 1
        assert by_clean[covered_by_two]["visibility_status"] == "visible"
        assert by_clean[last_coverage]["visibility_status"] == "hidden"
        assert by_clean[last_coverage]["business_status"] == "new"
        assert by_clean[last_coverage]["model_score"] is None
        assert by_clean[last_coverage]["score"] is None
        assert by_clean[last_coverage]["note"] is None
        assert list(by_clean[last_coverage]["tags"] or []) == []
        assert group_count == 0
        assert job_count == 0
    finally:
        await engine.dispose()


async def test_tenant_keyword_delete_triggers_visibility_recalculation() -> None:
    engine = make_engine()
    settings = TenantSettingsService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "settings-cancel")
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
                    "email": f"settings-cancel-{uuid4().hex[:8]}@example.com",
                },
            )
            keyword_master_id = await _keyword_master(conn, f"settings cancel {uuid4().hex}")
            keyword_id = str(new_uuid())
            clean_company_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_companies (name, name_normalized, country_iso3)
                        VALUES (:name, :name_normalized, 'USA')
                        RETURNING id
                        """
                    ),
                    {"name": "Settings Cancel Buyer", "name_normalized": f"settings-cancel-{uuid4().hex}"},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_company_keywords (clean_company_id, keyword_master_id)
                    VALUES (:clean_company_id, :keyword_master_id)
                    """
                ),
                {"clean_company_id": clean_company_id, "keyword_master_id": keyword_master_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES (:tenant_id, :keyword_master_id, 'PCB', 'active')
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_keywords
                      (id, tenant_id, keyword, keyword_normalized, status, created_by, keyword_master_id)
                    VALUES
                      (:id, :tenant_id, 'PCB', 'pcb', 'active', :created_by, :keyword_master_id)
                    """
                ),
                {
                    "id": keyword_id,
                    "tenant_id": tenant_id,
                    "created_by": user_id,
                    "keyword_master_id": keyword_master_id,
                },
            )
            await run_fan_out_for_tenant_keyword(
                conn,
                tenant_id=tenant_id,
                keyword_master_id=keyword_master_id,
            )

            await settings.delete_keyword(conn, tenant_id=tenant_id, keyword_id=keyword_id)

            row = (
                await conn.execute(
                    text(
                        """
                        SELECT tk.status AS tenant_keyword_status,
                               ck.status AS collection_keyword_status,
                               tc.visibility_status
                        FROM tenant_keyword tk
                        JOIN collection_keywords ck
                          ON ck.tenant_id = tk.tenant_id
                         AND ck.keyword_master_id = tk.keyword_master_id
                        JOIN tenant_companies tc
                          ON tc.tenant_id = tk.tenant_id
                         AND tc.clean_company_id = :clean_company_id
                        WHERE tk.tenant_id = :tenant_id
                          AND tk.keyword_master_id = :keyword_master_id
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "keyword_master_id": keyword_master_id,
                        "clean_company_id": clean_company_id,
                    },
                )
            ).mappings().one()

        assert row["tenant_keyword_status"] == "deleted"
        assert row["collection_keyword_status"] == "deleted"
        assert row["visibility_status"] == "hidden"
    finally:
        await engine.dispose()


async def test_lixiaoyun_stage1_tendata_raw_inherits_platform_keyword_and_materializes_subscribers() -> None:
    engine = make_engine()
    collection = CollectionService()
    cleanup = CleanupService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "stage1")
            user_id = str(new_uuid())
            keyword_master_id = await _keyword_master(conn, f"stage1 pcb {uuid4().hex}")
            keyword_id = str(new_uuid())
            task_id = str(new_uuid())
            tendata_source_id = f"td-stage1-{uuid4().hex}"
            buyer_name = f"Stage1 Overseas Buyer {uuid4().hex}"
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
                    "email": f"stage1-{uuid4().hex[:8]}@example.com",
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_keyword (tenant_id, keyword_master_id, keyword_raw, status)
                    VALUES (:tenant_id, :keyword_master_id, 'PCB', 'active')
                    """
                ),
                {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_keywords
                      (id, tenant_id, keyword, keyword_normalized, status, created_by, keyword_master_id)
                    VALUES
                      (:keyword_id, :tenant_id, 'PCB', 'pcb', 'active', :user_id, :keyword_master_id)
                    """
                ),
                {
                    "keyword_id": keyword_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "keyword_master_id": keyword_master_id,
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_tasks
                      (id, keyword, keyword_normalized, countries, countries_hash, source_types, task_type, context)
                    VALUES
                      (:task_id, 'PCB', 'pcb', '[]'::jsonb, '', '["lixiaoyun"]'::jsonb,
                       'competitor_search', '{"stage": "lixiaoyun_competitors"}'::jsonb)
                    """
                ),
                {"task_id": task_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                    VALUES (:id, :task_id, :keyword_id, :tenant_id)
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "task_id": task_id,
                    "keyword_id": keyword_id,
                    "tenant_id": tenant_id,
                },
            )

            summary = await collection._route_and_enqueue(
                conn,
                task_id=task_id,
                rows=[
                    {
                        "target_table": "lixiaoyun_raw_companies",
                        "source_id": f"lx-stage1-{uuid4().hex}",
                        "company_name_en": "Stage1 PCB Supplier",
                    },
                    {
                        "target_table": "tendata_raw_companies",
                        "tid": tendata_source_id,
                        "name": buyer_name,
                        "country_iso3": "USA",
                        "product_tags": ["pcb"],
                    },
                ],
            )
            raw_id = (
                await conn.execute(
                    text(
                        """
                        SELECT id
                        FROM tendata_raw_companies
                        WHERE source_id = :source_id
                        """
                    ),
                    {"source_id": tendata_source_id},
                )
            ).scalar_one()
            await cleanup._clean_and_link(conn, raw_table="tendata_raw_companies", raw_row_id=str(raw_id))
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT trc.keyword_master_id,
                               cck.keyword_master_id AS clean_keyword_master_id,
                               tc.visibility_status
                        FROM tendata_raw_companies trc
                        JOIN clean_companies cc
                          ON cc.name_normalized = normalize_company_name(trc.name)
                         AND cc.country_iso3 = trc.country_iso3
                        JOIN clean_company_keywords cck
                          ON cck.clean_company_id = cc.id
                        JOIN tenant_companies tc
                          ON tc.clean_company_id = cc.id
                         AND tc.tenant_id = :tenant_id
                        WHERE trc.id = :raw_id
                        """
                    ),
                    {"tenant_id": tenant_id, "raw_id": raw_id},
                )
            ).mappings().one()

        assert summary == {"inserted": 2, "updated": 0, "enqueued": 1}
        assert str(row["keyword_master_id"]) == keyword_master_id
        assert str(row["clean_keyword_master_id"]) == keyword_master_id
        assert row["visibility_status"] == "visible"
    finally:
        await engine.dispose()


async def test_hidden_tenant_company_cannot_be_operated_from_detail_scoring_group_or_sending() -> None:
    engine = make_engine()
    scoring = ScoringService()
    ops = TenantOpsService()
    messaging = TenantMessagingService()
    query = TenantQueryService()
    try:
        async with engine.begin() as conn:
            tenant_id = await _tenant(conn, "hidden-ops")
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
                    "email": f"hidden-ops-{uuid4().hex[:8]}@example.com",
                },
            )
            clean_company_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_companies
                          (name, name_normalized, country_iso3, website)
                        VALUES
                          ('Hidden Ops Buyer', :name_normalized, 'USA', 'https://hidden-ops.example')
                        RETURNING id
                        """
                    ),
                    {"name_normalized": f"hidden-ops-{uuid4().hex}"},
                )
            ).scalar_one()
            tenant_company_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO tenant_companies
                          (tenant_id, clean_company_id, business_status, data_status, visibility_status)
                        VALUES
                          (:tenant_id, :clean_company_id, 'new', 'ready', 'hidden')
                        RETURNING id
                        """
                    ),
                    {"tenant_id": tenant_id, "clean_company_id": clean_company_id},
                )
            ).scalar_one()
            clean_contact_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO clean_contacts (clean_company_id, name, position, email)
                        VALUES (:clean_company_id, 'Hidden Contact', 'Buyer', 'hidden@example.com')
                        RETURNING id
                        """
                    ),
                    {"clean_company_id": clean_company_id},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO tenant_contacts
                      (tenant_id, clean_contact_id, clean_company_id, contact_status, is_sendable)
                    VALUES
                      (:tenant_id, :clean_contact_id, :clean_company_id, 'available', true)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "clean_contact_id": clean_contact_id,
                    "clean_company_id": clean_company_id,
                },
            )
            group = await ops.create_group(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={"name": f"隐藏公司测试组-{uuid4().hex[:8]}"},
            )
            plan = await messaging.create_sending_plan(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                payload={
                    "name": f"隐藏公司发信计划-{uuid4().hex[:8]}",
                    "recipient_source": "manual",
                    "recipient_config": {"tenant_company_ids": [str(tenant_company_id)]},
                },
            )

            with pytest.raises(AppError) as detail_error:
                await query.v3_company_detail(conn, tenant_id, str(clean_company_id))
            scoring_result = await scoring.enqueue_jobs(
                conn,
                tenant_id=tenant_id,
                tenant_company_ids=[str(tenant_company_id)],
            )
            sending_candidates = await messaging.preview_plan_recipients(
                conn,
                tenant_id=tenant_id,
                plan_id=plan["id"],
            )

            with pytest.raises(AppError) as group_error:
                await ops.add_group_members(
                    conn,
                    tenant_id=tenant_id,
                    group_id=group["id"],
                    user_id=user_id,
                    payload={"tenant_company_ids": [str(tenant_company_id)]},
                )

        assert detail_error.value.status_code == 404
        assert scoring_result["enqueued_count"] == 0
        assert sending_candidates == []
        assert group_error.value.status_code == 404
    finally:
        await engine.dispose()
