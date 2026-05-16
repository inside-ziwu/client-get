import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import json

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.workers.collection_scheduler import CollectionSchedulerWorker


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    worker = CollectionSchedulerWorker()
    try:
        if args.once:
            result = await worker.run_once(engine)
            print(json.dumps(result, ensure_ascii=False))
            return
        while True:
            result = await worker.run_once(engine)
            print(json.dumps(result, ensure_ascii=False))
            await asyncio.sleep(args.sleep_seconds)
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run ClientGet collection scheduler worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--sleep-seconds", type=int, default=settings.collection_scheduler_sleep_seconds)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
