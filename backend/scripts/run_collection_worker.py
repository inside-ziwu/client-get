import argparse
import asyncio
import json
import sys

# 强制 stdout/stderr 使用 UTF-8，避免容器 ASCII locale 导致 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import text

from app.core.config import get_settings
from app.core.crypto import decrypt_secret
from app.db.pools import close_engines, get_engine, initialize_engines
from app.integrations.collection.router import CollectionProviderRouter
from app.workers.collection import CollectionWorker


async def load_credentials(engine) -> dict[str, list[dict]]:
    """Load active credentials from DB, grouped by source_type.

    credentials_encrypted 存储的可能是：
    - 普通 secret 字符串（旧格式）
    - JSON 序列化的 raw_config（新格式），各 source_type 字段映射如下：
        lixiaoyun  : {"token": "...", "distinct_id": "..."}
                     → secret=token, account_no=distinct_id
        waimao_tong: {"cookie": "...", "secret_key": "...", "device_id": "..."}
                     → secret=secret_key, cookie/device_id 透传
        tendata    : {"token": "...", "userId": "...", "jsessionid": "..."}
                     → secret=token, userId/jsessionid 透传
    """
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                """
                SELECT source_type, account_no, username, credentials_encrypted, is_active
                FROM data_source_credentials
                WHERE is_active = true
                ORDER BY source_type, rotation_order ASC, created_at ASC
                """
            )
        )
        by_source: dict[str, list[dict]] = {}
        for row in result.mappings().all():
            source_type = row["source_type"]
            decrypted = decrypt_secret(row["credentials_encrypted"])

            # 尝试解析为 raw_config JSON
            raw_config: dict | None = None
            try:
                parsed = json.loads(decrypted)
                if isinstance(parsed, dict):
                    raw_config = parsed
            except (json.JSONDecodeError, TypeError):
                pass

            if raw_config is not None:
                # 按 source_type 映射字段
                if source_type == "lixiaoyun":
                    cred = {
                        "account_no": raw_config.get("distinct_id") or row["account_no"],
                        "username": row["username"],
                        "secret": raw_config.get("token", ""),
                        "is_active": row["is_active"],
                    }
                elif source_type == "waimao_tong":
                    cred = {
                        "account_no": row["account_no"],
                        "username": row["username"],
                        "secret": raw_config.get("secret_key", ""),
                        "cookie": raw_config.get("cookie", ""),
                        "secret_key": raw_config.get("secret_key", ""),
                        "device_id": raw_config.get("device_id", ""),
                        "is_active": row["is_active"],
                    }
                elif source_type == "tendata":
                    cred = {
                        "account_no": raw_config.get("userId") or row["account_no"],
                        "username": row["username"],
                        "secret": raw_config.get("token", ""),
                        "token": raw_config.get("token", ""),
                        "userId": raw_config.get("userId", ""),
                        "jsessionid": raw_config.get("jsessionid", ""),
                        "is_active": row["is_active"],
                    }
                else:
                    # 未知 source_type：原样透传整个 raw_config + is_active
                    cred = {**raw_config, "account_no": row["account_no"], "username": row["username"], "is_active": row["is_active"]}
            else:
                # 旧格式：直接字符串 secret
                cred = {
                    "account_no": row["account_no"],
                    "username": row["username"],
                    "secret": decrypted,
                    "is_active": row["is_active"],
                }

            by_source.setdefault(source_type, []).append(cred)
    return by_source


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()

    credentials_by_source = await load_credentials(engine)
    provider_router = CollectionProviderRouter(credentials_by_source=credentials_by_source)
    worker = CollectionWorker(provider_router=provider_router)

    try:
        if args.once:
            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                limit=args.limit,
                lease_seconds=args.lease_seconds,
                heartbeat_interval_seconds=args.heartbeat_interval_seconds,
            )
            print(json.dumps(result, ensure_ascii=False))
            return
        while True:
            # Reload credentials on each loop iteration so token updates take effect
            credentials_by_source = await load_credentials(engine)
            worker.provider_router = CollectionProviderRouter(credentials_by_source=credentials_by_source)

            result = await worker.run_once(
                engine,
                service_instance=args.service_instance,
                limit=args.limit,
                lease_seconds=args.lease_seconds,
                heartbeat_interval_seconds=args.heartbeat_interval_seconds,
            )
            print(json.dumps(result, ensure_ascii=False))
            await asyncio.sleep(args.sleep_seconds)
    finally:
        await close_engines()


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run ClientGet collection worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--service-instance", default="collection-worker-1")
    parser.add_argument("--limit", type=int, default=settings.collection_worker_limit)
    parser.add_argument("--lease-seconds", type=int, default=settings.collection_task_lease_seconds)
    parser.add_argument("--sleep-seconds", type=int, default=settings.collection_worker_sleep_seconds)
    parser.add_argument(
        "--heartbeat-interval-seconds",
        type=int,
        default=settings.collection_heartbeat_interval_seconds,
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
