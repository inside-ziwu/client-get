"""回填历史邮件投递状态：调用 EngageLab /v1/email_status API 查询真实状态并更新数据库。

默认 dry-run，不写库。传 --execute 才会更新。
用法：
  cd backend
  python -m scripts.backfill_email_status --date 2025-05-24 --prod
  python -m scripts.backfill_email_status --date 2025-05-24 --prod --execute
"""

import argparse
import asyncio
import os
import sys
from datetime import date, datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import text

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.integrations.engagelab import EngageLabClient

STATUS_MAP = {
    1: ("delivered", False, False),
    4: ("bounced", False, True),
    5: ("bounced", True, False),
    18: (None, False, False),
}


async def run(args: argparse.Namespace) -> None:
    if args.prod:
        from dotenv import load_dotenv
        load_dotenv()
        prod_url = os.environ.get("CLIENTGET_PROD_DATABASE_URL")
        if not prod_url:
            print("错误：未找到 CLIENTGET_PROD_DATABASE_URL")
            return
        # 替换开发库 URL，复用 Settings 的 asyncpg 转换逻辑
        os.environ["CLIENTGET_DEV_DATABASE_URL"] = prod_url
        get_settings.cache_clear()
        print(">>> 连接生产库")

    settings = get_settings()
    initialize_engines(settings)
    engine = get_engine()
    client = EngageLabClient(settings=settings)

    try:
        async with engine.begin() as conn:
            # 1) 查出目标日期 status='sent' 的邮件
            rows = await conn.execute(
                text(
                    """
                    SELECT id, created_at, tenant_id, enrollment_id, tenant_contact_id,
                           to_email, engagelab_message_id, status
                    FROM emails
                    WHERE DATE(created_at AT TIME ZONE 'Asia/Shanghai') = :target_date
                      AND status = 'sent'
                      AND engagelab_message_id IS NOT NULL
                    ORDER BY created_at
                    """
                ),
                {"target_date": date.fromisoformat(args.date)},
            )
            emails = [dict(r) for r in rows.mappings().all()]
            print(f"找到 {len(emails)} 封 status='sent' 的邮件（{args.date}）")

            if not emails:
                return

            # 2) 调 EngageLab API 查询真实状态
            message_ids = [e["engagelab_message_id"] for e in emails]
            print(f"正在查询 EngageLab API（{len(message_ids)} 封）...")
            api_results = await client.query_email_status(args.date, message_ids)

            # 按 email_id 建索引
            status_by_id: dict[str, dict] = {}
            for r in api_results:
                eid = r.get("email_id")
                if eid:
                    status_by_id[eid] = r

            print(f"API 返回 {len(api_results)} 条记录，匹配 {len(status_by_id)} 封")

            # 3) 逐封更新
            stats = {"delivered": 0, "bounced_soft": 0, "bounced_invalid": 0, "sending": 0, "not_found": 0}
            now = datetime.now(timezone.utc)

            for email in emails:
                mid = email["engagelab_message_id"]
                api_row = status_by_id.get(mid)

                if not api_row:
                    stats["not_found"] += 1
                    print(f"  [未找到] {mid} -> {email['to_email']}")
                    continue

                api_status = api_row.get("status")
                new_status, is_soft_bounce, is_invalid = STATUS_MAP.get(
                    api_status, (None, False, False)
                )

                if new_status is None:
                    stats["sending"] += 1
                    print(f"  [发送中] {mid} -> {email['to_email']} (status={api_status})")
                    continue

                update_time_str = api_row.get("update_time")
                occurred_at = _parse_api_time(update_time_str) if update_time_str else now

                if new_status == "delivered":
                    stats["delivered"] += 1
                    label = "已送达"
                elif is_soft_bounce:
                    stats["bounced_soft"] += 1
                    label = "软退信"
                else:
                    stats["bounced_invalid"] += 1
                    label = "无效邮箱"

                print(f"  [{label}] {email['to_email']} (sub_status={api_row.get('sub_status')})")

                if not args.execute:
                    continue

                # 更新 emails 表
                if new_status == "delivered":
                    await conn.execute(
                        text(
                            """
                            UPDATE emails
                            SET status = 'delivered', delivered_at = :delivered_at
                            WHERE id = :id AND created_at = :created_at
                            """
                        ),
                        {"id": email["id"], "created_at": email["created_at"], "delivered_at": occurred_at},
                    )
                    # delivered 时更新 tenant_companies.business_status
                    if email["tenant_contact_id"]:
                        await conn.execute(
                            text(
                                """
                                UPDATE tenant_companies tc
                                SET business_status = 'contacted', updated_at = now()
                                FROM tenant_contacts tco
                                JOIN waimaotong_clean_contacts cc ON cc.id = tco.clean_contact_id
                                WHERE tc.tenant_id = :tenant_id
                                  AND tc.clean_company_id = tco.clean_company_id
                                  AND tc.business_status = 'in_plan'
                                  AND tco.tenant_id = :tenant_id
                                  AND (
                                    tco.id = :tenant_contact_id
                                    OR lower(cc.email::text) = lower(:to_email)
                                  )
                                """
                            ),
                            {
                                "tenant_id": email["tenant_id"],
                                "tenant_contact_id": email["tenant_contact_id"],
                                "to_email": email["to_email"],
                            },
                        )
                else:
                    bounce_field = "soft_bounce" if is_soft_bounce else "invalid_email"
                    await conn.execute(
                        text(
                            f"""
                            UPDATE emails
                            SET status = 'bounced', bounced_at = :bounced_at, {bounce_field} = true
                            WHERE id = :id AND created_at = :created_at
                            """
                        ),
                        {"id": email["id"], "created_at": email["created_at"], "bounced_at": occurred_at},
                    )
                    # bounced 时终止序列和联系人状态
                    if email["enrollment_id"]:
                        await conn.execute(
                            text(
                                """
                                UPDATE sequence_enrollments
                                SET status = 'bounced', completed_at = COALESCE(completed_at, :occurred_at), updated_at = now()
                                WHERE id = :enrollment_id
                                """
                            ),
                            {"enrollment_id": email["enrollment_id"], "occurred_at": occurred_at},
                        )
                    if email["tenant_contact_id"]:
                        await conn.execute(
                            text(
                                """
                                UPDATE tenant_contacts
                                SET contact_status = 'bounced', updated_at = now()
                                WHERE id = :tenant_contact_id
                                """
                            ),
                            {"tenant_contact_id": email["tenant_contact_id"]},
                        )

            if not args.execute:
                await conn.rollback()
                print("\n[DRY-RUN] 未写库。加 --execute 执行写入。")

            print(f"\n统计：{stats}")

    finally:
        await close_engines()


def _parse_api_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回填历史邮件投递状态")
    parser.add_argument(
        "--date",
        required=True,
        help="目标日期，格式 yyyy-mm-dd（如 2025-05-24）",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="连接生产库（CLIENTGET_PROD_DATABASE_URL）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行写库；不传只输出 dry-run",
    )
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
