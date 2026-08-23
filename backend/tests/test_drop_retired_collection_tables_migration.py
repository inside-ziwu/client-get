"""T-21 Phase B 退役表迁移契约与真实 PostgreSQL 回滚测试。"""

from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from tests.migration_helpers import (
    collect_statements,
    existing_tables,
    load_migration,
    run_statements_in_schema,
)

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260714_0001_drop_retired_collection_tables.py"
)
OPTIONAL_TABLES = (
    "collection_task_keywords",
    "collection_tasks",
    "collection_runs",
    "collection_keywords",
)
REQUIRED_TABLES = (
    "data_source_credentials",
    "data_sources",
    "peer_company_contacts",
    "peer_company_sources",
    "peer_company_keywords",
    "peer_companies",
    "clean_company_keywords",
    "clean_company_sources",
    "clean_contacts",
    "clean_companies",
    "tenant_keyword",
)


def _load_migration():
    return load_migration(MIGRATION_PATH, "t21_phase_b_migration")


def test_migration_has_strict_order_without_cascade(monkeypatch):
    migration = _load_migration()
    executed = collect_statements(migration, monkeypatch)

    assert migration.revision == "20260714_0001"
    assert migration.down_revision == "20260708_0002"
    assert migration.OPTIONAL_TABLES == OPTIONAL_TABLES
    assert migration.REQUIRED_TABLES == REQUIRED_TABLES
    assert executed[:2] == [
        "SET LOCAL lock_timeout = '5s'",
        "SET LOCAL statement_timeout = '30s'",
    ]
    assert executed[2:] == [
        *(f"DROP TABLE IF EXISTS public.{table}" for table in OPTIONAL_TABLES),
        *(f"DROP TABLE public.{table}" for table in REQUIRED_TABLES),
    ]
    assert all("CASCADE" not in statement.upper() for statement in executed)


def test_migration_downgrade_is_explicitly_irreversible():
    migration = _load_migration()

    with pytest.raises(RuntimeError, match="不可逆"):
        migration.downgrade()


def _create_tables(connection, schema: str, tables: tuple[str, ...]) -> None:
    connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    for table in tables:
        connection.execute(
            sql.SQL("CREATE TABLE {} (id integer PRIMARY KEY)").format(sql.Identifier(table))
        )


def _run_upgrade_sql(connection, schema: str, migration, monkeypatch) -> None:
    run_statements_in_schema(connection, schema, collect_statements(migration, monkeypatch))


def test_upgrade_accepts_all_fifteen_tables(postgres_schema, monkeypatch):
    migration = _load_migration()
    connection, schema = postgres_schema
    _create_tables(connection, schema, OPTIONAL_TABLES + REQUIRED_TABLES)

    _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert existing_tables(connection, schema) == set()


def test_upgrade_accepts_production_shape_with_four_optional_tables_missing(
    postgres_schema,
    monkeypatch,
):
    migration = _load_migration()
    connection, schema = postgres_schema
    _create_tables(connection, schema, REQUIRED_TABLES)

    _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert existing_tables(connection, schema) == set()


def test_missing_required_table_rolls_back_all_prior_drops(postgres_schema, monkeypatch):
    migration = _load_migration()
    connection, schema = postgres_schema
    existing = OPTIONAL_TABLES + REQUIRED_TABLES[:-1]
    _create_tables(connection, schema, existing)

    with pytest.raises(psycopg.errors.UndefinedTable):
        _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert existing_tables(connection, schema) == set(existing)


def test_unknown_external_dependency_rolls_back_all_drops(postgres_schema, monkeypatch):
    migration = _load_migration()
    connection, schema = postgres_schema
    existing = OPTIONAL_TABLES + REQUIRED_TABLES
    _create_tables(connection, schema, existing)
    connection.execute(
        """
        CREATE TABLE external_consumer (
          id integer PRIMARY KEY,
          peer_company_id integer REFERENCES peer_companies(id)
        )
        """
    )

    with pytest.raises(psycopg.errors.DependentObjectsStillExist):
        _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert existing_tables(connection, schema) == set(existing) | {"external_consumer"}
