import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.beijing_time import next_beijing_time
from app.workers import industry_news_fetch as worker


def test_next_beijing_time_same_day_and_next_day():
    before = datetime(2026, 8, 23, 23, 0, tzinfo=UTC)  # 北京 08-24 07:00
    target = next_beijing_time(8, before)
    assert target.hour == 8
    assert (target.month, target.day) == (8, 24)
    after = datetime(2026, 8, 24, 0, 10, tzinfo=UTC)  # 北京 08-24 08:10
    nxt = next_beijing_time(8, after)
    assert (nxt.month, nxt.day) == (8, 25)
    assert nxt.hour == 8


def test_next_beijing_time_cross_month():
    now = datetime(2026, 8, 31, 16, 10, tzinfo=UTC)  # 北京 9/1 00:10
    nxt = next_beijing_time(8, now)
    assert (nxt.year, nxt.month, nxt.day) == (2026, 9, 1)


@pytest.mark.asyncio
async def test_trigger_fetch_in_progress_and_no_sources(monkeypatch):
    worker._background_tasks.add(asyncio.create_task(asyncio.sleep(60)))
    try:
        result = await worker.trigger_fetch(MagicMock(), instance_id="default")
        assert result == {"triggered": False, "reason": "in_progress"}
    finally:
        for task in list(worker._background_tasks):
            task.cancel()
        worker._background_tasks.clear()

    engine = MagicMock()

    class _Begin:
        async def __aenter__(self):
            conn = AsyncMock()
            conn.scalar = AsyncMock(return_value=0)
            return conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    engine.begin.return_value = _Begin()
    result = await worker.trigger_fetch(engine, instance_id="default")
    assert result == {"triggered": False, "reason": "no_sources"}


@pytest.mark.asyncio
async def test_loop_exits_on_stop_event():
    stop = asyncio.Event()
    stop.set()
    await worker.run_industry_news_fetch_loop(
        MagicMock(),
        stop_event=stop,
        clock=lambda: datetime(2026, 8, 23, 0, 0, tzinfo=UTC),
        hour=8,
    )


@pytest.mark.asyncio
async def test_trigger_fetch_starts_background_task(monkeypatch):
    run_once = AsyncMock(return_value={"skipped": False, "source_count": 1})
    monkeypatch.setattr(worker, "run_once", run_once)
    engine = MagicMock()

    class _Begin:
        async def __aenter__(self):
            conn = AsyncMock()
            conn.scalar = AsyncMock(return_value=3)
            return conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    engine.begin.return_value = _Begin()
    worker._background_tasks.clear()
    result = await worker.trigger_fetch(engine, instance_id="default")
    assert result == {"triggered": True}
    tasks = list(worker._background_tasks)
    assert len(tasks) == 1
    # 任务进行中再次触发 → in_progress
    assert await worker.trigger_fetch(engine, instance_id="default") == {
        "triggered": False,
        "reason": "in_progress",
    }
    await asyncio.gather(*tasks)
    run_once.assert_awaited_once_with(engine, instance_id="default")
    assert not worker._background_tasks


@pytest.mark.asyncio
async def test_loop_runs_once_at_target_then_waits_for_next_day(monkeypatch):
    calls = 0
    timeouts: list[float] = []
    ticks = iter(
        [
            datetime(2026, 8, 23, 23, 59, 59, tzinfo=UTC),  # 北京 08-24 07:59:59，目标 08:00
            datetime(2026, 8, 23, 23, 59, 59, 999000, tzinfo=UTC),  # 醒来后墙钟仍略早于目标
        ]
    )
    stop = asyncio.Event()

    async def fake_run_once(engine, *, clock):
        nonlocal calls
        calls += 1
        return {"skipped": False}

    async def fake_wait_for(awaitable, timeout):
        timeouts.append(timeout)
        awaitable.close()
        if len(timeouts) == 1:
            raise TimeoutError  # 到点：跑一轮
        stop.set()  # 第二次等待：模拟进程退出

    monkeypatch.setattr(worker, "run_once", fake_run_once)
    monkeypatch.setattr(worker.asyncio, "wait_for", fake_wait_for)
    await worker.run_industry_news_fetch_loop(
        MagicMock(), stop_event=stop, clock=lambda: next(ticks), hour=8
    )
    assert calls == 1
    assert timeouts[0] == pytest.approx(1.0)
    # 墙钟略早于上一目标也不会同一时刻再跑一轮：下一目标是次日 08:00
    assert timeouts[1] > 86_000


@pytest.mark.asyncio
async def test_scheduled_round_is_visible_to_trigger_fetch(monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()
    seen: list[dict] = []

    async def slow_run_once(engine, *, clock):
        started.set()
        await release.wait()
        return {"skipped": False}

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        raise TimeoutError

    stop = asyncio.Event()
    monkeypatch.setattr(worker, "run_once", slow_run_once)
    monkeypatch.setattr(worker.asyncio, "wait_for", fake_wait_for)
    worker._background_tasks.clear()
    loop_task = asyncio.create_task(
        worker.run_industry_news_fetch_loop(
            MagicMock(),
            stop_event=stop,
            clock=lambda: datetime(2026, 8, 23, 23, 59, 59, tzinfo=UTC),
            hour=8,
        )
    )
    await started.wait()
    seen.append(await worker.trigger_fetch(MagicMock(), instance_id="default"))
    stop.set()
    release.set()
    await loop_task
    assert seen == [{"triggered": False, "reason": "in_progress"}]
    assert not worker._background_tasks


@pytest.mark.asyncio
async def test_trigger_fetch_reports_in_progress_when_lock_held_by_other_process(monkeypatch):
    """另一进程持有事务锁时不能谎报 triggered=True。"""
    worker._background_tasks.clear()
    monkeypatch.setattr(worker, "run_once", AsyncMock())  # 不应被调用
    engine = MagicMock()
    scalar = AsyncMock(side_effect=[3, False])  # 两次 begin 共用：有启用源；锁被占

    class _Begin:
        async def __aenter__(self):
            conn = AsyncMock()
            conn.scalar = scalar
            return conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    engine.begin.return_value = _Begin()
    result = await worker.trigger_fetch(engine, instance_id="default")
    worker.run_once.assert_not_awaited()
    assert result == {"triggered": False, "reason": "in_progress"}
    assert not worker._background_tasks


@pytest.mark.asyncio
async def test_trigger_fetch_logs_skipped_result(monkeypatch, caplog):
    run_once = AsyncMock(return_value={"skipped": True, "reason": "in_progress"})
    monkeypatch.setattr(worker, "run_once", run_once)
    engine = MagicMock()

    class _Begin:
        async def __aenter__(self):
            conn = AsyncMock()
            conn.scalar = AsyncMock(return_value=True)
            return conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    engine.begin.return_value = _Begin()
    worker._background_tasks.clear()
    with caplog.at_level("WARNING"):
        result = await worker.trigger_fetch(engine, instance_id="default")
        await asyncio.gather(*list(worker._background_tasks))
    assert result == {"triggered": True}
    assert any("立即抓取被跳过" in record.getMessage() for record in caplog.records)
