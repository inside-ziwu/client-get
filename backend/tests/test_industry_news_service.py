from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import AppError
from app.services.industry_news.fetchers import RawItem
from app.services.industry_news.service import IndustryNewsService

NOW = datetime(2026, 8, 23, 8, 0, tzinfo=UTC)


def _result(*, first=None, all_rows=None, scalar=None, rowcount=1):
    mappings = MagicMock()
    mappings.first.return_value = first
    mappings.all.return_value = all_rows or []
    result = MagicMock()
    result.mappings.return_value = mappings
    result.rowcount = rowcount
    if scalar is not None:
        result.__bool__ = lambda self: True
    return result


def _conn_for_list(industry="PCB", items=None, total=1):
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            _result(first={"industry": industry}),
            _result(all_rows=items or []),
        ]
    )
    conn.scalar = AsyncMock(return_value=total)
    return conn


@pytest.mark.asyncio
async def test_list_items_sql_has_cast_active_window_and_order():
    items = [
        {
            "id": "i1",
            "title": "Hello",
            "url": "https://example.com/a",
            "published_at": NOW,
            "fetched_at": NOW,
            "source_id": "s1",
            "source_name": "PCEA",
            "source_url": "https://pcea.net/feed/",
            "category": "PCB 技术 / 工程",
            "lang": "en",
            "is_read": False,
        }
    ]
    conn = _conn_for_list(items=items, total=3)
    service = IndustryNewsService()
    rows, total = await service.list_items(
        conn,
        tenant_id="t1",
        user_id="u1",
        instance_id="default",
        categories=["PCB 技术 / 工程"],
        source_ids=["11111111-1111-1111-1111-111111111111"],
        lang="en",
        unread_only=True,
        page=2,
        page_size=50,
        now_utc=NOW,
    )
    assert total == 3
    assert rows[0]["is_external"] is True
    assert rows[0]["target_domain"] == "example.com"
    list_call = conn.execute.await_args_list[1]
    sql = str(list_call.args[0].text)
    params = list_call.args[1]
    assert "CAST(:categories AS text[])" in sql
    assert "CAST(:source_ids AS uuid[])" in sql
    assert "s.lang = CAST(:lang AS text)" in sql
    assert "s.is_active" in sql
    assert "i.fetched_at >= :window_start" in sql
    assert "ORDER BY i.fetched_at DESC" in sql
    assert "COALESCE(i.published_at, i.fetched_at) DESC" in sql
    assert "i.id DESC" in sql
    assert "LIMIT :limit OFFSET :offset" in sql
    assert params["industry"] == "PCB"
    assert params["unread_only"] is True
    assert params["limit"] == 50
    assert params["offset"] == 50
    assert params["window_start"].tzinfo is not None
    assert params["window_start"] == NOW - timedelta(days=90)


@pytest.mark.asyncio
async def test_list_items_unknown_industry_returns_empty_without_item_query():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result(first={"industry": "unknown"}))
    rows, total = await IndustryNewsService().list_items(
        conn, tenant_id="t1", user_id="u1", instance_id="default"
    )
    assert rows == []
    assert total == 0
    assert conn.execute.await_count == 1


@pytest.mark.asyncio
async def test_fetch_source_skips_old_and_counts_duplicates():
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[_result(rowcount=1), _result(rowcount=0), _result(rowcount=1)]
    )
    service = IndustryNewsService()
    stats = await service.fetch_source(
        conn,
        {
            "id": "s1",
            "instance_id": "default",
            "name": "PCEA",
        },
        run_at=NOW,
        items=[
            RawItem("Old", "https://pcea.net/old", NOW - timedelta(days=91)),
            RawItem("New", "https://pcea.net/new", NOW - timedelta(days=1)),
            RawItem("New", "https://pcea.net/new-2", NOW - timedelta(days=1)),
        ],
    )
    assert stats["fetched"] == 3
    assert stats["skipped_old"] == 1
    assert stats["inserted"] == 1
    assert stats["duplicate"] == 1
    assert stats["ok"] is True
    insert_sql = str(conn.execute.await_args_list[0].args[0].text)
    assert "ON CONFLICT DO NOTHING" in insert_sql
    assert conn.execute.await_args_list[0].args[1]["fetched_at"] == NOW


class _Nested:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Begin:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Engine:
    def __init__(self, conn):
        self.conn = conn

    def begin(self):
        return _Begin(self.conn)


@pytest.mark.asyncio
async def test_run_once_lock_busy_skips():
    conn = AsyncMock()
    conn.scalar = AsyncMock(return_value=False)
    conn.begin_nested = MagicMock(return_value=_Nested())
    stats = await IndustryNewsService().run_once(
        _Engine(conn), instance_id="default", clock=lambda: NOW
    )
    assert stats == {"skipped": True, "reason": "in_progress"}


@pytest.mark.asyncio
async def test_mark_read_not_visible_is_404():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result(first={"industry": "PCB"}))
    conn.scalar = AsyncMock(return_value=None)
    with pytest.raises(AppError) as exc:
        await IndustryNewsService().mark_read(
            conn,
            tenant_id="t1",
            user_id="u1",
            instance_id="default",
            item_id="i1",
            now_utc=NOW,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_filter_options_only_active_sources():
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[
            _result(first={"industry": "PCB"}),
            _result(
                all_rows=[
                    {"id": "s1", "name": "PCEA", "category": "A", "lang": "en"},
                    {"id": "s2", "name": "TPCA", "category": "A", "lang": "zh-TW"},
                ]
            ),
        ]
    )
    data = await IndustryNewsService().list_filter_options(
        conn, tenant_id="t1", instance_id="default"
    )
    sql = str(conn.execute.await_args_list[1].args[0].text)
    assert "is_active = true" in sql
    assert data["has_sources"] is True
    assert data["categories"] == ["A"]
    assert data["langs"] == ["en", "zh-TW"]


@pytest.mark.asyncio
async def test_set_source_active_other_instance_404():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result(first=None))
    with pytest.raises(AppError) as exc:
        await IndustryNewsService().set_source_active(
            conn, instance_id="default", source_id="s1", is_active=False
        )
    assert exc.value.status_code == 404
    sql = str(conn.execute.await_args.args[0].text)
    params = conn.execute.await_args.args[1]
    assert "instance_id = :instance_id" in sql
    assert params["instance_id"] == "default"


@pytest.mark.asyncio
async def test_fetch_source_zero_items_marks_error_only():
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=_result())
    stats = await IndustryNewsService().fetch_source(
        conn, {"id": "s1", "instance_id": "default", "name": "PCEA"}, run_at=NOW, items=[]
    )
    assert stats["ok"] is False
    assert conn.execute.await_count == 1
    sql = str(conn.execute.await_args.args[0].text)
    params = conn.execute.await_args.args[1]
    assert "error_count = error_count + 1" in sql
    assert "last_success_at" not in sql
    assert params == {"id": "s1", "instance_id": "default", "run_at": NOW}


@pytest.mark.asyncio
async def test_run_once_default_clock_is_aware():
    conn = AsyncMock()
    conn.scalar = AsyncMock(return_value=False)
    stats = await IndustryNewsService().run_once(_Engine(conn), instance_id="default")
    assert stats == {"skipped": True, "reason": "in_progress"}


@pytest.mark.asyncio
async def test_run_once_isolates_failing_source_with_savepoint(monkeypatch):
    sources = [
        {
            "id": "a",
            "instance_id": "default",
            "name": "A",
            "url": "https://a.test/feed",
            "strategy": "rss",
            "parse_config": {},
        },
        {
            "id": "b",
            "instance_id": "default",
            "name": "B",
            "url": "https://b.test/feed",
            "strategy": "rss",
            "parse_config": {},
        },
    ]
    executed: list[tuple[str, dict]] = []

    async def execute(stmt, params=None):
        sql = str(stmt.text)
        executed.append((sql, params or {}))
        if "FROM industry_news_sources" in sql and "is_active = true" in sql:
            return _result(all_rows=sources)
        if "INSERT INTO industry_news_items" in sql and params["source_id"] == "a":
            raise RuntimeError("index row size exceeds maximum")  # 模拟 ProgramLimitExceeded
        return _result(rowcount=1)

    conn = AsyncMock()
    conn.execute = AsyncMock(side_effect=execute)
    conn.scalar = AsyncMock(return_value=True)
    conn.begin_nested = MagicMock(side_effect=lambda: _Nested())
    service = IndustryNewsService()
    monkeypatch.setattr(
        service,
        "_load_raw_items",
        AsyncMock(
            side_effect=[
                [RawItem("Title A", "https://a.test/x", None)],
                [RawItem("Title B", "https://b.test/y", None)],
            ]
        ),
    )

    stats = await service.run_once(_Engine(conn), instance_id="default", clock=lambda: NOW)

    assert stats["source_count"] == 2
    assert stats["ok_count"] == 1
    assert [item["ok"] for item in stats["sources"]] == [False, True]
    # A：savepoint 内失败 → 回滚后另开 savepoint 记错误；B：正常 savepoint。共 3 次 begin_nested
    assert conn.begin_nested.call_count == 3
    error_marks = [p for sql, p in executed if "error_count = error_count + 1" in sql]
    success_marks = [p for sql, p in executed if "error_count = 0" in sql]
    assert [p["id"] for p in error_marks] == ["a"]
    assert [p["id"] for p in success_marks] == ["b"]
    assert all(p["run_at"] == NOW for p in error_marks + success_marks)
    inserted = [p for sql, p in executed if "INSERT INTO industry_news_items" in sql]
    assert [p["source_id"] for p in inserted] == ["a", "b"]
    assert all(p["fetched_at"] == NOW and p["instance_id"] == "default" for p in inserted)


@pytest.mark.asyncio
async def test_mark_read_checks_visible_set_then_upserts():
    conn = AsyncMock()
    conn.execute = AsyncMock(
        side_effect=[_result(first={"industry": "电路板"}), _result(rowcount=1)]
    )
    conn.scalar = AsyncMock(return_value="i1")
    data = await IndustryNewsService().mark_read(
        conn,
        tenant_id="t1",
        user_id="u1",
        instance_id="default",
        item_id="i1",
        now_utc=NOW,
    )
    assert data == {"item_id": "i1", "is_read": True}
    visible_sql = str(conn.scalar.await_args.args[0].text)
    visible_params = conn.scalar.await_args.args[1]
    assert "s.is_active" in visible_sql
    assert "i.instance_id = :instance_id" in visible_sql
    assert "i.fetched_at >= :window_start" in visible_sql
    assert visible_params["industry"] == "PCB"
    assert visible_params["window_start"] == NOW - timedelta(days=90)
    insert_sql = str(conn.execute.await_args_list[1].args[0].text)
    insert_params = conn.execute.await_args_list[1].args[1]
    assert "ON CONFLICT (user_id, item_id) DO NOTHING" in insert_sql
    assert insert_params == {"tenant_id": "t1", "user_id": "u1", "item_id": "i1"}
