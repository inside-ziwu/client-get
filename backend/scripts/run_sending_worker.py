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
from app.workers.sending import SendingWorker


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    worker = SendingWorker()
    try:
        if args.once:
            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                idle_poll_seconds=args.idle_poll_seconds,
            )
            print(json.dumps(result, ensure_ascii=False))
            return
        while True:
            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                idle_poll_seconds=args.idle_poll_seconds,
            )
            print(json.dumps(result, ensure_ascii=False))
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ClientGet sending worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--service-instance", default="sending-worker-1")
    parser.add_argument("--idle-poll-seconds", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
