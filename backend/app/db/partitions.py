"""
Partition maintenance for range-partitioned tables.

Called at app startup and then daily by a background loop, pre-creating the
current month plus the next ``_MONTHS_AHEAD`` months.  The DEFAULT partition
(added in migration 0010) acts as a permanent safety net; these monthly
partitions exist purely for query performance (partition pruning).

一旦 DEFAULT 已接住某月的行，PostgreSQL 会拒绝再建该月分区（CheckViolation）。
提前多月 + 每日预建保证正常情况下不会走到这一步；万一走到，跳过该月并告警，
数据留在 DEFAULT 照常可读写，不阻塞启动。

Tables managed:
  - audit_logs        → audit_logs_p_YYYY_MM
  - emails            → emails_p_YYYY_MM
"""

import asyncio
import logging
from contextlib import suppress
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

_MANAGED: list[tuple[str, str]] = [
    ("audit_logs", "audit_logs_p"),
    ("emails", "emails_p"),
]

_MONTHS_AHEAD = 3
_MAINTENANCE_INTERVAL_SECONDS = 24 * 60 * 60


def _month_bounds(d: date) -> tuple[str, str]:
    """Return (start, end) ISO strings for the month containing *d*."""
    start = d.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat()


def _next_month(d: date) -> date:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1)
    return d.replace(month=d.month + 1, day=1)


async def ensure_partitions(engine: AsyncEngine, *, today: date | None = None) -> None:
    """Create the current month and the next ``_MONTHS_AHEAD`` months' partitions.

    每个分区独立事务：某月因 DEFAULT 已有该月数据而建不出来时，只跳过该月。
    """
    month = (today or date.today()).replace(day=1)
    months = [month]
    for _ in range(_MONTHS_AHEAD):
        months.append(_next_month(months[-1]))

    skipped: list[str] = []
    for parent, prefix in _MANAGED:
        for month in months:
            start, end = _month_bounds(month)
            name = f"{prefix}_{month.strftime('%Y_%m')}"
            try:
                async with engine.begin() as conn:
                    # DDL does not support bind parameters — values come from
                    # date.isoformat() so interpolation is safe here.
                    await conn.execute(
                        text(
                            f"""
                            CREATE TABLE IF NOT EXISTS {name}
                            PARTITION OF {parent}
                            FOR VALUES FROM ('{start}') TO ('{end}')
                            """
                        )
                    )
            except IntegrityError:
                skipped.append(name)
                logger.warning(
                    "partition skipped: %s — %s_default already holds rows in "
                    "[%s, %s); data stays in DEFAULT, migrate manually if pruning matters",
                    name,
                    parent,
                    start,
                    end,
                )
                continue
            logger.debug("partition ensured: %s (%s → %s)", name, start, end)

    logger.info(
        "partition check complete — %d months × %d tables, skipped=%s",
        len(months),
        len(_MANAGED),
        skipped,
    )


async def run_partition_maintenance_loop(
    engine: AsyncEngine,
    *,
    stop_event: asyncio.Event,
    interval_seconds: int = _MAINTENANCE_INTERVAL_SECONDS,
) -> None:
    """后台循环：启动时已跑过一轮，此后每隔 interval 预建一次，防止常驻进程跨月漏建。"""
    while not stop_event.is_set():
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        if stop_event.is_set():
            return
        try:
            await ensure_partitions(engine)
        except Exception:
            logger.exception("partition maintenance iteration failed")
