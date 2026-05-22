"""回填邮件模板缺失的 body_text。

默认 dry-run，不写库。传 --execute 才会更新 platform_email_templates
与 email_templates 中 body_text 为空且 body_html 可提取文本的记录。
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
from app.services.email_template_backfill_service import backfill_email_template_body_text


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            result = await backfill_email_template_body_text(conn, dry_run=not args.execute)
            if not args.execute:
                await conn.rollback()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回填邮件模板缺失的 body_text")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行写库；不传该参数时只输出 dry-run 统计",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
