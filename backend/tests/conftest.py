import os

os.environ.setdefault("CLIENTGET_INSTANCE_ID", "default")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")
os.environ.setdefault("CLIENTGET_JWT_SECRET", "test-secret-key-for-unit-tests")
os.environ.setdefault("ADMIN_EMAIL", "test@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("DATA_SOURCE_ENCRYPTION_KEY", "test-encryption-key-0123456789abcdef")
os.environ.setdefault("INTERNAL_SERVICE_SECRET", "test-internal-secret")
os.environ.setdefault("ENGAGELAB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("APP_ENV", "local")


import pytest


@pytest.fixture
def postgres_schema():
    """本机 PostgreSQL 上的一次性 schema（需 T21_MIGRATION_TEST_DATABASE_URL，未设则跳过）。"""
    from uuid import uuid4

    import psycopg
    from psycopg import sql

    from tests.migration_helpers import local_database_url

    connection = psycopg.connect(local_database_url(), autocommit=True)
    schema = f"mig_{uuid4().hex}"
    connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield connection, schema
    finally:
        connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        connection.close()
