"""run_cleanup_worker.py — 启动 cleanup_service worker。

用法：
    uv run python scripts/run_cleanup_worker.py --once
    uv run python scripts/run_cleanup_worker.py --sleep-seconds 2
"""
import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import json
import logging

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.workers.cleanup import CleanupWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()

    worker = CleanupWorker()

    try:
        if args.once:
            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                batch_size=args.batch_size,
            )
            print(json.dumps(result, ensure_ascii=False))
            return
        await worker.run_loop(
            engine,
            service_instance=args.service_instance,
            batch_size=args.batch_size,
            sleep_seconds=args.sleep_seconds,
        )
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ClientGet cleanup worker")
    parser.add_argument("--once", action="store_true", help="处理一批后退出")
    parser.add_argument("--service-instance", default="cleanup-worker-1")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
