"""
Partition maintenance for range-partitioned tables.

Called once at app startup to ensure the current month and next month each
have a dedicated partition.  The DEFAULT partition (added in migration 0010)
acts as a permanent safety net; these monthly partitions exist purely for
query performance (partition pruning).

Tables managed:
  - audit_logs        → audit_logs_p_YYYY_MM
  - emails            → emails_p_YYYY_MM
"""

import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

_MANAGED: list[tuple[str, str]] = [
    ("audit_logs", "audit_logs_p"),
    ("emails", "emails_p"),
]


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


async def ensure_partitions(engine: AsyncEngine) -> None:
    """Create current-month and next-month partitions if they don't exist yet."""
    today = date.today()
    months = [today, _next_month(today)]

    async with engine.begin() as conn:
        for parent, prefix in _MANAGED:
            for month in months:
                start, end = _month_bounds(month)
                name = f"{prefix}_{month.strftime('%Y_%m')}"
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
                logger.debug("partition ensured: %s (%s → %s)", name, start, end)

    logger.info(
        "partition check complete — ensured %d months × %d tables",
        len(months),
        len(_MANAGED),
    )
