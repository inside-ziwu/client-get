"""行业动态抓取 CLI。

用法：
  uv run python scripts/run_industry_news_fetch.py --once
  uv run python scripts/run_industry_news_fetch.py --once --source "PCB Update"
  uv run python scripts/run_industry_news_fetch.py --from-file <seed.json> --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.services.industry_news.fetchers import IndustryNewsFetcher
from app.workers.industry_news_fetch import run_once


async def dry_run_from_file(path: Path, source_name: str | None) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if source_name:
        rows = [row for row in rows if row["name"] == source_name]
    fetcher = IndustryNewsFetcher()
    reports = []
    for row in rows:
        source = {
            "id": row.get("code"),
            "name": row["name"],
            "url": row["url"],
            "strategy": row["strategy"],
            "parse_config": row.get("parse_config") or {},
            "instance_id": "dry-run",
        }
        try:
            items = await fetcher.fetch_items(source)
            samples = []
            for item in items[:3]:
                published = item.published_at.isoformat() if item.published_at else None
                samples.append({"title": item.title, "url": item.url, "published_at": published})
            reports.append(
                {
                    "name": row["name"],
                    "code": row.get("code"),
                    "ok": True,
                    "count": len(items),
                    "samples": samples,
                }
            )
        except Exception as exc:
            reports.append(
                {
                    "name": row["name"],
                    "code": row.get("code"),
                    "ok": False,
                    "count": 0,
                    "error": str(exc),
                    "samples": [],
                }
            )
    return reports


async def run(args: argparse.Namespace) -> None:
    if args.from_file:
        reports = await dry_run_from_file(Path(args.from_file), args.source)
        print(json.dumps(reports, ensure_ascii=False, indent=2, default=str))
        return
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    try:
        result = await run_once(engine, source_name=args.source)
        print(json.dumps(result, ensure_ascii=False, default=str))
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run industry news fetch")
    parser.add_argument("--once", action="store_true", help="跑一轮后退出（连库）")
    parser.add_argument("--source", default=None, help="只抓指定源名称")
    parser.add_argument(
        "--dry-run", action="store_true", help="只与 --from-file 搭配：不连库、只打印"
    )
    parser.add_argument("--from-file", default=None, help="不连库，直接按种子文件抓取")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.from_file:
        if not args.dry_run:
            print("--from-file 必须搭配 --dry-run（不写库）", file=sys.stderr)
            raise SystemExit(2)
        asyncio.run(run(args))
        return
    if not args.once:
        print("连库模式请加 --once", file=sys.stderr)
        raise SystemExit(2)
    if args.dry_run:
        print(
            "--dry-run 只支持 --from-file（连库 --once 会写库，无 dry-run 模式）", file=sys.stderr
        )
        raise SystemExit(2)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
