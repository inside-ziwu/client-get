"""行业动态抓取循环：每天北京 08:00 一轮，不做启动补跑。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.db.pools import get_engine
from app.services.industry_news.service import IndustryNewsService
from app.utils.beijing_time import next_beijing_time

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()
_service = IndustryNewsService()


def _now() -> datetime:
    return datetime.now(UTC)


def _spawn(coro) -> asyncio.Task:
    """登记后台任务：持有引用防 GC，并让 trigger_fetch 能看见进行中的轮次。"""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def run_once(
    engine: AsyncEngine,
    *,
    instance_id: str | None = None,
    clock: Callable[[], datetime] | None = None,
    source_name: str | None = None,
    service: IndustryNewsService | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    return await (service or _service).run_once(
        engine,
        instance_id=instance_id or settings.instance_id,
        clock=clock or _now,
        source_name=source_name,
    )


async def run_industry_news_fetch_loop(
    engine: AsyncEngine,
    *,
    stop_event: asyncio.Event,
    clock: Callable[[], datetime] | None = None,
    hour: int | None = None,
) -> None:
    settings = get_settings()
    fetch_hour = settings.industry_news_fetch_hour_beijing if hour is None else hour
    target: datetime | None = None
    while not stop_event.is_set():
        now = (clock or _now)()
        # 以 max(now, 上一目标) 计算下一目标：醒来后墙钟若比目标慢几毫秒也不会同一时刻跑两轮
        target = next_beijing_time(fetch_hour, max(now, target) if target is not None else now)
        timeout = max((target - now).total_seconds(), 0)
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=timeout)
        if stop_event.is_set():
            return
        try:
            # 例行轮也登记进 _background_tasks：进行中点「立即抓取」如实返回 in_progress
            stats = await _spawn(run_once(engine, clock=clock or _now))
            logger.info(
                "industry_news_fetch: 完成 skipped=%s reason=%s sources=%s",
                stats.get("skipped"),
                stats.get("reason"),
                stats.get("source_count"),
            )
        except Exception:
            logger.exception("industry_news_fetch: 一轮失败")


async def _has_active_sources(engine: AsyncEngine, instance_id: str) -> bool:
    async with engine.begin() as conn:
        return await _service.count_active_sources(conn, instance_id) > 0


def _has_in_progress_task() -> bool:
    return any(not task.done() for task in _background_tasks)


async def _lock_is_free(engine: AsyncEngine, instance_id: str) -> bool:
    """跨进程探测：另一进程（CLI、滚动发布中的旧 Pod）持有事务锁时也要如实返回 in_progress。"""
    async with engine.begin() as conn:
        return await _service.lock_is_free(conn, instance_id)


async def trigger_fetch(engine: AsyncEngine | None = None, *, instance_id: str) -> dict[str, Any]:
    if _has_in_progress_task():
        return {"triggered": False, "reason": "in_progress"}
    engine = engine or get_engine()
    if not await _has_active_sources(engine, instance_id):
        return {"triggered": False, "reason": "no_sources"}
    if not await _lock_is_free(engine, instance_id):
        return {"triggered": False, "reason": "in_progress"}

    async def _runner() -> None:
        try:
            result = await run_once(engine, instance_id=instance_id)
        except Exception:
            logger.exception("industry_news_fetch: 立即抓取失败 instance_id=%s", instance_id)
            return
        if result.get("skipped"):
            logger.warning(
                "industry_news_fetch: 立即抓取被跳过 instance_id=%s reason=%s",
                instance_id,
                result.get("reason"),
            )
        else:
            logger.info(
                "industry_news_fetch: 立即抓取完成 instance_id=%s sources=%s ok=%s",
                instance_id,
                result.get("source_count"),
                result.get("ok_count"),
            )

    _spawn(_runner())
    return {"triggered": True}
