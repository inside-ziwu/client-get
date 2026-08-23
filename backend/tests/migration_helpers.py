"""删表类迁移测试的共享脚手架（20260714_0001、20260824_0002 等复用）。

- `load_migration` / `collect_statements`：纯 mock，把迁移模块按文件路径加载，
  用假连接收集 `exec_driver_sql` 语句（空白折叠成单行，便于逐条断言）。
- `local_database_url` / `run_statements_in_schema`：可选真库用例的门控与执行，
  只允许本机 PostgreSQL（环境变量 `T21_MIGRATION_TEST_DATABASE_URL`），把语句里的
  `public.` 改写到临时 schema 后在一个事务内执行，用于断言整体回滚语义。
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType
from urllib.parse import urlparse

import pytest


def load_migration(path: Path, module_name: str) -> ModuleType:
    assert path.exists(), f"迁移文件不存在：{path}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect_statements(migration: ModuleType, monkeypatch, direction: str = "upgrade") -> list[str]:
    executed: list[str] = []

    class Connection:
        def exec_driver_sql(self, statement: str) -> None:
            executed.append(" ".join(statement.split()))

    monkeypatch.setattr(migration.op, "get_bind", lambda: Connection())
    getattr(migration, direction)()
    return executed


def local_database_url() -> str:
    database_url = os.getenv("T21_MIGRATION_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("未设置 T21_MIGRATION_TEST_DATABASE_URL")
    parsed = urlparse(database_url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}, "迁移集成测试只允许本机 PostgreSQL"
    return database_url


def run_statements_in_schema(connection, schema: str, statements: list[str]) -> None:
    """在临时 schema 内单事务执行迁移语句：任一条失败即整体回滚，与 alembic 在线模式一致。"""
    with connection.transaction():
        for statement in statements:
            connection.execute(statement.replace("public.", f'"{schema}".'))


def existing_tables(connection, schema: str) -> set[str]:
    rows = connection.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = %s",
        (schema,),
    ).fetchall()
    return {row[0] for row in rows}
