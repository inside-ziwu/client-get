"""行业动态抓取 CLI。

两种互斥模式：
  --once              连库跑一轮（写库），可用 --source 只抓一个源
  --from-file <seed>  不连库，按种子文件直接抓取并打印（验收解析规则用，永不写库）

用法：
  uv run python scripts/run_industry_news_fetch.py --once
  uv run python scripts/run_industry_news_fetch.py --once --source "PCB Update"
  uv run python scripts/run_industry_news_fetch.py \
      --from-file app/data/industry_news_sources_pcb.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="行业动态抓取：连库跑一轮，或按种子文件不连库试抓")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="连库跑一轮后退出（写库）")
    mode.add_argument(
        "--from-file", default=None, help="不连库，按种子文件直接抓取并打印（不写库）"
    )
    parser.add_argument("--source", default=None, help="只抓指定源名称")
    return parser.parse_args(argv)


def main() -> None:
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
