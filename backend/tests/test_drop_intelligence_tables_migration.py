"""20260824_0002 删除遗留情报四表：迁移契约与运行时退役锁定（纯 mock，不连库）。

真库往返（upgrade / downgrade 结构逐项对照快照）在 Neon 开发库另行执行，
记录见 .trellis/tasks/08-23-industry-news/research/backend-b-check.md。
"""

import importlib.util
import inspect
import re
from pathlib import Path

BACKEND = Path(__file__).parents[1]
MIGRATION_PATH = BACKEND / "alembic" / "versions" / "20260824_0002_drop_intelligence_tables.py"

DROP_ORDER = (
    "intelligence_article_publications",
    "intelligence_subscriptions",
    "intelligence_articles",
    "intelligence_sources",
)

# 列与 FK 目标固化自 2026-08-23 的 schema_snapshot.json（发布 B 后快照再生时四表会消失，
# 这里不再依赖快照文件，保证 downgrade 契约长期可断言）
SNAPSHOT_COLUMNS = {
    "intelligence_sources": (
        "id",
        "tenant_id",
        "name",
        "source_type",
        "url",
        "fetch_config",
        "industry_tags",
        "is_active",
        "last_fetched_at",
        "error_count",
        "deleted_at",
        "created_at",
        "updated_at",
    ),
    "intelligence_articles": (
        "id",
        "source_id",
        "title",
        "url",
        "author",
        "published_at",
        "content_raw",
        "content_summary",
        "ai_category",
        "ai_tags",
        "ai_relevance_score",
        "ai_model_id",
        "ai_usage_log_id",
        "status",
        "created_at",
    ),
    "intelligence_subscriptions": (
        "id",
        "tenant_id",
        "user_id",
        "industry_tags",
        "min_relevance",
        "notify_enabled",
        "created_at",
        "updated_at",
    ),
    "intelligence_article_publications": (
        "id",
        "tenant_id",
        "article_id",
        "article_created_at",
        "status",
        "has_summary",
        "read_at",
        "matched_by",
        "subscription_id",
        "created_at",
        "updated_at",
    ),
}
SNAPSHOT_FK_TARGETS = {
    "intelligence_sources": ("tenants",),
    "intelligence_articles": ("ai_models", "ai_usage_logs"),
    "intelligence_subscriptions": ("tenants", "users"),
    "intelligence_article_publications": ("tenants", "intelligence_subscriptions"),
}


def _load_migration():
    spec = importlib.util.spec_from_file_location("drop_intelligence_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _statements(migration, monkeypatch, direction: str) -> list[str]:
    executed: list[str] = []

    class Connection:
        def exec_driver_sql(self, statement: str) -> None:
            executed.append(" ".join(statement.split()))

    monkeypatch.setattr(migration.op, "get_bind", lambda: Connection())
    getattr(migration, direction)()
    return executed


def test_upgrade_deletes_scene_row_then_drops_in_fk_order_without_cascade(monkeypatch):
    migration = _load_migration()
    executed = _statements(migration, monkeypatch, "upgrade")

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


def test_downgrade_rebuilds_four_tables_matching_snapshot(monkeypatch):
    migration = _load_migration()
    executed = _statements(migration, monkeypatch, "downgrade")

    creates = [s for s in executed if s.startswith("CREATE TABLE")]
    created_order = [re.match(r"CREATE TABLE public\.(\w+)", s).group(1) for s in creates]
    # 被引用方先建：subscriptions 必须早于 publications；DEFAULT 分区紧跟父表
    assert created_order == [
        "intelligence_sources",
        "intelligence_articles",
        "intelligence_articles_default",
        "intelligence_subscriptions",
        "intelligence_article_publications",
    ]

    by_table = dict(zip(created_order, creates, strict=True))
    for table in DROP_ORDER:
        stmt = by_table[table]
        for column in SNAPSHOT_COLUMNS[table]:
            assert re.search(rf"\b{column}\b", stmt), f"{table} 缺列 {column}"
        for target in SNAPSHOT_FK_TARGETS[table]:
            assert f"REFERENCES public.{target}(id)" in stmt, f"{table} 缺 FK → {target}"
    assert "PARTITION BY RANGE (created_at)" in by_table["intelligence_articles"]
    default_partition = by_table["intelligence_articles_default"]
    assert "PARTITION OF public.intelligence_articles DEFAULT" in default_partition
    assert "UNIQUE (tenant_id, article_id)" in by_table["intelligence_article_publications"]
    assert any(
        "CREATE INDEX idx_article_publications_tenant" in s and "(tenant_id, status)" in s
        for s in executed
    )
    # 按 docstring 约定：不还原触发器与 RLS policy
    assert not any("TRIGGER" in s.upper() or "POLICY" in s.upper() for s in executed)


def test_runtime_code_no_longer_references_intelligence_tables():
    from app.db import partitions
    from scripts import init_instance

    assert [table for table, _ in partitions._MANAGED] == ["audit_logs", "emails"]
    assert "intelligence_summary" not in inspect.getsource(init_instance.main)
