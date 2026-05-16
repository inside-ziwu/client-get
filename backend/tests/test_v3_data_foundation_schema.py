from sqlalchemy import text

from tests.helpers import make_engine


async def _rows(conn, sql: str, params: dict | None = None) -> list[dict]:
    result = await conn.execute(text(sql), params or {})
    return [dict(row) for row in result.mappings().all()]


async def _scalar(conn, sql: str, params: dict | None = None):
    result = await conn.execute(text(sql), params or {})
    return result.scalar()


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


def _assert_bigint_identity(columns: dict[str, dict], column: str = "id") -> None:
    assert columns[column]["data_type"] == "bigint"
    assert columns[column]["is_nullable"] == "NO"
    assert columns[column]["identity_generation"] is not None or columns[column]["column_default"] is not None


async def test_v3_data_foundation_tables_and_columns() -> None:
    engine = make_engine()
    try:
        async with engine.connect() as conn:
            table_names = {
                row["table_name"]
                for row in await _rows(
                    conn,
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """,
                )
            }
            assert {
                "keyword_master",
                "tenant_keyword",
                "lixiaoyun_raw_companies",
                "lixiaoyun_raw_contacts",
                "tendata_raw_companies",
                "tendata_raw_contacts",
                "clean_companies",
                "clean_contacts",
                "clean_company_sources",
                "clean_company_keywords",
                "tenant_companies",
                "tenant_contacts",
                "collection_runs",
                "collection_tasks",
            } <= table_names

            tenant_keyword = await _columns(conn, "tenant_keyword")
            _assert_bigint_identity(tenant_keyword)
            assert {"tenant_id", "keyword_master_id", "keyword_raw", "created_by", "created_at", "status"} <= set(
                tenant_keyword
            )

            for table in (
                "lixiaoyun_raw_companies",
                "tendata_raw_companies",
                "lixiaoyun_raw_contacts",
                "tendata_raw_contacts",
                "clean_companies",
                "clean_contacts",
                "clean_company_sources",
                "clean_company_keywords",
                "tenant_companies",
                "tenant_contacts",
                "collection_runs",
            ):
                _assert_bigint_identity(await _columns(conn, table))

            for table in ("lixiaoyun_raw_companies", "tendata_raw_companies"):
                columns = await _columns(conn, table)
                assert "keyword_master_id" in columns
                assert "source_id" in columns
                assert "task_id" not in columns
                assert "keyword_normalized" not in columns
                assert "last_seen_at" not in columns

            collection_runs = await _columns(conn, "collection_runs")
            assert {"stage", "triggered_by", "triggered_tenant_id"} <= set(collection_runs)
            assert collection_runs["keyword_master_id"]["udt_name"] == "uuid"

            collection_tasks = await _columns(conn, "collection_tasks")
            assert collection_tasks["run_id"]["data_type"] == "bigint"
            assert {"scheduled_biz_date", "batch_no", "page_size", "cursor_snapshot"} <= set(collection_tasks)
    finally:
        await engine.dispose()


async def test_v3_data_foundation_constraints_and_indexes() -> None:
    engine = make_engine()
    try:
        async with engine.connect() as conn:
            tenant_keyword_constraints = await _constraint_defs(conn, "tenant_keyword")
            assert any("UNIQUE (tenant_id, keyword_master_id)" in item for item in tenant_keyword_constraints)
            assert any("CHECK" in item and "active" in item and "deleted" in item for item in tenant_keyword_constraints)

            for table in ("lixiaoyun_raw_contacts", "tendata_raw_contacts"):
                indexes = await _index_defs(conn, table)
                assert any("source_contact_id" in item and "IS NOT NULL" in item for item in indexes)
                assert any("email" in item and "source_contact_id IS NULL" in item for item in indexes)

            clean_sources_constraints = await _constraint_defs(conn, "clean_company_sources")
            assert any("UNIQUE (source_type, source_company_id)" in item for item in clean_sources_constraints)
            assert any("CHECK" in item and "tendata" in item for item in clean_sources_constraints)

            clean_keywords_constraints = await _constraint_defs(conn, "clean_company_keywords")
            assert any("UNIQUE (clean_company_id, keyword_master_id)" in item for item in clean_keywords_constraints)

            run_constraints = await _constraint_defs(conn, "collection_runs")
            assert any("lixiaoyun_competitors" in item and "tendata_customers" in item for item in run_constraints)
            assert any("daily_limit_reached" in item and "completed" in item for item in run_constraints)

            run_indexes = await _index_defs(conn, "collection_runs")
            assert any("keyword_master_id" in item and "provider" in item and "stage" in item for item in run_indexes)
            assert any("UNIQUE" in item and "daily_limit_reached" in item for item in run_indexes)

            task_indexes = await _index_defs(conn, "collection_tasks")
            assert any("run_id" in item and "status" in item and "scheduled_at" in item for item in task_indexes)
    finally:
        await engine.dispose()


async def test_v3_data_foundation_removed_fields_are_not_present() -> None:
    engine = make_engine()
    try:
        async with engine.connect() as conn:
            clean_companies = await _columns(conn, "clean_companies")
            assert "data_completeness" not in clean_companies
            assert "sources" not in clean_companies
            assert clean_companies["reg_capital"]["data_type"] == "numeric"
            assert clean_companies["employee_num"]["data_type"] == "text"
            assert clean_companies["industry_tags"]["data_type"] == "ARRAY"
            assert clean_companies["updated_at"]["data_type"] == "timestamp with time zone"

            tenant_companies = await _columns(conn, "tenant_companies")
            assert "matched_keywords" not in tenant_companies
            assert "score_adjustment" not in tenant_companies
            assert "score_adjusted_at" not in tenant_companies
            assert "score_adjusted_by" not in tenant_companies
            assert "score_adjust_reason" not in tenant_companies
            assert {"model_score", "score", "note", "tags", "visibility_status"} <= set(tenant_companies)
            assert tenant_companies["tags"]["data_type"] == "ARRAY"
            assert tenant_companies["visibility_status"]["column_default"] == "'hidden'::text"

            tenant_contacts = await _columns(conn, "tenant_contacts")
            assert "tenant_company_id" not in tenant_contacts
            assert {"clean_contact_id", "clean_company_id", "contact_status", "is_sendable"} <= set(tenant_contacts)

    finally:
        await engine.dispose()


async def test_tendata_cleaning_pipeline_schema_alignment() -> None:
    engine = make_engine()
    try:
        async with engine.connect() as conn:
            clean_companies_constraints = await _constraint_defs(conn, "clean_companies")
            assert any("UNIQUE (name_normalized, country_iso3)" in item for item in clean_companies_constraints)

            tenant_companies_constraints = await _constraint_defs(conn, "tenant_companies")
            assert any("UNIQUE (tenant_id, clean_company_id)" in item for item in tenant_companies_constraints)
            assert any("CHECK" in item and "visible" in item and "hidden" in item for item in tenant_companies_constraints)
            assert any("CHECK" in item and "in_group" in item and "selected" not in item for item in tenant_companies_constraints)

            tenant_indexes = await _index_defs(conn, "tenant_companies")
            assert any("tenant_id" in item and "visibility_status" in item for item in tenant_indexes)

            for table in ("company_scores", "group_members", "scoring_jobs"):
                columns = await _columns(conn, table)
                assert columns["tenant_company_id"]["data_type"] == "bigint"
                constraints = await _constraint_defs(conn, table)
                assert any("FOREIGN KEY (tenant_company_id)" in item and "tenant_companies(id)" in item for item in constraints)

            group_members = await _columns(conn, "group_members")
            assert group_members["tenant_contact_id"]["data_type"] == "bigint"
            group_constraints = await _constraint_defs(conn, "group_members")
            assert any("FOREIGN KEY (tenant_contact_id)" in item and "tenant_contacts(id)" in item for item in group_constraints)

            clean_sources_constraints = await _constraint_defs(conn, "clean_company_sources")
            assert any("UNIQUE (source_type, source_company_id)" in item for item in clean_sources_constraints)
            clean_keywords_constraints = await _constraint_defs(conn, "clean_company_keywords")
            assert any("UNIQUE (clean_company_id, keyword_master_id)" in item for item in clean_keywords_constraints)
    finally:
        await engine.dispose()
