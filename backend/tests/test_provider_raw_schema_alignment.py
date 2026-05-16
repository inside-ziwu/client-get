from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.ids import new_uuid
from app.main import create_app
from app.security.jwt import create_access_token
from app.services.cleanup_service import CleanupService
from app.services.collection_service import CollectionService
from app.services.keyword_service import get_or_create_keyword_master, normalize_keyword
from tests.helpers import make_engine


async def _rows(conn, sql: str, params: dict | None = None) -> list[dict]:
    result = await conn.execute(text(sql), params or {})
    return [dict(row) for row in result.mappings().all()]


async def _columns(conn, table: str) -> dict[str, dict]:
    rows = await _rows(
        conn,
        """
        SELECT column_name, data_type, udt_name, is_nullable, column_default, identity_generation
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table
        ORDER BY ordinal_position
        """,
        {"table": table},
    )
    return {row["column_name"]: row for row in rows}


async def _constraint_defs(conn, table: str) -> list[str]:
    rows = await _rows(
        conn,
        """
        SELECT pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public' AND t.relname = :table
        ORDER BY c.conname
        """,
        {"table": table},
    )
    return [row["definition"] for row in rows]


async def _index_defs(conn, table: str) -> list[str]:
    rows = await _rows(
        conn,
        """
        SELECT indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = :table
        ORDER BY indexname
        """,
        {"table": table},
    )
    return [row["indexdef"] for row in rows]


async def _keyword_master(conn, keyword: str = "provider raw alignment") -> str:
    return str(
        await get_or_create_keyword_master(
            conn,
            keyword=keyword,
            keyword_normalized=normalize_keyword(keyword),
        )
    )


async def _create_platform_token() -> str:
    user_id = str(new_uuid())
    engine = make_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO platform_users (id, email, password_hash, name, status)
                VALUES (:id, :email, 'hash', '平台管理员', 'active')
                """
            ),
            {"id": user_id, "email": f"provider-raw-{uuid4().hex[:8]}@example.com"},
        )
    await engine.dispose()
    return create_access_token({"sub": user_id, "kind": "platform", "roles": ["platform_admin"]})


async def test_provider_raw_schema_columns_constraints_and_indexes() -> None:
    engine = make_engine()
    try:
        async with engine.connect() as conn:
            tendata_company = await _columns(conn, "tendata_raw_companies")
            for column in (
                "collection_type",
                "detail_status",
                "detail_fetched_at",
                "trade_status",
                "trade_fetched_at",
                "contacts_status",
                "contacts_fetched_at",
                "enrichment_error",
            ):
                assert column in tendata_company
            assert tendata_company["collection_type"]["is_nullable"] == "NO"

            tendata_constraints = await _constraint_defs(conn, "tendata_raw_companies")
            assert any("UNIQUE (keyword_master_id, source_id, collection_type)" in item for item in tendata_constraints)
            assert any("CHECK" in item and "direct_search" in item and "reverse_lookup" in item for item in tendata_constraints)
            assert any("CHECK" in item and "pending" in item and "skipped" in item for item in tendata_constraints)

            wmt_company = await _columns(conn, "waimaotong_raw_companies")
            for column in (
                "keyword_master_id",
                "collection_type",
                "source_id",
                "real_id",
                "address",
                "employee_size",
                "founded_year",
                "description",
                "products",
                "source_tags",
                "emails",
                "trade_amount_3y_usd",
                "trade_count",
                "contacts_count",
                "has_trade_data",
                "search_payload",
                "detail_payload",
                "trade_payload",
                "raw_payload",
                "detail_status",
                "detail_fetched_at",
                "trade_status",
                "trade_fetched_at",
                "contacts_status",
                "contacts_fetched_at",
                "enrichment_error",
                "updated_at",
            ):
                assert column in wmt_company
            assert "task_id" not in wmt_company
            assert "last_seen_at" not in wmt_company
            assert wmt_company["keyword_master_id"]["udt_name"] == "uuid"

            wmt_company_constraints = await _constraint_defs(conn, "waimaotong_raw_companies")
            assert any("UNIQUE (keyword_master_id, source_id, collection_type)" in item for item in wmt_company_constraints)
            assert any("CHECK" in item and "direct_search" in item and "reverse_lookup" in item for item in wmt_company_constraints)

            wmt_contact = await _columns(conn, "waimaotong_raw_contacts")
            for column in (
                "raw_company_id",
                "source_contact_id",
                "name",
                "position",
                "department",
                "email",
                "email_status",
                "phone",
                "mobile",
                "linkedin",
                "whatsapp",
                "source",
                "confidence",
                "raw_payload",
            ):
                assert column in wmt_contact
            assert "source_company_id" not in wmt_contact
            assert "title" not in wmt_contact
            assert "task_id" not in wmt_contact
            assert "last_seen_at" not in wmt_contact
            assert wmt_contact["raw_company_id"]["data_type"] == "bigint"
            assert wmt_contact["email"]["udt_name"] == "citext"
            assert wmt_contact["email"]["is_nullable"] == "YES"

            wmt_contact_constraints = await _constraint_defs(conn, "waimaotong_raw_contacts")
            assert any("FOREIGN KEY (raw_company_id)" in item and "ON DELETE CASCADE" in item for item in wmt_contact_constraints)
            wmt_contact_indexes = await _index_defs(conn, "waimaotong_raw_contacts")
            assert any("source_contact_id" in item and "IS NOT NULL" in item for item in wmt_contact_indexes)
            assert any("email" in item and "source_contact_id IS NULL" in item for item in wmt_contact_indexes)
    finally:
        await engine.dispose()


async def test_tendata_raw_uniqueness_preserves_collection_path_evidence() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"td raw {uuid4().hex}")
            source_id = f"td-{uuid4().hex}"
            first_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO tendata_raw_companies
                          (keyword_master_id, source_id, collection_type, name, country_iso3)
                        VALUES
                          (:keyword_master_id, :source_id, 'reverse_lookup', 'Same Buyer', 'USA')
                        RETURNING id
                        """
                    ),
                    {"keyword_master_id": keyword_master_id, "source_id": source_id},
                )
            ).scalar_one()
            second_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO tendata_raw_companies
                          (keyword_master_id, source_id, collection_type, name, country_iso3)
                        VALUES
                          (:keyword_master_id, :source_id, 'direct_search', 'Same Buyer', 'USA')
                        RETURNING id
                        """
                    ),
                    {"keyword_master_id": keyword_master_id, "source_id": source_id},
                )
            ).scalar_one()

        assert first_id != second_id
    finally:
        await engine.dispose()


async def test_waimaotong_raw_contact_uniqueness_uses_source_id_then_email_fallback() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"wmt raw {uuid4().hex}")
            raw_company_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO waimaotong_raw_companies
                          (keyword_master_id, source_id, collection_type, name, country_iso3)
                        VALUES
                          (:keyword_master_id, :source_id, 'direct_search', 'WMT Buyer', 'DEU')
                        RETURNING id
                        """
                    ),
                    {"keyword_master_id": keyword_master_id, "source_id": f"wmt-{uuid4().hex}"},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_raw_contacts
                      (raw_company_id, source_contact_id, name, position, email, raw_payload)
                    VALUES
                      (:raw_company_id, 'contact-1', 'Alice', 'CEO', NULL, '{}'::jsonb)
                    ON CONFLICT (raw_company_id, source_contact_id)
                    WHERE source_contact_id IS NOT NULL
                    DO UPDATE SET name = EXCLUDED.name
                    """
                ),
                {"raw_company_id": raw_company_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_raw_contacts
                      (raw_company_id, source_contact_id, name, position, email, raw_payload)
                    VALUES
                      (:raw_company_id, 'contact-1', 'Alice Updated', 'CEO', NULL, '{}'::jsonb)
                    ON CONFLICT (raw_company_id, source_contact_id)
                    WHERE source_contact_id IS NOT NULL
                    DO UPDATE SET name = EXCLUDED.name
                    """
                ),
                {"raw_company_id": raw_company_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_raw_contacts
                      (raw_company_id, source_contact_id, name, position, email, raw_payload)
                    VALUES
                      (:raw_company_id, NULL, 'Bob', 'Buyer', 'bob@example.com', '{}'::jsonb)
                    ON CONFLICT (raw_company_id, email)
                    WHERE source_contact_id IS NULL AND email IS NOT NULL
                    DO UPDATE SET name = EXCLUDED.name
                    """
                ),
                {"raw_company_id": raw_company_id},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_raw_contacts
                      (raw_company_id, source_contact_id, name, position, email, raw_payload)
                    VALUES
                      (:raw_company_id, NULL, 'Bob Updated', 'Buyer', 'BOB@example.com', '{}'::jsonb)
                    ON CONFLICT (raw_company_id, email)
                    WHERE source_contact_id IS NULL AND email IS NOT NULL
                    DO UPDATE SET name = EXCLUDED.name
                    """
                ),
                {"raw_company_id": raw_company_id},
            )
            count = (
                await conn.execute(
                    text("SELECT COUNT(*) FROM waimaotong_raw_contacts WHERE raw_company_id = :id"),
                    {"id": raw_company_id},
                )
            ).scalar_one()

        assert count == 2
    finally:
        await engine.dispose()


async def test_waimaotong_persistence_preserves_split_payloads_and_statuses() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"wmt persist {uuid4().hex}")
            source_id = f"wmt-{uuid4().hex}"
            service = CollectionService()
            raw_company_id = await service._upsert_waimaotong_raw(
                conn,
                task_id="legacy-task-id-is-ignored",
                row={
                    "keyword_master_id": keyword_master_id,
                    "source_id": source_id,
                    "collection_type": "direct_search",
                    "name": "Payload Buyer",
                    "country_iso3": "USA",
                    "domain": "payload.example",
                    "industry": "PCB",
                    "phone": "+1",
                    "emails": ["info@payload.example"],
                    "source_tags": ["search-tag"],
                    "search_payload": {"stage": "search"},
                    "raw_payload": {"stage": "raw"},
                },
            )
            await service._upsert_waimaotong_detail(
                conn,
                raw_company_id=raw_company_id,
                row={
                    "address": "1 Main St",
                    "employee_size": "51-200",
                    "founded_year": 2010,
                    "description": "PCB importer",
                    "products": ["pcb"],
                    "detail_payload": {"stage": "detail"},
                },
            )
            await service._upsert_waimaotong_trade(
                conn,
                raw_company_id=raw_company_id,
                row={
                    "trade_amount_3y_usd": 1234.56,
                    "trade_count": 7,
                    "contacts_count": 0,
                    "has_trade_data": True,
                    "trade_payload": {"stage": "trade"},
                },
            )
            await service._upsert_waimaotong_raw_contact(
                conn,
                task_id="legacy-task-id-is-ignored",
                row={
                    "raw_company_id": raw_company_id,
                    "source_contact_id": None,
                    "name": "No Email Preserved",
                    "position": "Buyer",
                    "raw_payload": {"stage": "contact"},
                },
            )
            await service.mark_waimaotong_enrichment_failed(
                conn,
                raw_company_id=raw_company_id,
                stage="detail",
                error={"code": "DETAIL_TIMEOUT"},
            )

            company = (
                await conn.execute(
                    text(
                        """
                        SELECT search_payload, detail_payload, trade_payload, raw_payload,
                               detail_status, trade_status, contacts_status, enrichment_error
                        FROM waimaotong_raw_companies
                        WHERE id = :id
                        """
                    ),
                    {"id": int(raw_company_id)},
                )
            ).mappings().one()
            contact_count = (
                await conn.execute(
                    text("SELECT COUNT(*) FROM waimaotong_raw_contacts WHERE raw_company_id = :id"),
                    {"id": int(raw_company_id)},
                )
            ).scalar_one()

        assert company["search_payload"]["stage"] == "search"
        assert company["detail_payload"]["stage"] == "detail"
        assert company["trade_payload"]["stage"] == "trade"
        assert company["raw_payload"]["stage"] == "raw"
        assert company["detail_status"] == "failed"
        assert company["trade_status"] == "fetched"
        assert company["contacts_status"] == "fetched"
        assert company["enrichment_error"]["stage"] == "detail"
        assert contact_count == 1
    finally:
        await engine.dispose()


async def test_enrichment_status_transitions_cover_pending_fetched_failed_and_skipped() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"status raw {uuid4().hex}")
            service = CollectionService()
            raw_company_id = await service._upsert_waimaotong_raw(
                conn,
                task_id="legacy-task-id-is-ignored",
                row={
                    "keyword_master_id": keyword_master_id,
                    "source_id": f"wmt-{uuid4().hex}",
                    "collection_type": "direct_search",
                    "name": "Status Buyer",
                    "country_iso3": "USA",
                    "raw_payload": {"stage": "search"},
                },
            )
            pending = (
                await conn.execute(
                    text(
                        """
                        SELECT detail_status, trade_status, contacts_status
                        FROM waimaotong_raw_companies
                        WHERE id = :id
                        """
                    ),
                    {"id": int(raw_company_id)},
                )
            ).mappings().one()

            await service._mark_enrichment_status(
                conn,
                "waimaotong_raw_companies",
                raw_company_id,
                "detail",
                "fetched",
            )
            await service._mark_enrichment_status(
                conn,
                "waimaotong_raw_companies",
                raw_company_id,
                "trade",
                "skipped",
            )
            await service._mark_enrichment_status(
                conn,
                "waimaotong_raw_companies",
                raw_company_id,
                "contacts",
                "failed",
                error={"code": "CONTACT_TIMEOUT"},
            )
            final = (
                await conn.execute(
                    text(
                        """
                        SELECT detail_status, detail_fetched_at,
                               trade_status, trade_fetched_at,
                               contacts_status, contacts_fetched_at,
                               enrichment_error
                        FROM waimaotong_raw_companies
                        WHERE id = :id
                        """
                    ),
                    {"id": int(raw_company_id)},
                )
            ).mappings().one()

        assert pending == {
            "detail_status": "pending",
            "trade_status": "pending",
            "contacts_status": "pending",
        }
        assert final["detail_status"] == "fetched"
        assert final["detail_fetched_at"] is not None
        assert final["trade_status"] == "skipped"
        assert final["trade_fetched_at"] is None
        assert final["contacts_status"] == "failed"
        assert final["contacts_fetched_at"] is None
        assert final["enrichment_error"]["stage"] == "contacts"
        assert final["enrichment_error"]["code"] == "CONTACT_TIMEOUT"
    finally:
        await engine.dispose()


async def test_tendata_failed_enrichment_updates_matching_status_and_error() -> None:
    engine = make_engine()
    try:
        async with engine.begin() as conn:
            keyword_master_id = await _keyword_master(conn, f"td status {uuid4().hex}")
            service = CollectionService()
            raw_company_id = await service._upsert_tendata_raw(
                conn,
                task_id="legacy-task-id-is-ignored",
                row={
                    "keyword_master_id": keyword_master_id,
                    "source_id": f"td-{uuid4().hex}",
                    "collection_type": "reverse_lookup",
                    "name": "Tendata Status Buyer",
                    "country_iso3": "USA",
                    "raw_payload": {"stage": "raw"},
                },
            )
            await service.mark_tendata_enrichment_failed(
                conn,
                raw_company_id=raw_company_id,
                stage="trade",
                error={"code": "TRADE_TIMEOUT"},
            )
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT trade_status, trade_fetched_at, enrichment_error
                        FROM tendata_raw_companies
                        WHERE id = :id
                        """
                    ),
                    {"id": int(raw_company_id)},
                )
            ).mappings().one()

        assert row["trade_status"] == "failed"
        assert row["trade_fetched_at"] is None
        assert row["enrichment_error"]["stage"] == "trade"
        assert row["enrichment_error"]["code"] == "TRADE_TIMEOUT"
    finally:
        await engine.dispose()


async def test_cleanup_source_evidence_preserves_collection_path() -> None:
    class RecordingConnection:
        def __init__(self) -> None:
            self.params: list[dict] = []

        async def execute(self, _statement, params: dict) -> None:
            self.params.append(params)

    conn = RecordingConnection()
    cleanup = CleanupService()
    source_id = f"wmt-{uuid4().hex}"

    await cleanup._upsert_clean_company_source(
        conn,
        clean_id="101",
        raw_table="waimaotong_raw_companies",
        raw={"id": 201, "source_id": source_id, "collection_type": "direct_search"},
    )
    await cleanup._upsert_clean_company_source(
        conn,
        clean_id="101",
        raw_table="waimaotong_raw_companies",
        raw={"id": 202, "source_id": source_id, "collection_type": "reverse_lookup"},
    )

    assert conn.params == [
        {
            "clean_id": 101,
            "source_type": "waimaotong",
            "source_company_id": 201,
            "source_key": f"{source_id}|direct_search",
        },
        {
            "clean_id": 101,
            "source_type": "waimaotong",
            "source_company_id": 202,
            "source_key": f"{source_id}|reverse_lookup",
        },
    ]


async def test_admin_raw_api_exposes_key_fields_and_omits_payloads_by_default() -> None:
    engine = make_engine()
    async with engine.begin() as conn:
        keyword_master_id = await _keyword_master(conn, "线路板")
        null_keyword_tendata_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO tendata_raw_companies
                      (keyword_master_id, source_id, collection_type, name, country_iso3)
                    VALUES
                      (NULL, :source_id, 'reverse_lookup', 'No Keyword Tendata', 'USA')
                    RETURNING id
                    """
                ),
                {"source_id": f"td-null-{uuid4().hex}"},
            )
        ).scalar_one()
        tendata_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO tendata_raw_companies
                      (keyword_master_id, source_id, collection_type, name, country_iso3,
                       detail_status, trade_status, contacts_status, raw_payload)
                    VALUES
                      (:keyword_master_id, :source_id, 'reverse_lookup', 'Admin Tendata', 'USA',
                       'fetched', 'fetched', 'skipped', '{"secret": true}'::jsonb)
                    RETURNING id
                    """
                ),
                {"keyword_master_id": keyword_master_id, "source_id": f"td-{uuid4().hex}"},
            )
        ).scalar_one()
        wmt_id = (
            await conn.execute(
                text(
                    """
                    INSERT INTO waimaotong_raw_companies
                      (keyword_master_id, source_id, collection_type, name, country_iso3,
                       industry, employee_size, founded_year, products, trade_amount_3y_usd,
                       trade_count, contacts_count, detail_status, trade_status, contacts_status,
                       search_payload, detail_payload, trade_payload, raw_payload)
                    VALUES
                      (:keyword_master_id, :source_id, 'direct_search', 'Admin WMT', 'DEU',
                       'PCB', '51-200', 2015, ARRAY['pcb'], 5000, 12, 3,
                       'pending', 'pending', 'fetched', '{"secret": "search"}'::jsonb,
                       '{"secret": "detail"}'::jsonb, '{"secret": "trade"}'::jsonb,
                       '{"secret": "raw"}'::jsonb)
                    RETURNING id
                    """
                ),
                {"keyword_master_id": keyword_master_id, "source_id": f"wmt-{uuid4().hex}"},
            )
        ).scalar_one()
    await engine.dispose()

    admin_token = await _create_platform_token()
    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            tendata_response = await client.get(
                "/admin/api/v1/raw/tendata/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"keyword_master_id": keyword_master_id, "page_size": 20},
            )
            tendata_null_keyword_response = await client.get(
                "/admin/api/v1/raw/tendata/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"q": "No Keyword Tendata", "page_size": 20},
            )
            wmt_response = await client.get(
                "/admin/api/v1/raw/waimaotong/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"keyword_master_id": keyword_master_id, "page_size": 20},
            )
            wmt_debug_response = await client.get(
                f"/admin/api/v1/raw/waimaotong/companies/{wmt_id}/debug",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            wmt_filtered_response = await client.get(
                "/admin/api/v1/raw/waimaotong/companies",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={
                    "keyword_master_id": keyword_master_id,
                    "industry": "PCB",
                    "tag": "pcb",
                    "size": "medium",
                    "amount_min": 1000,
                    "amount_max": 6000,
                    "count_min": 10,
                    "count_max": 20,
                    "contact_min": 1,
                    "contact_max": 5,
                    "year_min": 2010,
                    "year_max": 2020,
                    "page_size": 20,
                },
            )

        assert tendata_response.status_code == 200, tendata_response.text
        assert tendata_null_keyword_response.status_code == 200, tendata_null_keyword_response.text
        tendata_rows = tendata_response.json()["data"]
        tendata_row = next(item for item in tendata_rows if item["id"] == str(tendata_id))
        tendata_null_keyword_rows = tendata_null_keyword_response.json()["data"]
        null_keyword_tendata_row = next(
            item for item in tendata_null_keyword_rows if item["id"] == str(null_keyword_tendata_id)
        )
        assert tendata_row["keyword_master_id"] == keyword_master_id
        assert tendata_row["keyword"] == "线路板"
        assert null_keyword_tendata_row["keyword_master_id"] is None
        assert null_keyword_tendata_row["keyword"] is None
        assert tendata_row["collection_type"] == "reverse_lookup"
        assert tendata_row["detail_status"] == "fetched"
        assert tendata_row["contacts_status"] == "skipped"
        assert "raw_payload" not in tendata_row
        assert "search_payload" not in tendata_row

        assert wmt_response.status_code == 200, wmt_response.text
        wmt_rows = wmt_response.json()["data"]
        wmt_row = next(item for item in wmt_rows if item["id"] == str(wmt_id))
        assert wmt_row["collection_type"] == "direct_search"
        assert wmt_row["contacts_status"] == "fetched"
        assert "raw_payload" not in wmt_row
        assert "search_payload" not in wmt_row
        assert "detail_payload" not in wmt_row
        assert "trade_payload" not in wmt_row

        assert wmt_filtered_response.status_code == 200, wmt_filtered_response.text
        filtered_rows = wmt_filtered_response.json()["data"]
        filtered_row = next(item for item in filtered_rows if item["id"] == str(wmt_id))
        assert filtered_row["source_id"].startswith("wmt-")
        assert "raw_payload" not in filtered_row

        assert wmt_debug_response.status_code == 200, wmt_debug_response.text
        debug_payload = wmt_debug_response.json()["data"]
        assert debug_payload["provider"] == "waimaotong"
        assert debug_payload["raw_payload"] == {"secret": "raw"}
        assert debug_payload["search_payload"] == {"secret": "search"}
        assert debug_payload["detail_payload"] == {"secret": "detail"}
        assert debug_payload["trade_payload"] == {"secret": "trade"}
