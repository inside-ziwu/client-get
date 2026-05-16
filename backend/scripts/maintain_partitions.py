import argparse
import asyncio
import json
from datetime import date

from sqlalchemy import text

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines


def month_start(value: date) -> date:
    return value.replace(day=1)


def next_month(value: date) -> date:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)


async def ensure_partition(conn, *, prefix: str, table_name: str, partition_date: date) -> str:
    start = month_start(partition_date)
    end = next_month(start)
    partition_name = f"{prefix}_{start.strftime('%Y_%m')}"
    await conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF {table_name}
            FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}');
            """
        )
    )
    return partition_name


async def main(months_ahead: int) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    created = []
    try:
        async with engine.begin() as conn:
            cursor = month_start(date.today())
            for _ in range(months_ahead + 1):
                created.append(await ensure_partition(conn, prefix="emails_p", table_name="emails", partition_date=cursor))
                created.append(await ensure_partition(conn, prefix="audit_logs_p", table_name="audit_logs", partition_date=cursor))
                cursor = next_month(cursor)
    finally:
        await close_engines()
    print(json.dumps({"created": created}, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure monthly partitions for emails and audit logs")
    parser.add_argument("--months-ahead", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args().months_ahead))
