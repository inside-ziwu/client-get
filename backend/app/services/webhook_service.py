"""Webhook 服务：处理 EngageLab 推送事件，回写邮件状态和 D-041 追踪字段"""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid


class WebhookService:
    async def process_engagelab_event(self, conn: AsyncConnection, payload: dict) -> dict:
        """
        处理 EngageLab webhook 事件。

        支持的事件类型映射：
          open / opened       → event_type='opened'
                                emails.first_opened_at = COALESCE(first_opened_at, now())
                                emails.open_count += 1
          bounce / bounced    → event_type='bounced'
                                emails.soft_bounce = true（当 bounce_type='soft'）
                                emails.invalid_email = true（当 bounce_type='invalid'/'hard'）
          spam / complained   → event_type='complained'
                                emails.report_spam = true
          unsubscribe / unsubscribed → event_type='unsubscribed'
                                emails.unsubscribed = true
          delivered / sent / clicked / replied → 照常处理状态字段
        """
        message_id = payload.get("message_id") or payload.get("engagelab_message_id")
        # EngageLab 状态回调用 message_status，响应回调用 event
        raw_event = (
            payload.get("event")
            or payload.get("message_status")
            or payload.get("event_type")
        )
        event_type = self._normalize_event_type(raw_event)
        # EngageLab 时间戳：itime（毫秒长整型）或 occurred_at / timestamp
        occurred_at = payload.get("occurred_at") or payload.get("timestamp") or payload.get("itime")
        occurred_at_dt = self._parse_timestamp(occurred_at)
        # EngageLab 不发 event_id，用 message_id + 事件类型 生成唯一标识
        provider_event_id = (
            payload.get("event_id")
            or payload.get("id")
            or f"{message_id}_{raw_event}_{occurred_at}"
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

        status_updates 包含：
          - status             — 新状态值
          - 时间戳字段（sent_at / delivered_at / opened_at / clicked_at / bounced_at）
          - 回信字段（reply_*）

        D-041 追踪字段（直接在此处写入）：
          - open 事件：first_opened_at（COALESCE）+ open_count（+1）
          - bounce 事件：soft_bounce / invalid_email
          - spam/complained 事件：report_spam
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
            # 首次打开时间：COALESCE（只有第一次打开时记录）
            set_parts.append("first_opened_at = COALESCE(first_opened_at, :occurred_at_open)")
            # 累计打开次数递增
            set_parts.append("open_count = open_count + 1")
            params["occurred_at_open"] = status_updates.get("opened_at") or payload.get("occurred_at_dt")

        elif event_type == "bounced":
            # EngageLab 直接用 message_status 区分：soft_bounce / invalid_email
            raw_status = (payload.get("message_status") or payload.get("bounce_type") or "").lower()
            if raw_status in {"soft_bounce", "soft", "temporary", "temp"}:
                set_parts.append("soft_bounce = true")
            else:
                # hard bounce / invalid_email 归为无效邮箱
                set_parts.append("invalid_email = true")

        elif event_type == "complained":
            # 举报垃圾邮件
            set_parts.append("report_spam = true")

        elif event_type == "unsubscribed":
            # 退订标志
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
            "sent": "sent",
            "delivered": "delivered",
            "opened": "opened",
            "open": "opened",
            "clicked": "clicked",
            "click": "clicked",
            "replied": "replied",
            "reply": "replied",
            "route": "replied",
            "bounced": "bounced",
            "bounce": "bounced",
            # EngageLab 直接用 soft_bounce / invalid_email 作为 message_status
            "soft_bounce": "bounced",
            "invalid_email": "bounced",
            # spam / complained
            "complained": "complained",
            "complaint": "complained",
            "spam": "complained",
            "report_spam": "complained",
            # unsubscribe 事件
            "unsubscribed": "unsubscribed",
            "unsubscribe": "unsubscribed",
            # target 事件（忽略，不影响状态）
            "target": "target",
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
        email=None,  # 保留参数兼容旧调用，暂不使用
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
            fields["reply_message_id"] = payload.get("reply_message_id")
            fields["reply_from_email"] = payload.get("reply_from_email")
            fields["reply_subject"] = payload.get("reply_subject")
            fields["reply_body_text"] = payload.get("reply_body_text")
            fields["reply_received_at"] = occurred_at
        return fields

    def _to_json(self, value: dict) -> str:
        import json

        return json.dumps(value, ensure_ascii=False)
