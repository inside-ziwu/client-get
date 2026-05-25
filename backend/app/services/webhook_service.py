"""Webhook 服务：处理 EngageLab 推送事件，回写邮件状态和 D-041 追踪字段

EngageLab webhook 真实 payload 结构（根据生产日志确认）：
  状态回调：payload.status.message_status + payload.status.status_data.email_id
  响应回调：payload.event（顶层）+ payload.response_data.email_id（待确认）
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid

logger = logging.getLogger(__name__)


class WebhookService:
    async def process_engagelab_event(self, conn: AsyncConnection, payload: dict) -> dict:
        """处理 EngageLab webhook 事件（适配真实 payload 嵌套结构）"""

        # 展平嵌套结构，提取事件类型和 email_id
        raw_event = self._extract_event_type(payload)
        event_type = self._normalize_event_type(raw_event)
        message_id = self._extract_email_id(payload)

        # 时间戳：itime（毫秒长整型）
        occurred_at = payload.get("itime") or payload.get("occurred_at") or payload.get("timestamp")
        occurred_at_dt = self._parse_timestamp(occurred_at)

        # EngageLab 不发 event_id，用 message_id + 事件类型 + 时间戳 生成唯一标识
        provider_event_id = f"{message_id}_{raw_event}_{occurred_at}"

        logger.info(
            "Webhook 解析: raw_event=%s, event_type=%s, message_id=%s, itime=%s",
            raw_event, event_type, message_id, occurred_at,
        )

        if not message_id or not event_type:
            raise AppError(code="VALIDATION_ERROR", message="Webhook payload 不完整", status_code=422)

        # target 事件仅表示请求成功，不需要更新邮件状态
        if event_type == "target":
            return {"status": "ignored", "reason": "target_event"}

        # 按 engagelab_message_id 查找邮件
        email_result = await conn.execute(
            text(
                """
                SELECT id, created_at, tenant_id, enrollment_id, tenant_contact_id, to_email, status,
                       open_count, first_opened_at
                FROM emails
                WHERE engagelab_message_id = :message_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"message_id": message_id},
        )
        email = email_result.mappings().first()
        if email is None:
            logger.warning("Webhook email_not_found: message_id=%s", message_id)
            return {"status": "ignored", "reason": "email_not_found"}

        # 写入 email_events（幂等：ON CONFLICT DO NOTHING）
        inserted = await conn.execute(
            text(
                """
                INSERT INTO email_events
                  (id, tenant_id, email_id, email_created_at, event_type, metadata, source, provider_event_id, occurred_at)
                VALUES
                  (:id, :tenant_id, :email_id, :email_created_at, :event_type, CAST(:metadata AS jsonb), 'engagelab', :provider_event_id, :occurred_at)
                ON CONFLICT DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": email["tenant_id"],
                "email_id": email["id"],
                "email_created_at": email["created_at"],
                "event_type": event_type,
                "metadata": self._to_json(payload),
                "provider_event_id": provider_event_id,
                "occurred_at": occurred_at_dt,
            },
        )
        event_row = inserted.mappings().first()
        if event_row is None:
            return {"status": "duplicate", "provider_event_id": provider_event_id}

        # 更新 emails 表：状态字段 + D-041 追踪字段
        status_updates = self._status_update_fields(event_type, occurred_at_dt, payload, email)
        await self._apply_email_updates(conn, email, status_updates, event_type, raw_event)

        # 序列状态联动（回复/退信/退订时终止序列）
        if event_type in {"replied", "bounced", "unsubscribed"} and email["enrollment_id"]:
            await conn.execute(
                text(
                    """
                    UPDATE sequence_enrollments
                    SET status = :status,
                        completed_at = COALESCE(completed_at, :occurred_at),
                        updated_at = now()
                    WHERE id = :enrollment_id
                    """
                ),
                {
                    "enrollment_id": email["enrollment_id"],
                    "status": event_type,
                    "occurred_at": occurred_at_dt,
                },
            )
        # 联系人状态联动
        if event_type in {"replied", "bounced", "unsubscribed"} and email["tenant_contact_id"]:
            await conn.execute(
                text(
                    """
                    UPDATE tenant_contacts
                    SET contact_status = :status,
                        updated_at = now()
                    WHERE id = :tenant_contact_id
                    """
                ),
                {
                    "tenant_contact_id": email["tenant_contact_id"],
                    "status": event_type,
                },
            )
        if event_type == "delivered":
            await conn.execute(
                text(
                    """
                    UPDATE tenant_companies tc
                    SET business_status = 'contacted',
                        updated_at = now()
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

        return {"status": "processed", "provider_event_id": provider_event_id}

    def _extract_event_type(self, payload: dict) -> str | None:
        """
        提取原始事件类型。

        生产实际结构（状态回调）：
          payload["status"]["message_status"] = "sent" / "delivered" / ...
        响应回调（待确认）：
          payload["event"] 或 payload["response"]["event"]
        """
        # 状态回调：嵌套在 payload.status 中
        status_obj = payload.get("status")
        if isinstance(status_obj, dict):
            ms = status_obj.get("message_status")
            if ms:
                return ms

        # 响应回调：可能在 payload.response 或直接在顶层
        response_obj = payload.get("response")
        if isinstance(response_obj, dict):
            evt = response_obj.get("event")
            if evt:
                return evt

        # 兜底：顶层字段
        return (
            payload.get("event")
            or payload.get("message_status")
            or payload.get("event_type")
        )

    def _extract_email_id(self, payload: dict) -> str | None:
        """
        提取 email_id 用于匹配本地 emails.engagelab_message_id。

        生产实际结构：
          状态回调：payload["status"]["status_data"]["email_id"]
          target 事件：payload["status"]["status_data"]["email_ids"][0]
        兜底：
          payload["message_id"]（顶层）
        """
        # 状态回调：status.status_data.email_id
        status_obj = payload.get("status")
        if isinstance(status_obj, dict):
            sd = status_obj.get("status_data")
            if isinstance(sd, dict):
                eid = sd.get("email_id")
                if eid:
                    return str(eid)
                # target 事件用 email_ids 数组
                eids = sd.get("email_ids")
                if isinstance(eids, list) and eids:
                    return str(eids[0])

        # 响应回调：response.response_data.email_id 或 response_data.email_id
        response_obj = payload.get("response")
        if isinstance(response_obj, dict):
            rd = response_obj.get("response_data")
            if isinstance(rd, dict):
                eid = rd.get("email_id")
                if eid:
                    return str(eid)

        rd_top = payload.get("response_data")
        if isinstance(rd_top, dict):
            eid = rd_top.get("email_id")
            if eid:
                return str(eid)

        # 兜底：顶层 message_id
        mid = payload.get("message_id") or payload.get("email_id")
        return str(mid) if mid else None

    async def _apply_email_updates(
        self,
        conn: AsyncConnection,
        email,
        status_updates: dict,
        event_type: str,
        raw_event: str | None,
    ) -> None:
        """拼装 UPDATE emails SET ... 语句"""
        base_fields = {field: value for field, value in status_updates.items() if field != "status"}
        set_parts = ["status = :status"]
        params: dict = {
            "email_id": email["id"],
            "email_created_at": email["created_at"],
            "status": status_updates["status"],
            **base_fields,
        }

        for field in base_fields:
            set_parts.append(f"{field} = :{field}")

        # D-041 追踪字段处理
        if event_type == "opened":
            set_parts.append("first_opened_at = COALESCE(first_opened_at, :occurred_at_open)")
            set_parts.append("open_count = open_count + 1")
            params["occurred_at_open"] = status_updates.get("opened_at")

        elif event_type == "bounced":
            raw = (raw_event or "").lower()
            if raw in {"soft_bounce", "soft", "temporary", "temp"}:
                set_parts.append("soft_bounce = true")
            else:
                set_parts.append("invalid_email = true")

        elif event_type == "complained":
            set_parts.append("report_spam = true")

        elif event_type == "unsubscribed":
            set_parts.append("unsubscribed = true")

        set_clause = ", ".join(set_parts)
        await conn.execute(
            text(
                f"""
                UPDATE emails
                SET {set_clause}
                WHERE id = :email_id AND created_at = :email_created_at
                """
            ),
            params,
        )

    def _normalize_event_type(self, value: str | None) -> str | None:
        if value is None:
            return None
        mapping = {
            # 状态回调 message_status 值
            "target": "target",
            "sent": "sent",
            "delivered": "delivered",
            "soft_bounce": "bounced",
            "invalid_email": "bounced",
            # 响应回调 event 值
            "open": "opened",
            "click": "clicked",
            "unsubscribe": "unsubscribed",
            "report_spam": "complained",
            "route": "replied",
            # 兼容别名
            "opened": "opened",
            "clicked": "clicked",
            "replied": "replied",
            "bounced": "bounced",
            "complained": "complained",
            "unsubscribed": "unsubscribed",
        }
        return mapping.get(value.lower())

    def _parse_timestamp(self, value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            ts = value / 1000 if value > 1e12 else value
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        return datetime.now(timezone.utc)

    def _status_update_fields(
        self,
        event_type: str,
        occurred_at: datetime,
        payload: dict,
        email=None,
    ) -> dict:
        """计算需要更新的状态字段"""
        fields: dict = {"status": event_type}
        timestamp_field_map = {
            "sent": "sent_at",
            "delivered": "delivered_at",
            "opened": "opened_at",
            "clicked": "clicked_at",
            "replied": "replied_at",
            "bounced": "bounced_at",
        }
        if event_type in timestamp_field_map:
            fields[timestamp_field_map[event_type]] = occurred_at
        if event_type == "replied":
            response_obj = payload.get("response") or {}
            rd = response_obj.get("response_data") if isinstance(response_obj, dict) else {}
            rd = rd or payload.get("response_data") or {}
            fields["reply_message_id"] = rd.get("email_id") or payload.get("reply_message_id")
            fields["reply_from_email"] = rd.get("from") or payload.get("reply_from_email")
            fields["reply_subject"] = rd.get("subject") or payload.get("reply_subject")
            fields["reply_body_text"] = rd.get("text") or payload.get("reply_body_text")
            fields["reply_received_at"] = occurred_at
        return fields

    def _to_json(self, value: dict) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)
