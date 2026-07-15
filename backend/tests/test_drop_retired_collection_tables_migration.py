"""T-21 Phase B 退役表迁移契约与真实 PostgreSQL 回滚测试。"""

import importlib.util
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

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
    assert MIGRATION_PATH.exists(), "Phase B 迁移文件尚未创建"
    spec = importlib.util.spec_from_file_location("t21_phase_b_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _upgrade_statements(migration, monkeypatch) -> list[str]:
    executed: list[str] = []

    class Connection:
        def exec_driver_sql(self, statement: str) -> None:
            executed.append(statement.strip())

    monkeypatch.setattr(migration.op, "get_bind", lambda: Connection())
    migration.upgrade()
    return executed


def test_migration_has_strict_order_without_cascade(monkeypatch):
    migration = _load_migration()
    executed = _upgrade_statements(migration, monkeypatch)

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


def _local_database_url() -> str:
    database_url = os.getenv("T21_MIGRATION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("未设置 T21_MIGRATION_TEST_DATABASE_URL")
    parsed = urlparse(database_url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}, "迁移集成测试只允许本机 PostgreSQL"
    return database_url


@pytest.fixture
def postgres_schema():
    connection = psycopg.connect(_local_database_url(), autocommit=True)
    schema = f"t21_{uuid4().hex}"
    connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield connection, schema
    finally:
        connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        connection.close()


def _create_tables(connection, schema: str, tables: tuple[str, ...]) -> None:
    connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    for table in tables:
        connection.execute(
            sql.SQL("CREATE TABLE {} (id integer PRIMARY KEY)").format(sql.Identifier(table))
        )


def _run_upgrade_sql(connection, schema: str, migration, monkeypatch) -> None:
    statements = _upgrade_statements(migration, monkeypatch)
    with connection.transaction():
        for statement in statements:
            connection.execute(statement.replace("public.", f'"{schema}".'))


def _existing_tables(connection, schema: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = %s
        """,
        (schema,),
    ).fetchall()
    return {row[0] for row in rows}


def test_upgrade_accepts_all_fifteen_tables(postgres_schema, monkeypatch):
    migration = _load_migration()
    connection, schema = postgres_schema
    _create_tables(connection, schema, OPTIONAL_TABLES + REQUIRED_TABLES)

    _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert _existing_tables(connection, schema) == set()


def test_upgrade_accepts_production_shape_with_four_optional_tables_missing(
    postgres_schema,
    monkeypatch,
):
    migration = _load_migration()
    connection, schema = postgres_schema
    _create_tables(connection, schema, REQUIRED_TABLES)

    _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert _existing_tables(connection, schema) == set()


def test_missing_required_table_rolls_back_all_prior_drops(postgres_schema, monkeypatch):
    migration = _load_migration()
    connection, schema = postgres_schema
    existing = OPTIONAL_TABLES + REQUIRED_TABLES[:-1]
    _create_tables(connection, schema, existing)

    with pytest.raises(psycopg.errors.UndefinedTable):
        _run_upgrade_sql(connection, schema, migration, monkeypatch)

    assert _existing_tables(connection, schema) == set(existing)


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

    assert _existing_tables(connection, schema) == set(existing) | {"external_consumer"}
