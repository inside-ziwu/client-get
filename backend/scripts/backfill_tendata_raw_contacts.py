"""Backfill Tendata raw contacts into clean_contacts.

Default mode is dry-run. Use --execute for the write path.
"""
import argparse
import asyncio
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.services.cleanup_service import CleanupService


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            result = await CleanupService().backfill_tendata_raw_contacts(
                conn,
                dry_run=not args.execute,
            )
        print(json.dumps(result, ensure_ascii=False))
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill tendata_raw_contacts into clean_contacts")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行写库；不传该参数时只输出 dry-run 统计",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
