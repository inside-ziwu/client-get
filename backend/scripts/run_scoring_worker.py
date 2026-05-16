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
from app.workers.scoring import ScoringWorker


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    worker = ScoringWorker()
    try:
        if args.once:
            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                limit=args.limit,
                lease_seconds=args.lease_seconds,
            )
            print(json.dumps(result, ensure_ascii=False))
            return
        while True:
            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                limit=args.limit,
                lease_seconds=args.lease_seconds,
            )
            print(json.dumps(result, ensure_ascii=False))
            await asyncio.sleep(args.sleep_seconds)
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ClientGet scoring worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--service-instance", default="scoring-worker-1")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--lease-seconds", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
