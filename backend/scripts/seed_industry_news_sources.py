"""按实例导入 / 更新行业动态源种子。

用法：
  uv run python scripts/seed_industry_news_sources.py --instance default --dry-run
  uv run python scripts/seed_industry_news_sources.py --instance default
  uv run python scripts/seed_industry_news_sources.py --instance X --confirm-instance X

按 (instance_id, code) upsert：新行插入（id 由 new_uuid 生成）；已存在则更新
name / url / industry / category / lang / strategy / parse_config，不改启停与健康字段。
非 default 实例必须同时带 --confirm-instance <同值>。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.config import get_settings
from app.core.ids import new_uuid
from app.db.pools import close_engines, get_engine, initialize_engines

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "app" / "data" / "industry_news_sources_pcb.json"

_SQL_EXISTING = text(
    """
    SELECT id, name, url, industry, category, lang, strategy, parse_config
    FROM industry_news_sources
    WHERE instance_id = :instance_id AND code = :code
    """
)
_SQL_INSERT = text(
    """
    INSERT INTO industry_news_sources (
      id, instance_id, industry, code, name, url, category, lang, strategy, parse_config
    ) VALUES (
      CAST(:id AS uuid), :instance_id, :industry, :code, :name, :url, :category, :lang,
      :strategy, CAST(:parse_config AS jsonb)
    )
    """
)
_SQL_UPDATE = text(
    """
    UPDATE industry_news_sources
    SET industry = :industry,
        name = :name,
        url = :url,
        category = :category,
        lang = :lang,
        strategy = :strategy,
        parse_config = CAST(:parse_config AS jsonb)
    WHERE instance_id = :instance_id AND code = :code
    """
)


def _load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("种子文件必须是数组")
    return data


def _same(existing: dict, row: dict) -> bool:
    existing_config = existing["parse_config"]
    if isinstance(existing_config, str):
        existing_config = json.loads(existing_config)
    return (
        existing["name"] == row["name"]
        and existing["url"] == row["url"]
        and existing["industry"] == row["industry"]
        and existing["category"] == row["category"]
        and existing["lang"] == row["lang"]
        and existing["strategy"] == row["strategy"]
        and existing_config == row.get("parse_config", {})
    )


async def seed(args: argparse.Namespace) -> dict:
    if args.instance != "default" and args.confirm_instance != args.instance:
        print(
            "错误：非 default 实例必须同时带 --confirm-instance <同值>，避免误导入到共库的其他实例",
            file=sys.stderr,
        )
        raise SystemExit(2)
    rows = _load_rows(Path(args.file))
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    created = updated = unchanged = 0
    preview = []
    try:
        async with engine.begin() as conn:
            for row in rows:
                existing = (
                    (
                        await conn.execute(
                            _SQL_EXISTING,
                            {"instance_id": args.instance, "code": row["code"]},
                        )
                    )
                    .mappings()
                    .first()
                )
                payload = {
                    "id": str(new_uuid()),
                    "instance_id": args.instance,
                    "industry": row["industry"],
                    "code": row["code"],
                    "name": row["name"],
                    "url": row["url"],
                    "category": row["category"],
                    "lang": row["lang"],
                    "strategy": row["strategy"],
                    "parse_config": json.dumps(row.get("parse_config") or {}, ensure_ascii=False),
                }
                if existing is None:
                    created += 1
                    action = "created"
                    if not args.dry_run:
                        await conn.execute(_SQL_INSERT, payload)
                elif _same(dict(existing), row):
                    unchanged += 1
                    action = "unchanged"
                else:
                    updated += 1
                    action = "updated"
                    if not args.dry_run:
                        await conn.execute(_SQL_UPDATE, payload)
                preview.append(
                    {
                        "code": row["code"],
                        "name": row["name"],
                        "url": row["url"],
                        "action": action,
                    }
                )
    finally:
        await close_engines()
    return {"created": created, "updated": updated, "unchanged": unchanged, "rows": preview}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入行业动态源种子")
    parser.add_argument("--instance", required=True)
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-instance", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(seed(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
