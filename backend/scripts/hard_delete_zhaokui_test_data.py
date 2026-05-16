import argparse
import asyncio
import json

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.services.tenant_hard_delete_service import TARGET_TENANT_SLUG, TenantHardDeleteService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hard-delete approved Zhao Kui tenant test data.")
    parser.add_argument("--tenant-slug", default=TARGET_TENANT_SLUG)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute destructive cleanup. Omit for dry-run.",
    )
    parser.add_argument(
        "--confirm",
        help=f"Required with --execute. Must equal {TARGET_TENANT_SLUG}.",
    )
    parser.add_argument(
        "--confirm-company-ids",
        help=(
            "Comma-separated tenant_company_id list required when multiple exact muzi "
            "candidates are manually confirmed."
        ),
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    confirmed_company_ids = (
        [int(item.strip()) for item in args.confirm_company_ids.split(",") if item.strip()]
        if args.confirm_company_ids
        else None
    )
    settings = get_settings()
    initialize_engines(settings)
    service = TenantHardDeleteService()
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            if args.execute:
                result = await service.execute(
                    conn,
                    tenant_slug=args.tenant_slug,
                    confirm=args.confirm or "",
                    confirmed_company_ids=confirmed_company_ids,
                )
            else:
                result = await service.preview(conn, tenant_slug=args.tenant_slug)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    finally:
        await close_engines()


if __name__ == "__main__":
    asyncio.run(main())
