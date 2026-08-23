"""20260824_0002 删除遗留情报四表：迁移契约、运行时退役锁定，以及本机 PostgreSQL 上的往返与回滚。

纯 mock 用例只锁语句序列与结构性事实（顺序 / 分区 / UNIQUE / 索引 / 不还原触发器与 policy），
不复制列清单——列、类型、NOT NULL 的逐项对照由真库用例在临时 schema 内做
（需 `T21_MIGRATION_TEST_DATABASE_URL`，未设则跳过；脚手架见 tests/migration_helpers.py）。
"""

import re
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
    Path(__file__).parents[1] / "alembic" / "versions" / "20260824_0002_drop_intelligence_tables.py"
)

DROP_ORDER = (
    "intelligence_article_publications",
    "intelligence_subscriptions",
    "intelligence_articles",
    "intelligence_sources",
)
CREATE_ORDER = (
    "intelligence_sources",
    "intelligence_articles",
    "intelligence_articles_default",
    "intelligence_subscriptions",
    "intelligence_article_publications",
)


@pytest.fixture(scope="module")
def migration():
    return load_migration(MIGRATION_PATH, "drop_intelligence_migration")


def test_upgrade_deletes_scene_row_then_drops_in_fk_order_without_cascade(migration, monkeypatch):
    executed = collect_statements(migration, monkeypatch, "upgrade")

    assert migration.revision == "20260824_0002"
    assert migration.down_revision == "20260824_0001"
    assert executed[:2] == [
        "SET LOCAL lock_timeout = '5s'",
        "SET LOCAL statement_timeout = '30s'",
    ]
    # 先删 AI 场景默认行（隐藏后无人能改，留着会让被引用模型删不掉），再按引用方 → 被引用方删表
    assert executed[2] == (
        "DELETE FROM public.ai_scene_defaults WHERE scene = 'intelligence_summary'"
    )
    assert executed[3:] == [f"DROP TABLE public.{table}" for table in DROP_ORDER]
    assert all("IF EXISTS" not in s.upper() and "CASCADE" not in s.upper() for s in executed)


def test_downgrade_rebuilds_structure_in_dependency_order(migration, monkeypatch):
    executed = collect_statements(migration, monkeypatch, "downgrade")

    creates = [s for s in executed if s.startswith("CREATE TABLE")]
    created_order = [re.match(r"CREATE TABLE public\.(\w+)", s).group(1) for s in creates]
    # 被引用方先建：subscriptions 必须早于 publications；DEFAULT 分区紧跟父表
    assert created_order == list(CREATE_ORDER)

    by_table = dict(zip(created_order, creates, strict=True))
    assert "PARTITION BY RANGE (created_at)" in by_table["intelligence_articles"]
    assert (
        "PARTITION OF public.intelligence_articles DEFAULT"
        in by_table["intelligence_articles_default"]
    )
    assert "UNIQUE (tenant_id, article_id)" in by_table["intelligence_article_publications"]
    assert (
        "REFERENCES public.intelligence_subscriptions(id)"
        in by_table["intelligence_article_publications"]
    )
    assert any(
        "CREATE INDEX idx_article_publications_tenant" in s and "(tenant_id, status)" in s
        for s in executed
    )
    # 按 docstring 约定：不还原触发器与 RLS policy，也不回灌已删的场景默认行
    assert not any("TRIGGER" in s.upper() or "POLICY" in s.upper() for s in executed)
    assert not any("ai_scene_defaults" in s for s in executed)


def test_runtime_code_no_longer_references_intelligence_module():
    from app.db import partitions
    from app.schemas.admin_config import AISceneDefaultUpdate
    from scripts import init_instance

    assert [table for table, _ in partitions._MANAGED] == ["audit_logs", "emails"]
    assert "intelligence_summary" not in init_instance.AI_SCENE_SEEDS
    # 写入侧同步收口：PUT scene-defaults 不再接受该场景，迁移删掉的默认行不会被写回
    with pytest.raises(ValueError):
        AISceneDefaultUpdate(scene="intelligence_summary", model_id="m1")


# ---------------------------------------------------------------- 真库往返（本机 PostgreSQL，可选）

# downgrade 的四表引用这些父表；临时 schema 里只需最小桩
_STUB_PARENTS = ("tenants", "users", "ai_models", "ai_usage_logs")

# 对照生产快照 2026-08-23 抽查的列契约：(表, 列, 数据类型, 是否可空)
_COLUMN_CONTRACT = (
    ("intelligence_sources", "name", "character varying", "NO"),
    ("intelligence_sources", "fetch_config", "jsonb", "NO"),
    ("intelligence_sources", "url", "text", "YES"),
    ("intelligence_articles", "title", "character varying", "NO"),
    ("intelligence_articles", "ai_relevance_score", "numeric", "YES"),
    ("intelligence_articles", "created_at", "timestamp with time zone", "NO"),
    ("intelligence_subscriptions", "min_relevance", "numeric", "NO"),
    ("intelligence_article_publications", "article_id", "uuid", "NO"),
    ("intelligence_article_publications", "subscription_id", "uuid", "YES"),
)


def _prepare_schema(connection, schema: str) -> None:
    connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
    for table in _STUB_PARENTS:
        connection.execute(
            sql.SQL("CREATE TABLE {} (id uuid PRIMARY KEY)").format(sql.Identifier(table))
        )
    connection.execute(
        """
        CREATE TABLE ai_scene_defaults (
            id uuid PRIMARY KEY,
            instance_id text NOT NULL,
            scene text NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO ai_scene_defaults (id, instance_id, scene) VALUES
            (gen_random_uuid(), 'default', 'intelligence_summary'),
            (gen_random_uuid(), 'instance_b', 'intelligence_summary'),
            (gen_random_uuid(), 'default', 'scoring')
        """
    )


def _scene_rows(connection, schema: str) -> list[str]:
    rows = connection.execute(
        sql.SQL("SELECT scene FROM {}.ai_scene_defaults ORDER BY scene").format(
            sql.Identifier(schema)
        )
    ).fetchall()
    return [row[0] for row in rows]


def _column_shape(connection, schema: str, table: str, column: str) -> tuple[str, str]:
    row = connection.execute(
        """
        SELECT data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """,
        (schema, table, column),
    ).fetchone()
    assert row is not None, f"{table}.{column} 不存在"
    return row[0], row[1]


def test_round_trip_on_local_postgres(postgres_schema, migration, monkeypatch):
    connection, schema = postgres_schema
    _prepare_schema(connection, schema)
    downgrade = collect_statements(migration, monkeypatch, "downgrade")
    upgrade = collect_statements(migration, monkeypatch, "upgrade")

    # downgrade：四表 + DEFAULT 分区建出来，抽查列的类型与可空性与快照一致
    run_statements_in_schema(connection, schema, downgrade)
    assert set(CREATE_ORDER) <= existing_tables(connection, schema)
    for table, column, data_type, nullable in _COLUMN_CONTRACT:
        assert _column_shape(connection, schema, table, column) == (data_type, nullable), (
            f"{table}.{column}"
        )
    partitioned = connection.execute(
        """
        SELECT c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = 'intelligence_articles'
        """,
        (schema,),
    ).fetchone()
    assert partitioned == ("p",)

    # upgrade：四表与分区全部消失，只删 intelligence_summary 的场景行，其余场景保留
    run_statements_in_schema(connection, schema, upgrade)
    assert existing_tables(connection, schema) == set(_STUB_PARENTS) | {"ai_scene_defaults"}
    assert _scene_rows(connection, schema) == ["scoring"]

    # 再次 downgrade 仍可重建（结构定义自洽，不依赖已删的行）
    run_statements_in_schema(connection, schema, downgrade)
    assert set(CREATE_ORDER) <= existing_tables(connection, schema)


def test_missing_table_rolls_back_scene_delete_and_prior_drops(
    postgres_schema, migration, monkeypatch
):
    connection, schema = postgres_schema
    _prepare_schema(connection, schema)
    run_statements_in_schema(
        connection, schema, collect_statements(migration, monkeypatch, "downgrade")
    )
    # 模拟带外删表：最后一张 intelligence_sources 不在
    connection.execute(sql.SQL("DROP TABLE {}.intelligence_sources").format(sql.Identifier(schema)))
    before = existing_tables(connection, schema)

    with pytest.raises(psycopg.errors.UndefinedTable):
        run_statements_in_schema(
            connection, schema, collect_statements(migration, monkeypatch, "upgrade")
        )

    # 不带 IF EXISTS 的意义：任一步失败整轮回滚——前三张表与场景行都还在
    assert existing_tables(connection, schema) == before
    assert _scene_rows(connection, schema) == [
        "intelligence_summary",
        "intelligence_summary",
        "scoring",
    ]
