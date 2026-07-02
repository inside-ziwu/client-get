"""邮件状态对账：调用 EngageLab API 补齐因 webhook 丢失的投递状态。"""

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.integrations.engagelab import EngageLabClient

logger = logging.getLogger(__name__)

STATUS_MAP = {
    1: ("delivered", False, False),   # delivery
    4: ("bounced", False, True),      # Invalid Email
    5: ("bounced", True, False),      # Soft bounce
    18: (None, False, False),         # 发送中
}


class EmailReconciliationService:
    async def reconcile_once(
        self, conn: AsyncConnection, client: EngageLabClient
    ) -> dict:
        """查询所有 stuck 邮件的真实投递状态并更新数据库。"""
        instance_id = get_settings().instance_id
        rows = await conn.execute(
            text(
                """
                SELECT e.id, e.created_at, e.sent_at, e.tenant_id, e.enrollment_id,
                       e.tenant_contact_id, e.to_email, e.engagelab_message_id
                FROM emails e
                JOIN tenants t ON t.id = e.tenant_id
                WHERE e.status = 'sent'
                  AND e.sent_at < now() - interval '30 minutes'
                  AND e.engagelab_message_id IS NOT NULL
                  AND t.instance_id = :instance_id
                ORDER BY e.sent_at
                """
            ),
            {"instance_id": instance_id},
        )
        emails = [dict(r) for r in rows.mappings().all()]

        if not emails:
            return {"total": 0, "delivered": 0, "bounced_soft": 0, "bounced_invalid": 0, "sending": 0, "not_found": 0}

        logger.info("对账：找到 %d 封 stuck 邮件", len(emails))

        send_date_groups = self._group_by_send_date_cst(emails)

        status_by_mid: dict[str, dict] = {}
        for send_date, group_emails in send_date_groups.items():
            message_ids = [e["engagelab_message_id"] for e in group_emails]
            api_results = await client.query_email_status(send_date, message_ids)
            for r in api_results:
                eid = r.get("email_id")
                if eid:
                    status_by_mid[eid] = r

        stats = {"total": len(emails), "delivered": 0, "bounced_soft": 0, "bounced_invalid": 0, "sending": 0, "not_found": 0}

        for email in emails:
            mid = email["engagelab_message_id"]
            api_row = status_by_mid.get(mid)

            if not api_row:
                stats["not_found"] += 1
                continue

            api_status = api_row.get("status")
            new_status, is_soft_bounce, is_invalid = STATUS_MAP.get(api_status, (None, False, False))

            if new_status is None:
                stats["sending"] += 1
                continue

            update_time_str = api_row.get("update_time")
            occurred_at = _parse_api_time(update_time_str) if update_time_str else datetime.now(timezone.utc)

            if new_status == "delivered":
                stats["delivered"] += 1
                await self._apply_delivered(conn, email, occurred_at)
            else:
                if is_soft_bounce:
                    stats["bounced_soft"] += 1
                else:
                    stats["bounced_invalid"] += 1
                await self._apply_bounced(conn, email, occurred_at, is_soft_bounce)

        logger.info("对账完成：%s", stats)
        return stats

    def _group_by_send_date_cst(self, emails: list[dict]) -> dict[str, list[dict]]:
        """按 sent_at 转换为 CST 日期分组（EngageLab API 要求北京时间日期）。"""
        from zoneinfo import ZoneInfo
        cst = ZoneInfo("Asia/Shanghai")
        groups: dict[str, list[dict]] = {}
        for email in emails:
            sent_at = email["sent_at"]
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            cst_date = sent_at.astimezone(cst).strftime("%Y-%m-%d")
            groups.setdefault(cst_date, []).append(email)
        return groups

    async def _apply_delivered(self, conn: AsyncConnection, email: dict, occurred_at: datetime) -> None:
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

    async def _apply_bounced(
        self, conn: AsyncConnection, email: dict, occurred_at: datetime, is_soft_bounce: bool
    ) -> None:
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


def _parse_api_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
