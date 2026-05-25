"""Webhook 服务：处理 EngageLab 推送事件，回写邮件状态和 D-041 追踪字段

EngageLab webhook 有两种回调格式：
  状态回调（投递类）：message_status + status_data（含 email_id）
  响应回调（行为类）：event + response_data（含 email_id）
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
        """
        处理 EngageLab webhook 事件。

        EngageLab 两种回调结构：
          状态回调：message_status="delivered" + status_data={email_id, task_id, ...}
          响应回调：event="open" + response_data={email_id, task_id, ip, ...}

        email_id 在嵌套的 status_data / response_data 中，用于匹配本地 emails.engagelab_message_id
        """
        # 提取事件类型：状态回调用 message_status，响应回调用 event
        raw_event = (
            payload.get("message_status")
            or payload.get("event")
            or payload.get("event_type")
        )
        event_type = self._normalize_event_type(raw_event)

        # 提取 email_id：优先从嵌套的 status_data / response_data 中取
        message_id = self._extract_email_id(payload)

        # 时间戳：itime（毫秒长整型）
        occurred_at = payload.get("itime") or payload.get("occurred_at") or payload.get("timestamp")
        occurred_at_dt = self._parse_timestamp(occurred_at)

        # EngageLab 不发 event_id，用 message_id + 事件类型 + 时间戳 生成唯一标识
        provider_event_id = (
            payload.get("event_id")
            or payload.get("id")
            or f"{message_id}_{raw_event}_{occurred_at}"
        )

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
        await self._apply_email_updates(conn, email, status_updates, event_type, payload)

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

    def _extract_email_id(self, payload: dict) -> str | None:
        """
        从 EngageLab webhook payload 提取 email_id。

        EngageLab 的 email_id 在嵌套结构中：
          状态回调：status_data.email_id
          响应回调：response_data.email_id
        顶层的 message_id 是 webhook 消息标识，不一定等于邮件的 email_id。
        """
        # 优先从嵌套数据中提取（EngageLab 文档标准格式）
        status_data = payload.get("status_data") or {}
        response_data = payload.get("response_data") or {}

        email_id = (
            status_data.get("email_id")
            or response_data.get("email_id")
            # target 事件的 email_ids 是数组
            or self._first_from_list(status_data.get("email_ids"))
            or self._first_from_list(response_data.get("email_ids"))
            # 兜底：顶层字段
            or payload.get("message_id")
            or payload.get("email_id")
            or payload.get("engagelab_message_id")
            or payload.get("mail_id")
        )
        return str(email_id) if email_id else None

    def _first_from_list(self, value) -> str | None:
        if isinstance(value, list) and value:
            return str(value[0])
        return None

    async def _apply_email_updates(
        self,
        conn: AsyncConnection,
        email,
        status_updates: dict,
        event_type: str,
        payload: dict,
    ) -> None:
        """
        拼装 UPDATE emails SET ... 语句。

        D-041 追踪字段：
          - open 事件：first_opened_at（COALESCE）+ open_count（+1）
          - bounce 事件：soft_bounce / invalid_email（根据原始 message_status 区分）
          - spam 事件：report_spam
          - unsubscribe 事件：unsubscribed
        """
        # 基础状态字段
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
            params["occurred_at_open"] = status_updates.get("opened_at") or payload.get("occurred_at_dt")

        elif event_type == "bounced":
            # EngageLab 直接用 message_status 区分：soft_bounce / invalid_email
            raw_status = (payload.get("message_status") or "").lower()
            if raw_status in {"soft_bounce", "soft", "temporary", "temp"}:
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
            "reply": "replied",
            "bounced": "bounced",
            "bounce": "bounced",
            "complained": "complained",
            "complaint": "complained",
            "spam": "complained",
            "unsubscribed": "unsubscribed",
        }
        return mapping.get(value.lower())

    def _parse_timestamp(self, value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            # EngageLab itime：毫秒级时间戳
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
        """计算需要更新的状态字段（不含 D-041 追踪字段）"""
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
            # route 回调的回复数据在 response_data 中
            resp = payload.get("response_data") or {}
            fields["reply_message_id"] = resp.get("email_id") or payload.get("reply_message_id")
            fields["reply_from_email"] = resp.get("from") or payload.get("reply_from_email")
            fields["reply_subject"] = resp.get("subject") or payload.get("reply_subject")
            fields["reply_body_text"] = resp.get("text") or payload.get("reply_body_text")
            fields["reply_received_at"] = occurred_at
        return fields

    def _to_json(self, value: dict) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)
