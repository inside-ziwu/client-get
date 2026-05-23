import base64
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.ai_usage_log_service import AiUsageLogService
from app.services.audit_service import AuditService
from app.services.tenant_ai_provider_service import TenantAiProviderService
from app.services.tenant_contact_utils import ensure_contacts_from_wmt
from app.utils.email_text import text_from_html
from app.utils.html_sanitizer import sanitize_html, sanitize_plain_text, sanitize_subject


class TenantMessagingService:
    def __init__(self) -> None:
        self.audit = AuditService()
        self.ai_provider = TenantAiProviderService()
        self.usage_logs = AiUsageLogService()

    def _body_text_with_fallback(self, body_text: str | None, body_html: str | None) -> str:
        if body_text and body_text.strip():
            return body_text
        return text_from_html(body_html)

    async def list_email_templates(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, category, source_type, subject, is_ai_generated, created_at, updated_at
                FROM email_templates
                WHERE tenant_id = :tenant_id AND deleted_at IS NULL
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "category": row["category"],
                "source_type": row["source_type"],
                "subject": row["subject"],
                "is_ai_generated": row["is_ai_generated"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def list_platform_templates(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        industry_result = await conn.execute(
            text("SELECT industry FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        tenant_row = industry_result.mappings().first()
        if tenant_row is None:
            raise AppError(code="NOT_FOUND", message="租户不存在", status_code=404)
        industry = tenant_row["industry"]

        result = await conn.execute(
            text(
                """
                SELECT id, name, description, category, subject, variables, created_at, updated_at
                FROM platform_email_templates
                WHERE industry = :industry AND is_active = true
                ORDER BY updated_at DESC
                """
            ),
            {"industry": industry},
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "subject": row["subject"],
                "variables": row["variables"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def copy_platform_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        template_id: str,
        user_id: str,
    ) -> dict:
        industry_result = await conn.execute(
            text("SELECT industry FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": tenant_id},
        )
        tenant_row = industry_result.mappings().first()
        if tenant_row is None:
            raise AppError(code="NOT_FOUND", message="租户不存在", status_code=404)
        industry = tenant_row["industry"]

        result = await conn.execute(
            text(
                """
                SELECT id, name, description, category, subject, body_html, body_text, variables
                FROM platform_email_templates
                WHERE id = :template_id AND is_active = true AND industry = :industry
                """
            ),
            {"template_id": template_id, "industry": industry},
        )
        platform_tpl = result.mappings().first()
        if platform_tpl is None:
            raise AppError(code="NOT_FOUND", message="平台模板不存在或不可用", status_code=404)

        return await self.create_email_template(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "name": platform_tpl["name"],
                "category": platform_tpl["category"],
                "subject": platform_tpl["subject"],
                "body_html": platform_tpl["body_html"],
                "body_text": platform_tpl["body_text"],
                "variables": platform_tpl["variables"],
                "source_type": "platform_copy",
                "platform_template_id": str(platform_tpl["id"]),
            },
        )

    async def create_email_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        content = self._sanitize_template_content(payload)
        template_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO email_templates
                  (id, tenant_id, source_type, platform_template_id, name, category, subject, body_html, body_text,
                   variables, is_ai_generated, ai_prompt)
                VALUES
                  (:id, :tenant_id, :source_type, :platform_template_id, :name, :category, :subject, :body_html, :body_text,
                   CAST(:variables AS jsonb), :is_ai_generated, :ai_prompt)
                """
            ),
            {
                "id": template_id,
                "tenant_id": tenant_id,
                "source_type": payload.get("source_type", "custom"),
                "platform_template_id": payload.get("platform_template_id"),
                "name": payload["name"],
                "category": payload.get("category", "cold_outreach"),
                "subject": content["subject"],
                "body_html": content["body_html"],
                "body_text": content["body_text"],
                "variables": self._to_json(payload.get("variables", [])),
                "is_ai_generated": payload.get("is_ai_generated", False),
                "ai_prompt": payload.get("ai_prompt"),
            },
        )
        template = await self.get_email_template(conn, tenant_id, template_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="email_template",
            entity_id=template_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value=template,
        )
        return template

    async def ai_generate_email_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        await self.ai_provider.assert_feature_available(conn, tenant_id=tenant_id)
        model = await self._get_ai_model_for_scene(conn, "email_generation")
        estimated_cost = Decimal(payload.get("estimated_cost", "1.0"))
        usage_log_id = await self.usage_logs.create_pending(
            conn,
            tenant_id=tenant_id,
            model_id=model["id"],
            usage_type="email_generation",
            estimated_cost=estimated_cost,
            idempotency_key=f"email-generate-usage:{tenant_id}:{new_uuid()}",
            user_id=user_id,
            entity_type="email_template",
        )
        provider_usage = {"input_tokens": 300, "output_tokens": 500, "total_tokens": 800}
        await self.usage_logs.complete(
            conn,
            usage_log_id=usage_log_id,
            provider_request_id=f"heuristic-email-{new_uuid()}",
            provider_response=provider_usage,
            actual_cost=estimated_cost,
            response_usage=provider_usage,
        )

        prompt = payload.get("prompt", "")
        company = payload.get("company_name", "贵司")
        category = payload.get("category", "cold_outreach")
        subject = payload.get("subject") or f"关于 {company} 的合作机会"
        body_text = (
            f"您好，我注意到 {company} 在相关领域有布局。"
            f"\n\n我们希望围绕 {prompt or '业务合作'} 与您建立联系。"
            "\n如果方便，本周可以安排一个简短沟通。"
        )
        body_html = body_text.replace("\n", "<br>")
        return await self.create_email_template(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "name": payload.get("name", f"AI 生成模板 {category}"),
                "category": category,
                "subject": subject,
                "body_html": body_html,
                "body_text": body_text,
                "variables": ["company_name", "contact_name"],
                "is_ai_generated": True,
                "ai_prompt": prompt,
                "source_type": "custom",
                "usage_log_id": usage_log_id,
            },
        )

    async def get_email_template(self, conn: AsyncConnection, tenant_id: str, template_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, name, category, source_type, platform_template_id, subject, body_html, body_text,
                       variables, is_ai_generated, ai_prompt, created_at, updated_at
                FROM email_templates
                WHERE tenant_id = :tenant_id AND id = :template_id AND deleted_at IS NULL
                """
            ),
            {"tenant_id": tenant_id, "template_id": template_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="邮件模板不存在", status_code=404)
        return self._serialize_template(row)

    async def update_email_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        template_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        before = await self.get_email_template(conn, tenant_id, template_id)
        content = self._sanitize_template_content(payload)
        await conn.execute(
            text(
                """
                UPDATE email_templates
                SET name = COALESCE(:name, name),
                    category = COALESCE(:category, category),
                    subject = COALESCE(:subject, subject),
                    body_html = COALESCE(:body_html, body_html),
                    body_text = COALESCE(:body_text, body_text),
                    variables = CAST(:variables AS jsonb),
                    ai_prompt = COALESCE(:ai_prompt, ai_prompt),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :template_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "template_id": template_id,
                "name": payload.get("name"),
                "category": payload.get("category"),
                "subject": content["subject"],
                "body_html": content["body_html"],
                "body_text": content["body_text"],
                "variables": self._to_json(payload.get("variables", before["variables"])),
                "ai_prompt": payload.get("ai_prompt"),
            },
        )
        after = await self.get_email_template(conn, tenant_id, template_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="email_template",
            entity_id=template_id,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_email_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        template_id: str,
        user_id: str,
    ) -> None:
        before = await self.get_email_template(conn, tenant_id, template_id)
        await conn.execute(
            text(
                """
                UPDATE email_templates
                SET deleted_at = now(), updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :template_id
                """
            ),
            {"tenant_id": tenant_id, "template_id": template_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="email_template",
            entity_id=template_id,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
        )

    async def clone_email_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        template_id: str,
        user_id: str,
    ) -> dict:
        template = await self.get_email_template(conn, tenant_id, template_id)
        return await self.create_email_template(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "name": f"{template['name']} 副本",
                "category": template["category"],
                "subject": template["subject"],
                "body_html": template["body_html"],
                "body_text": template["body_text"],
                "variables": template["variables"],
                "source_type": "custom",
                "is_ai_generated": template["is_ai_generated"],
                "ai_prompt": template["ai_prompt"],
            },
        )

    async def preview_email_template(self, conn: AsyncConnection, tenant_id: str, template_id: str) -> dict:
        template = await self.get_email_template(conn, tenant_id, template_id)
        return {
            "id": template["id"],
            "subject": template["subject"],
            "body_html": template["body_html"],
            "body_text": template["body_text"],
        }

    async def list_sending_plans(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        *,
        status: str | None = None,
        keyword: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[dict] | dict:
        where_clauses = ["tenant_id = :tenant_id", "deleted_at IS NULL"]
        params: dict = {"tenant_id": tenant_id}

        if status:
            where_clauses.append("status = :status")
            params["status"] = status

        if keyword:
            where_clauses.append("name ILIKE :keyword")
            params["keyword"] = f"%{keyword}%"

        if date_from:
            where_clauses.append("created_at >= :date_from")
            params["date_from"] = date_from

        if date_to:
            next_day = (date.fromisoformat(date_to) + timedelta(days=1)).isoformat()
            where_clauses.append("created_at < :date_to")
            params["date_to"] = next_day

        where_sql = " AND ".join(where_clauses)
        select_cols = """id, name, description, status, recipient_source, recipient_config, send_strategy,
                       sender_name, sender_email, domain_id, total_recipients, sent_count, scheduled_at,
                       started_at, completed_at, created_at, updated_at"""

        if page is not None and page_size is not None:
            count_result = await conn.execute(
                text(f"SELECT COUNT(*) FROM sending_plans WHERE {where_sql}"),
                params,
            )
            total = count_result.scalar_one()

            offset = (page - 1) * page_size
            data_params = {**params, "limit": page_size, "offset": offset}
            result = await conn.execute(
                text(
                    f"""
                    SELECT {select_cols}
                    FROM sending_plans
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                data_params,
            )
            items = [self._serialize_plan(row) for row in result.mappings().all()]
            return {"items": items, "total": total}

        result = await conn.execute(
            text(
                f"""
                SELECT {select_cols}
                FROM sending_plans
                WHERE {where_sql}
                ORDER BY created_at DESC
                """
            ),
            params,
        )
        return [self._serialize_plan(row) for row in result.mappings().all()]

    async def create_sending_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        plan_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO sending_plans
                  (id, tenant_id, created_by, name, description, status, recipient_source, recipient_config,
                   send_strategy, sender_name, sender_email, domain_id)
                VALUES
                  (:id, :tenant_id, :created_by, :name, :description, 'draft', :recipient_source,
                   CAST(:recipient_config AS jsonb), CAST(:send_strategy AS jsonb), :sender_name, :sender_email, :domain_id)
                """
            ),
            {
                "id": plan_id,
                "tenant_id": tenant_id,
                "created_by": user_id,
                "name": payload["name"],
                "description": payload.get("description"),
                "recipient_source": payload["recipient_source"],
                "recipient_config": self._to_json(payload.get("recipient_config", {})),
                "send_strategy": self._to_json(
                    payload.get(
                        "send_strategy",
                        {"timezone_aware": True, "preferred_hours": [9, 17], "daily_limit": 100, "interval_seconds": [30, 120]},
                    )
                ),
                "sender_name": payload.get("sender_name"),
                "sender_email": payload.get("sender_email"),
                "domain_id": payload.get("domain_id"),
            },
        )
        plan = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value=plan,
        )
        return plan

    async def create_complete_sending_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        normalized = await self._normalize_complete_plan_payload(conn, tenant_id, payload)
        plan_payload = normalized["plan"]
        steps = normalized["steps"]
        lock_recipients = normalized["lock_recipients"]
        domain = normalized["domain"]
        candidates = normalized["candidates"]

        if lock_recipients and domain["verification_status"] != "verified":
            raise AppError(code="VALIDATION_ERROR", message="发送域名未验证，不能锁定收件人", status_code=422)
        eligible_count = sum(1 for item in candidates if item["excluded_reason"] is None)
        if lock_recipients and eligible_count == 0:
            raise AppError(code="VALIDATION_ERROR", message="该分组没有可发送收件人", status_code=422)

        plan = await self.create_sending_plan(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            payload=plan_payload,
        )
        for step in steps:
            await self.create_plan_step(conn, tenant_id=tenant_id, plan_id=plan["id"], payload=step)
        if lock_recipients:
            await self.lock_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan["id"])
        return await self.get_sending_plan(conn, tenant_id, plan["id"])

    async def complete_update_sending_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        before = await self.get_sending_plan(conn, tenant_id, plan_id)
        if before["status"] != "draft":
            raise AppError(code="FORBIDDEN", message="只有草稿状态的计划可以编辑", status_code=403)

        plan_payload = payload.get("plan", {})
        steps = payload.get("steps", [])

        await self.update_sending_plan(
            conn, tenant_id=tenant_id, plan_id=plan_id, user_id=user_id, payload=plan_payload
        )

        old_steps = await self.list_plan_steps(conn, tenant_id, plan_id)
        for old_step in old_steps:
            await self.delete_plan_step(conn, tenant_id=tenant_id, plan_id=plan_id, step_id=old_step["id"])
        for step in steps:
            await self.create_plan_step(conn, tenant_id=tenant_id, plan_id=plan_id, payload=step)

        return await self.get_sending_plan(conn, tenant_id, plan_id)

    async def get_sending_plan(self, conn: AsyncConnection, tenant_id: str, plan_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, name, description, status, recipient_source, recipient_config, send_strategy,
                       sender_name, sender_email, domain_id, total_recipients, sent_count, scheduled_at,
                       started_at, completed_at, created_at, updated_at
                FROM sending_plans
                WHERE tenant_id = :tenant_id AND id = :plan_id AND deleted_at IS NULL
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="发送计划不存在", status_code=404)
        plan = self._serialize_plan(row)
        plan["steps_count"] = len(await self.list_plan_steps(conn, tenant_id, plan_id))
        return plan

    async def update_sending_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        user_id: str,
        payload: dict,
    ) -> dict:
        before = await self.get_sending_plan(conn, tenant_id, plan_id)
        if before["status"] != "draft":
            raise AppError(code="FORBIDDEN", message="只有草稿状态的计划可以编辑", status_code=403)
        await conn.execute(
            text(
                """
                UPDATE sending_plans
                SET name = COALESCE(:name, name),
                    description = COALESCE(:description, description),
                    recipient_source = COALESCE(:recipient_source, recipient_source),
                    recipient_config = CAST(:recipient_config AS jsonb),
                    send_strategy = CAST(:send_strategy AS jsonb),
                    sender_name = COALESCE(:sender_name, sender_name),
                    sender_email = COALESCE(:sender_email, sender_email),
                    domain_id = COALESCE(:domain_id, domain_id),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :plan_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "name": payload.get("name"),
                "description": payload.get("description"),
                "recipient_source": payload.get("recipient_source"),
                "recipient_config": self._to_json(payload.get("recipient_config", before["recipient_config"])),
                "send_strategy": self._to_json(payload.get("send_strategy", before["send_strategy"])),
                "sender_name": payload.get("sender_name"),
                "sender_email": payload.get("sender_email"),
                "domain_id": payload.get("domain_id"),
            },
        )
        after = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_sending_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        user_id: str,
    ) -> None:
        before = await self.get_sending_plan(conn, tenant_id, plan_id)
        if before["status"] not in ("draft", "completed", "cancelled"):
            raise AppError(code="FORBIDDEN", message="该状态下不允许删除计划", status_code=403)
        await conn.execute(
            text(
                """
                UPDATE sending_plans
                SET deleted_at = now(), updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :plan_id
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            old_value=before,
        )

    async def schedule_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        user_id: str,
        scheduled_at: str | None,
    ) -> dict:
        await self.get_sending_plan(conn, tenant_id, plan_id)
        schedule_dt = self._parse_datetime(scheduled_at) if scheduled_at else datetime.now(timezone.utc)
        await conn.execute(
            text(
                """
                UPDATE sending_plans
                SET status = 'scheduled', scheduled_at = :scheduled_at, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :plan_id
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id, "scheduled_at": schedule_dt},
        )
        plan = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"status": "scheduled", "scheduled_at": plan["scheduled_at"]},
        )
        return plan

    async def start_plan(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        user_id: str,
    ) -> dict:
        plan = await self._load_plan_row(conn, tenant_id, plan_id, for_update=True)
        if plan["status"] not in {"draft", "scheduled", "paused"}:
            raise AppError(code="VALIDATION_ERROR", message="当前状态不能启动发送计划", status_code=422)
        if not plan["domain_id"]:
            raise AppError(code="VALIDATION_ERROR", message="发送计划未绑定域名", status_code=422)
        domain = await self._load_domain(conn, tenant_id, str(plan["domain_id"]))
        if domain["verification_status"] != "verified":
            raise AppError(code="VALIDATION_ERROR", message="发送域名未验证，不能启动计划", status_code=422)

        steps = await self.list_plan_steps(conn, tenant_id, plan_id)
        if not steps:
            raise AppError(code="VALIDATION_ERROR", message="发送计划至少需要一个步骤", status_code=422)
        first_step = steps[0]
        if first_step["step_number"] != 1 or first_step["condition_type"] != "always" or first_step["delay_days"] != 0:
            raise AppError(code="VALIDATION_ERROR", message="第一步必须为 always 且 delay_days=0", status_code=422)

        locked = await self.list_plan_recipients(conn, tenant_id, plan_id)
        if not locked:
            await self.lock_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)
            locked = await self.list_plan_recipients(conn, tenant_id, plan_id)
        eligible = [item for item in locked if item["excluded_at"] is None]
        if not eligible:
            raise AppError(code="VALIDATION_ERROR", message="计划没有可发送收件人", status_code=422)

        next_due = plan["scheduled_at"] or datetime.now(timezone.utc)
        for recipient in eligible:
            await conn.execute(
                text(
                    """
                    INSERT INTO sequence_enrollments
                      (id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id, current_step, status, next_step_due_at)
                    VALUES
                      (:id, :tenant_id, :plan_id, :plan_recipient_id, :tenant_contact_id, 1, 'active', :next_step_due_at)
                    ON CONFLICT (plan_id, tenant_contact_id) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "plan_id": plan_id,
                    "plan_recipient_id": recipient["id"],
                    "tenant_contact_id": int(recipient["tenant_contact_id"]),
                    "next_step_due_at": next_due,
                },
            )
        await conn.execute(
            text(
                """
                UPDATE sending_plans
                SET status = 'running',
                    started_at = COALESCE(started_at, now()),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :plan_id
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        await conn.execute(
            text(
                """
                UPDATE tenant_companies
                SET business_status = CASE
                      WHEN business_status IN ('new','in_group') THEN 'in_plan'
                      ELSE business_status
                    END,
                    updated_at = now()
                WHERE tenant_id = :tenant_id
                  AND id IN (
                    SELECT tenant_company_id
                    FROM sending_plan_recipients
                    WHERE plan_id = :plan_id
                  )
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        started = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"status": "running"},
        )
        return started

    async def pause_plan(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str, user_id: str) -> dict:
        await self._update_plan_status(conn, tenant_id, plan_id, "paused")
        await conn.execute(
            text(
                """
                UPDATE sequence_enrollments
                SET status = 'paused', updated_at = now()
                WHERE tenant_id = :tenant_id AND plan_id = :plan_id AND status = 'active'
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        plan = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"status": "paused"},
        )
        return plan

    async def resume_plan(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str, user_id: str) -> dict:
        await self._update_plan_status(conn, tenant_id, plan_id, "running")
        await conn.execute(
            text(
                """
                UPDATE sequence_enrollments
                SET status = 'active',
                    next_step_due_at = COALESCE(next_step_due_at, now()),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND plan_id = :plan_id AND status = 'paused'
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        plan = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"status": "running"},
        )
        return plan

    async def cancel_plan(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str, user_id: str) -> dict:
        await self._update_plan_status(conn, tenant_id, plan_id, "cancelled", completed=True)
        await conn.execute(
            text(
                """
                UPDATE sequence_enrollments
                SET status = 'cancelled', completed_at = now(), updated_at = now()
                WHERE tenant_id = :tenant_id AND plan_id = :plan_id AND status IN ('active', 'paused')
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        plan = await self.get_sending_plan(conn, tenant_id, plan_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="sending_plan",
            entity_id=plan_id,
            tenant_id=tenant_id,
            user_id=user_id,
            new_value={"status": "cancelled"},
        )
        return plan

    async def preview_plan_recipients(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str) -> list[dict]:
        plan = await self._load_plan_row(conn, tenant_id, plan_id)
        candidates = await self._build_recipient_candidates(
            conn,
            tenant_id=tenant_id,
            recipient_source=plan["recipient_source"],
            recipient_config=plan["recipient_config"],
        )
        return candidates

    async def preview_recipients_for_group(self, conn: AsyncConnection, tenant_id: str, group_id: str) -> dict:
        """按群组预览收件人：按公司分组返回候选人列表和汇总统计"""
        await self._validate_recipient_config(conn, tenant_id, "group", {"group_id": group_id})
        candidates = await self._build_recipient_candidates(
            conn,
            tenant_id=tenant_id,
            recipient_source="group",
            recipient_config={"group_id": group_id},
        )
        companies_map: dict[str, dict] = {}
        for c in candidates:
            cid = c["tenant_company_id"]
            if cid not in companies_map:
                companies_map[cid] = {
                    "tenant_company_id": cid,
                    "company_name": c["company_name"],
                    "recipient_count": 0,
                    "recipients": [],
                }
            entry = {
                "contact_name": c["contact_name"],
                "contact_email": c["contact_email"],
                "level_name": c.get("level_display_name"),
                "excluded_reason": c["excluded_reason"],
            }
            companies_map[cid]["recipients"].append(entry)
            if c["excluded_reason"] is None:
                companies_map[cid]["recipient_count"] += 1

        companies = list(companies_map.values())
        total_recipients = sum(co["recipient_count"] for co in companies)
        return {
            "companies": companies,
            "summary": {
                "company_count": len(companies),
                "recipient_count": total_recipients,
            },
        }

    async def list_plan_recipients(self, conn: AsyncConnection, tenant_id: str, plan_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT pr.id, pr.tenant_company_id, pr.tenant_contact_id, pr.source_type, pr.source_ref, pr.locked_at,
                       pr.appended_after_start, pr.excluded_at, pr.excluded_reason, cc.company_name AS company_name,
                       shc.email AS contact_email, shc.name AS contact_name,
                       se.status AS enrollment_status, se.current_step AS current_step
                FROM sending_plan_recipients pr
                JOIN tenant_companies tc ON tc.id = pr.tenant_company_id
                JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
                JOIN tenant_contacts tc2 ON tc2.id = pr.tenant_contact_id
                LEFT JOIN waimaotong_clean_contacts shc ON shc.id = tc2.clean_contact_id
                LEFT JOIN sequence_enrollments se ON se.plan_id = pr.plan_id AND se.tenant_contact_id = pr.tenant_contact_id
                WHERE pr.tenant_id = :tenant_id AND pr.plan_id = :plan_id
                ORDER BY pr.locked_at ASC
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        return [
            {
                "id": str(row["id"]),
                "tenant_company_id": str(row["tenant_company_id"]),
                "tenant_contact_id": str(row["tenant_contact_id"]),
                "source_type": row["source_type"],
                "source_ref": str(row["source_ref"]) if row["source_ref"] else None,
                "locked_at": row["locked_at"].isoformat(),
                "appended_after_start": row["appended_after_start"],
                "excluded_at": row["excluded_at"].isoformat() if row["excluded_at"] else None,
                "excluded_reason": row["excluded_reason"],
                "company_name": row["company_name"],
                "contact_name": row["contact_name"],
                "contact_email": row["contact_email"],
                "enrollment_status": row["enrollment_status"],
                "current_step": row["current_step"],
            }
            for row in result.mappings().all()
        ]

    async def lock_plan_recipients(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str) -> dict:
        candidates = await self.preview_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)
        eligible = [c for c in candidates if not c["excluded_reason"] and c["tenant_contact_id"]]
        inserted = 0
        if eligible:
            result = await conn.execute(
                text(
                    """
                    INSERT INTO sending_plan_recipients
                      (id, tenant_id, plan_id, tenant_company_id, tenant_contact_id, source_type, source_ref,
                       locked_at, appended_after_start, excluded_at, excluded_reason)
                    SELECT t.id, t.tenant_id, t.plan_id, t.company_id, t.contact_id,
                           t.source_type, t.source_ref, now(), false, NULL, NULL
                    FROM unnest(
                      CAST(:ids AS uuid[]), CAST(:tenant_ids AS uuid[]), CAST(:plan_ids AS uuid[]),
                      CAST(:company_ids AS bigint[]), CAST(:contact_ids AS bigint[]),
                      CAST(:source_types AS text[]), CAST(:source_refs AS uuid[])
                    ) AS t(id, tenant_id, plan_id, company_id, contact_id, source_type, source_ref)
                    ON CONFLICT (plan_id, tenant_contact_id) DO NOTHING
                    RETURNING sending_plan_recipients.id
                    """
                ),
                {
                    "ids": [str(new_uuid()) for _ in eligible],
                    "tenant_ids": [tenant_id] * len(eligible),
                    "plan_ids": [plan_id] * len(eligible),
                    "company_ids": [int(c["tenant_company_id"]) for c in eligible],
                    "contact_ids": [int(c["tenant_contact_id"]) for c in eligible],
                    "source_types": [c["source_type"] for c in eligible],
                    "source_refs": [c["source_ref"] for c in eligible],
                },
            )
            inserted = len(result.fetchall())
        total = (
            await conn.execute(
                text("SELECT count(*) FROM sending_plan_recipients WHERE tenant_id = :tenant_id AND plan_id = :plan_id"),
                {"tenant_id": tenant_id, "plan_id": plan_id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                """
                UPDATE sending_plans
                SET total_recipients = :total_recipients, updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :plan_id
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id, "total_recipients": total},
        )
        return {"inserted_count": inserted, "total_recipients": total, "preview": candidates}

    async def append_plan_recipients(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        payload: dict,
    ) -> dict:
        plan = await self._load_plan_row(conn, tenant_id, plan_id)
        candidates = await self._build_recipient_candidates(
            conn,
            tenant_id=tenant_id,
            recipient_source=payload.get("recipient_source", plan["recipient_source"]),
            recipient_config=payload.get("recipient_config", {}),
        )
        appended = 0
        for candidate in candidates:
            if candidate["excluded_reason"]:
                continue
            await conn.execute(
                text(
                    """
                    INSERT INTO sending_plan_recipients
                      (id, tenant_id, plan_id, tenant_company_id, tenant_contact_id, source_type, source_ref,
                       locked_at, appended_after_start)
                    VALUES
                      (:id, :tenant_id, :plan_id, :tenant_company_id, :tenant_contact_id, :source_type, :source_ref,
                       now(), true)
                    ON CONFLICT (plan_id, tenant_contact_id) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "plan_id": plan_id,
                    "tenant_company_id": int(candidate["tenant_company_id"]),
                    "tenant_contact_id": int(candidate["tenant_contact_id"]),
                    "source_type": candidate["source_type"],
                    "source_ref": candidate["source_ref"],
                },
            )
            appended += 1
            if plan["status"] == "running":
                recipient_row = await conn.execute(
                    text(
                        """
                        SELECT id
                        FROM sending_plan_recipients
                        WHERE plan_id = :plan_id AND tenant_contact_id = :tenant_contact_id
                        """
                    ),
                    {"plan_id": plan_id, "tenant_contact_id": candidate["tenant_contact_id"]},
                )
                recipient = recipient_row.mappings().first()
                if recipient is not None:
                    await conn.execute(
                        text(
                            """
                            INSERT INTO sequence_enrollments
                              (id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id, current_step, status, next_step_due_at)
                            VALUES
                              (:id, :tenant_id, :plan_id, :plan_recipient_id, :tenant_contact_id, 1, 'active', now())
                            ON CONFLICT (plan_id, tenant_contact_id) DO NOTHING
                            """
                        ),
                        {
                            "id": str(new_uuid()),
                            "tenant_id": tenant_id,
                            "plan_id": plan_id,
                            "plan_recipient_id": recipient["id"],
                            "tenant_contact_id": candidate["tenant_contact_id"],
                        },
                    )
        total = (
            await conn.execute(
                text("SELECT count(*) FROM sending_plan_recipients WHERE tenant_id = :tenant_id AND plan_id = :plan_id"),
                {"tenant_id": tenant_id, "plan_id": plan_id},
            )
        ).scalar_one()
        await conn.execute(
            text("UPDATE sending_plans SET total_recipients = :total, updated_at = now() WHERE tenant_id = :tenant_id AND id = :plan_id"),
            {"tenant_id": tenant_id, "plan_id": plan_id, "total": total},
        )
        return {"appended_count": appended, "total_recipients": total}

    async def list_plan_steps(self, conn: AsyncConnection, tenant_id: str, plan_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT ss.id, ss.step_number, ss.template_id, ss.delay_days, ss.condition_type, ss.use_ai_personalization, ss.ai_instructions, ss.created_at, ss.updated_at,
                       et.name AS template_name
                FROM sequence_steps ss
                LEFT JOIN email_templates et ON et.id = ss.template_id
                WHERE ss.tenant_id = :tenant_id AND ss.plan_id = :plan_id
                ORDER BY step_number ASC
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        return [
            {
                "id": str(row["id"]),
                "step_number": row["step_number"],
                "template_id": str(row["template_id"]),
                "delay_days": row["delay_days"],
                "condition_type": row["condition_type"],
                "use_ai_personalization": row["use_ai_personalization"],
                "ai_instructions": row["ai_instructions"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "template_name": row["template_name"],
            }
            for row in result.mappings().all()
        ]

    async def create_plan_step(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        payload: dict,
    ) -> dict:
        step_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO sequence_steps
                  (id, tenant_id, plan_id, step_number, template_id, delay_days, condition_type, use_ai_personalization, ai_instructions)
                VALUES
                  (:id, :tenant_id, :plan_id, :step_number, :template_id, :delay_days, :condition_type, :use_ai_personalization, :ai_instructions)
                """
            ),
            {
                "id": step_id,
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "step_number": payload["step_number"],
                "template_id": payload["template_id"],
                "delay_days": payload.get("delay_days", 0),
                "condition_type": payload.get("condition_type", "always" if payload["step_number"] == 1 else "no_reply"),
                "use_ai_personalization": payload.get("use_ai_personalization", False),
                "ai_instructions": payload.get("ai_instructions"),
            },
        )
        return next(item for item in await self.list_plan_steps(conn, tenant_id, plan_id) if item["id"] == step_id)

    async def update_plan_step(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        plan_id: str,
        step_id: str,
        payload: dict,
    ) -> dict:
        existing = next((item for item in await self.list_plan_steps(conn, tenant_id, plan_id) if item["id"] == step_id), None)
        if existing is None:
            raise AppError(code="NOT_FOUND", message="发送步骤不存在", status_code=404)
        await conn.execute(
            text(
                """
                UPDATE sequence_steps
                SET step_number = COALESCE(:step_number, step_number),
                    template_id = COALESCE(:template_id, template_id),
                    delay_days = COALESCE(:delay_days, delay_days),
                    condition_type = COALESCE(:condition_type, condition_type),
                    use_ai_personalization = COALESCE(:use_ai_personalization, use_ai_personalization),
                    ai_instructions = COALESCE(:ai_instructions, ai_instructions),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND plan_id = :plan_id AND id = :step_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "step_id": step_id,
                "step_number": payload.get("step_number"),
                "template_id": payload.get("template_id"),
                "delay_days": payload.get("delay_days"),
                "condition_type": payload.get("condition_type"),
                "use_ai_personalization": payload.get("use_ai_personalization"),
                "ai_instructions": payload.get("ai_instructions"),
            },
        )
        return next(item for item in await self.list_plan_steps(conn, tenant_id, plan_id) if item["id"] == step_id)

    async def delete_plan_step(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str, step_id: str) -> None:
        await conn.execute(
            text("DELETE FROM sequence_steps WHERE tenant_id = :tenant_id AND plan_id = :plan_id AND id = :step_id"),
            {"tenant_id": tenant_id, "plan_id": plan_id, "step_id": step_id},
        )

    async def preview_plan(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str) -> dict:
        plan = await self.get_sending_plan(conn, tenant_id, plan_id)
        recipients = await self.preview_plan_recipients(conn, tenant_id=tenant_id, plan_id=plan_id)
        steps = await self.list_plan_steps(conn, tenant_id, plan_id)
        return {
            "plan": plan,
            "recipients_preview": recipients,
            "steps": steps,
            "eligible_recipients": sum(1 for item in recipients if item["excluded_reason"] is None),
        }

    async def sample_emails(self, conn: AsyncConnection, *, tenant_id: str, plan_id: str) -> list[dict]:
        preview = await self.preview_plan(conn, tenant_id=tenant_id, plan_id=plan_id)
        steps = preview["steps"]
        recipients = [item for item in preview["recipients_preview"] if item["excluded_reason"] is None][:3]
        if not steps or not recipients:
            return []
        first_template = await self.get_email_template(conn, tenant_id, steps[0]["template_id"])
        items = []
        for recipient in recipients:
            items.append(
                {
                    "tenant_contact_id": recipient["tenant_contact_id"],
                    "subject": sanitize_subject(self._render_text(first_template["subject"], recipient)),
                    "body_text": sanitize_plain_text(
                        self._render_text(first_template["body_text"] or "", recipient)
                    ),
                }
            )
        return items

    async def list_emails(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
        plan_id: str | None = None,
    ) -> dict:
        params = {"tenant_id": tenant_id, "limit": limit + 1}
        cursor_clause = ""
        if cursor:
            cursor_data = self._decode_email_cursor(cursor)
            params["cursor_created_at"] = cursor_data["created_at"]
            params["cursor_id"] = cursor_data["id"]
            cursor_clause = "AND (e.created_at, e.id) < (:cursor_created_at, CAST(:cursor_id AS uuid))"
        plan_clause = ""
        if plan_id:
            params["plan_id"] = plan_id
            plan_clause = "AND e.plan_id = CAST(:plan_id AS uuid)"
        result = await conn.execute(
            text(
                f"""
                SELECT e.id, e.created_at, e.plan_id, e.step_id, e.step_number, e.template_id, e.enrollment_id,
                       e.tenant_contact_id, e.from_email, e.to_email, e.subject, e.status, e.sent_at, e.opened_at,
                       e.clicked_at, e.replied_at, e.bounced_at, sp.name AS plan_name, et.name AS template_name
                FROM emails e
                LEFT JOIN sending_plans sp ON sp.id = e.plan_id
                LEFT JOIN email_templates et ON et.id = e.template_id
                WHERE e.tenant_id = :tenant_id
                  {cursor_clause}
                  {plan_clause}
                ORDER BY e.created_at DESC, e.id DESC
                LIMIT :limit
                """
            ),
            params,
        )
        rows = result.mappings().all()
        count_params: dict = {"tenant_id": tenant_id}
        count_plan_clause = ""
        if plan_id:
            count_params["plan_id"] = plan_id
            count_plan_clause = "AND plan_id = CAST(:plan_id AS uuid)"
        total_result = await conn.execute(
            text(
                f"""
                SELECT count(*)
                FROM emails
                WHERE tenant_id = :tenant_id
                  {count_plan_clause}
                """
            ),
            count_params,
        )
        total = total_result.scalar_one()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last_row = page_rows[-1]
            next_cursor = self._encode_email_cursor(
                created_at=last_row["created_at"],
                email_id=str(last_row["id"]),
            )
        return {
            "items": [self._serialize_email(row) for row in page_rows],
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total": total,
        }

    async def email_stats(self, conn: AsyncConnection, tenant_id: str) -> dict:
        """
        返回邮件统计数据，包含 D-041 投递监控 6 个指标所需字段：
          - total / sent / delivered / opened / clicked / replied / bounced / unsubscribed
          - opened_unique   — 独立打开数（基于 first_opened_at 非空）
          - soft_bounce_count   — 软退信数
          - invalid_email_count — 无效邮箱数
          - report_spam_count   — 举报垃圾邮件数
          - unsubscribed_count  — 退订数（基于 unsubscribed 布尔字段）
        """
        result = await conn.execute(
            text(
                """
                SELECT
                  count(*) AS total,
                  count(*) FILTER (WHERE status = 'sent') AS sent,
                  count(*) FILTER (WHERE status = 'delivered') AS delivered,
                  count(*) FILTER (WHERE status = 'opened') AS opened,
                  count(*) FILTER (WHERE status = 'clicked') AS clicked,
                  count(*) FILTER (WHERE status = 'replied') AS replied,
                  count(*) FILTER (WHERE status = 'bounced') AS bounced,
                  count(*) FILTER (WHERE status = 'unsubscribed') AS unsubscribed,
                  -- D-041 追踪字段统计
                  count(*) FILTER (WHERE first_opened_at IS NOT NULL) AS opened_unique,
                  count(*) FILTER (WHERE soft_bounce = true) AS soft_bounce_count,
                  count(*) FILTER (WHERE invalid_email = true) AS invalid_email_count,
                  count(*) FILTER (WHERE report_spam = true) AS report_spam_count,
                  count(*) FILTER (WHERE unsubscribed = true) AS unsubscribed_count,
                  sum(open_count) AS total_open_count
                FROM emails
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        row = result.mappings().one()
        data = dict(row)
        # 计算各项比率（分母为已发送总量）
        sent = int(data.get("sent") or 0)
        if sent > 0:
            data["delivery_rate"] = round(int(data.get("delivered") or 0) / sent, 4)
            data["open_rate"] = round(int(data.get("opened_unique") or 0) / sent, 4)
            data["soft_bounce_rate"] = round(int(data.get("soft_bounce_count") or 0) / sent, 4)
            data["report_spam_rate"] = round(int(data.get("report_spam_count") or 0) / sent, 4)
            data["unsubscribed_rate"] = round(int(data.get("unsubscribed_count") or 0) / sent, 4)
            data["bounce_rate"] = round(int(data.get("bounced") or 0) / sent, 4)
        else:
            data["delivery_rate"] = 0
            data["open_rate"] = 0
            data["soft_bounce_rate"] = 0
            data["report_spam_rate"] = 0
            data["unsubscribed_rate"] = 0
            data["bounce_rate"] = 0
        return data

    async def email_stats_by_plan(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT sp.id AS plan_id, sp.name, count(e.id) AS total,
                       count(e.id) FILTER (WHERE e.status = 'replied') AS replied,
                       count(e.id) FILTER (WHERE e.status = 'bounced') AS bounced
                FROM sending_plans sp
                LEFT JOIN emails e ON e.plan_id = sp.id
                WHERE sp.tenant_id = :tenant_id AND sp.deleted_at IS NULL
                GROUP BY sp.id
                ORDER BY sp.created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "plan_id": str(row["plan_id"]),
                "name": row["name"],
                "total": row["total"],
                "replied": row["replied"],
                "bounced": row["bounced"],
            }
            for row in result.mappings().all()
        ]

    async def email_stats_by_template(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT et.id AS template_id, et.name, count(e.id) AS total
                FROM email_templates et
                LEFT JOIN emails e ON e.template_id = et.id
                WHERE et.tenant_id = :tenant_id AND et.deleted_at IS NULL
                GROUP BY et.id
                ORDER BY et.created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [{"template_id": str(row["template_id"]), "name": row["name"], "total": row["total"]} for row in result.mappings().all()]

    async def email_stats_by_step(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT step_number, count(*) AS total
                FROM emails
                WHERE tenant_id = :tenant_id
                GROUP BY step_number
                ORDER BY step_number
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [{"step_number": row["step_number"], "total": row["total"]} for row in result.mappings().all()]

    async def email_stats_trend(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT date(created_at) AS stat_date,
                       count(*) AS total,
                       count(*) FILTER (WHERE status = 'replied') AS replied,
                       count(*) FILTER (WHERE status = 'bounced') AS bounced
                FROM emails
                WHERE tenant_id = :tenant_id
                GROUP BY date(created_at)
                ORDER BY stat_date DESC
                LIMIT 30
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "date": row["stat_date"].isoformat(),
                "total": row["total"],
                "replied": row["replied"],
                "bounced": row["bounced"],
            }
            for row in result.mappings().all()
        ]

    async def email_ai_analysis(self, conn: AsyncConnection, tenant_id: str) -> dict:
        await self.ai_provider.assert_feature_available(conn, tenant_id=tenant_id)
        stats = await self.email_stats(conn, tenant_id)
        total = stats["total"] or 0
        replied = stats["replied"] or 0
        bounced = stats["bounced"] or 0
        reply_rate = (replied / total) if total else 0
        bounce_rate = (bounced / total) if total else 0
        summary = []
        if total == 0:
            summary.append("当前还没有发送记录，无法进行 AI 分析。")
        else:
            summary.append(f"当前总发送 {total} 封，回复率 {reply_rate:.1%}，退信率 {bounce_rate:.1%}。")
            if bounce_rate > 0.05:
                summary.append("退信偏高，建议优先检查域名验证、联系人邮箱质量和发送频率。")
            if reply_rate < 0.02:
                summary.append("回复率偏低，建议优化主题行、首段价值表达与受众筛选。")
            else:
                summary.append("回复率表现尚可，建议继续放大高回复模板和目标客群。")
        return {"summary": " ".join(summary), "stats": stats}

    async def get_email(self, conn: AsyncConnection, tenant_id: str, email_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT e.*, sp.name AS plan_name, et.name AS template_name
                FROM emails e
                LEFT JOIN sending_plans sp ON sp.id = e.plan_id
                LEFT JOIN email_templates et ON et.id = e.template_id
                WHERE e.tenant_id = :tenant_id AND e.id = :email_id
                ORDER BY e.created_at DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "email_id": email_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="邮件不存在", status_code=404)
        return self._serialize_email(row, include_body=True)

    async def claim_due_emails(
        self,
        conn: AsyncConnection,
        *,
        service_instance: str,
        limit: int,
    ) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT e.id AS enrollment_id, e.plan_id, e.plan_recipient_id, e.tenant_id, e.tenant_contact_id, e.current_step,
                       e.next_step_due_at, p.domain_id, p.sender_name, p.sender_email, s.id AS step_id, s.step_number,
                       s.template_id, s.condition_type, s.delay_days,
                       pr.tenant_company_id, cc.company_name AS company_name, shc.name AS contact_name, shc.email AS to_email,
                       t.subject, t.body_html, t.body_text
                FROM sequence_enrollments e
                JOIN sending_plans p ON p.id = e.plan_id
                JOIN sequence_steps s ON s.plan_id = e.plan_id AND s.step_number = e.current_step
                JOIN sending_plan_recipients pr ON pr.id = e.plan_recipient_id
                JOIN tenant_companies tc ON tc.id = pr.tenant_company_id
                JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
                JOIN tenant_contacts tco ON tco.id = e.tenant_contact_id
                LEFT JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id
                JOIN email_templates t ON t.id = s.template_id
                WHERE e.status = 'active'
                  AND e.next_step_due_at <= now()
                  AND p.status = 'running'
                ORDER BY e.next_step_due_at ASC
                LIMIT :limit
                FOR UPDATE OF e SKIP LOCKED
                """
            ),
            {"limit": limit},
        )
        claimed = []
        for row in result.mappings().all():
            if not await self._step_condition_satisfied(conn, row):
                continue
            inserted = await conn.execute(
                text(
                    """
                    INSERT INTO email_send_locks
                      (id, tenant_id, enrollment_id, step_id, status, locked_by, locked_at)
                    VALUES
                      (:id, :tenant_id, :enrollment_id, :step_id, 'locked', :locked_by, now())
                    ON CONFLICT (enrollment_id, step_id) DO UPDATE
                    SET status = 'locked',
                        locked_by = excluded.locked_by,
                        locked_at = now(),
                        released_at = NULL,
                        email_id = NULL,
                        email_created_at = NULL
                    WHERE email_send_locks.status IN ('failed', 'released')
                    RETURNING id
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": row["tenant_id"],
                    "enrollment_id": row["enrollment_id"],
                    "step_id": row["step_id"],
                    "locked_by": service_instance,
                },
            )
            if inserted.mappings().first() is None:
                continue
            await self.reserve_domain_quota(conn, domain_id=str(row["domain_id"]), count=1)
            created_at = datetime.now(timezone.utc)
            email_id = str(new_uuid())
            body_html = self._render_text(
                row["body_html"],
                {"company_name": row["company_name"], "contact_name": row["contact_name"], "sender_name": row["sender_name"]},
            )
            body_text = self._render_text(
                row["body_text"] or "",
                {"company_name": row["company_name"], "contact_name": row["contact_name"], "sender_name": row["sender_name"]},
            )
            subject = self._render_text(
                row["subject"],
                {"company_name": row["company_name"], "contact_name": row["contact_name"], "sender_name": row["sender_name"]},
            )
            body_html = sanitize_html(body_html) or ""
            body_text = self._body_text_with_fallback(body_text, body_html)
            body_text = sanitize_plain_text(body_text)
            subject = sanitize_subject(subject) or ""
            await conn.execute(
                text(
                    """
                    INSERT INTO emails
                      (id, created_at, tenant_id, plan_id, step_id, step_number, template_id, enrollment_id,
                       tenant_contact_id, from_email, from_name, to_email, to_name, subject, body_html, body_text, status)
                    VALUES
                      (:id, :created_at, :tenant_id, :plan_id, :step_id, :step_number, :template_id, :enrollment_id,
                       :tenant_contact_id, :from_email, :from_name, :to_email, :to_name, :subject, :body_html, :body_text, 'queued')
                    """
                ),
                {
                    "id": email_id,
                    "created_at": created_at,
                    "tenant_id": row["tenant_id"],
                    "plan_id": row["plan_id"],
                    "step_id": row["step_id"],
                    "step_number": row["step_number"],
                    "template_id": row["template_id"],
                    "enrollment_id": row["enrollment_id"],
                    "tenant_contact_id": row["tenant_contact_id"],
                    "from_email": row["sender_email"],
                    "from_name": row["sender_name"],
                    "to_email": row["to_email"],
                    "to_name": row["contact_name"],
                    "subject": subject,
                    "body_html": body_html,
                    "body_text": body_text,
                },
            )
            await conn.execute(
                text(
                    """
                    UPDATE email_send_locks
                    SET email_id = :email_id, email_created_at = :email_created_at
                    WHERE enrollment_id = :enrollment_id AND step_id = :step_id
                    """
                ),
                {
                    "email_id": email_id,
                    "email_created_at": created_at,
                    "enrollment_id": row["enrollment_id"],
                    "step_id": row["step_id"],
                },
            )
            claimed.append(
                {
                    "email_id": email_id,
                    "tenant_id": str(row["tenant_id"]),
                    "plan_id": str(row["plan_id"]),
                    "step_id": str(row["step_id"]),
                    "tenant_contact_id": str(row["tenant_contact_id"]),
                    "from_email": row["sender_email"],
                    "from_name": row["sender_name"],
                    "to_email": row["to_email"],
                    "to_name": row["contact_name"],
                    "subject": subject,
                    "body_html": body_html,
                    "body_text": body_text,
                }
            )
        return {"items": claimed}

    async def mark_email_sent(
        self,
        conn: AsyncConnection,
        *,
        email_id: str,
        payload: dict,
    ) -> dict:
        email = await self._load_email(conn, email_id)
        await conn.execute(
            text(
                """
                UPDATE emails
                SET status = 'sent',
                    engagelab_message_id = COALESCE(:engagelab_message_id, engagelab_message_id),
                    sent_at = COALESCE(:sent_at, now())
                WHERE id = :email_id AND created_at = :created_at
                """
            ),
            {
                "email_id": email["id"],
                "created_at": email["created_at"],
                "engagelab_message_id": payload.get("engagelab_message_id"),
                "sent_at": self._parse_datetime(payload.get("sent_at")) if payload.get("sent_at") else None,
            },
        )
        await conn.execute(
            text(
                """
                UPDATE email_send_locks
                SET status = 'sent', released_at = now()
                WHERE email_id = :email_id
                """
            ),
            {"email_id": email_id},
        )
        await conn.execute(
            text(
                """
                UPDATE tenant_contacts
                SET contact_status = CASE
                      WHEN contact_status = 'available' THEN 'contacted'
                      ELSE contact_status
                    END,
                    updated_at = now()
                WHERE id = :tenant_contact_id
                """
            ),
            {"tenant_contact_id": email["tenant_contact_id"]},
        )
        next_step = await conn.execute(
            text(
                """
                SELECT step_number, delay_days
                FROM sequence_steps
                WHERE plan_id = :plan_id AND step_number = :next_step_number
                """
            ),
            {"plan_id": email["plan_id"], "next_step_number": email["step_number"] + 1},
        )
        next_row = next_step.mappings().first()
        if next_row is None:
            await conn.execute(
                text(
                    """
                    UPDATE sequence_enrollments
                    SET status = 'completed',
                        last_step_sent_at = now(),
                        next_step_due_at = NULL,
                        completed_at = now(),
                        updated_at = now()
                    WHERE id = :enrollment_id
                    """
                ),
                {"enrollment_id": email["enrollment_id"]},
            )
        else:
            await conn.execute(
                text(
                    """
                    UPDATE sequence_enrollments
                    SET current_step = :current_step,
                        last_step_sent_at = now(),
                        next_step_due_at = now() + make_interval(days => :delay_days),
                        updated_at = now()
                    WHERE id = :enrollment_id
                    """
                ),
                {
                    "enrollment_id": email["enrollment_id"],
                    "current_step": next_row["step_number"],
                    "delay_days": next_row["delay_days"],
                },
            )
        await conn.execute(
            text(
                """
                UPDATE sending_plans
                SET sent_count = sent_count + 1, updated_at = now()
                WHERE id = :plan_id
                """
            ),
            {"plan_id": email["plan_id"]},
        )
        return {"email_id": email_id, "status": "sent"}

    async def mark_email_failed(
        self,
        conn: AsyncConnection,
        *,
        email_id: str,
        payload: dict,
    ) -> dict:
        email = await self._load_email(conn, email_id)
        await conn.execute(
            text(
                """
                UPDATE emails
                SET status = 'failed',
                    error_code = :error_code,
                    error_message = :error_message
                WHERE id = :email_id AND created_at = :created_at
                """
            ),
            {
                "email_id": email["id"],
                "created_at": email["created_at"],
                "error_code": payload.get("error_code"),
                "error_message": payload.get("error_message"),
            },
        )
        await conn.execute(
            text(
                """
                UPDATE email_send_locks
                SET status = 'failed', released_at = now()
                WHERE email_id = :email_id
                """
            ),
            {"email_id": email_id},
        )
        await conn.execute(
            text(
                """
                UPDATE sequence_enrollments
                SET next_step_due_at = now() + interval '15 minutes',
                    updated_at = now()
                WHERE id = :enrollment_id
                """
            ),
            {"enrollment_id": email["enrollment_id"]},
        )
        return {"email_id": email_id, "status": "failed", "reason": payload.get("reason")}

    async def reserve_domain_quota(self, conn: AsyncConnection, *, domain_id: str, count: int) -> dict:
        usage = await conn.execute(
            text(
                """
                UPDATE domain_daily_usage
                SET reserved_count = reserved_count + :count,
                    updated_at = now()
                WHERE domain_id = :domain_id
                  AND usage_date = CURRENT_DATE
                  AND reserved_count + :count <= daily_limit
                RETURNING id, domain_id, usage_date, daily_limit, reserved_count, sent_count, failed_count
                """
            ),
            {"domain_id": domain_id, "count": count},
        )
        row = usage.mappings().first()
        if row is None:
            domain = await conn.execute(
                text("SELECT tenant_id, daily_limit FROM domain_warmup_status WHERE id = :domain_id"),
                {"domain_id": domain_id},
            )
            domain_row = domain.mappings().first()
            if domain_row is None:
                raise AppError(code="NOT_FOUND", message="发送域名不存在", status_code=404)
            await conn.execute(
                text(
                    """
                    INSERT INTO domain_daily_usage
                      (id, tenant_id, domain_id, usage_date, daily_limit, reserved_count, sent_count, failed_count)
                    VALUES
                      (:id, :tenant_id, :domain_id, CURRENT_DATE, :daily_limit, 0, 0, 0)
                    ON CONFLICT (domain_id, usage_date) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": domain_row["tenant_id"],
                    "domain_id": domain_id,
                    "daily_limit": domain_row["daily_limit"],
                },
            )
            usage = await conn.execute(
                text(
                    """
                    UPDATE domain_daily_usage
                    SET reserved_count = reserved_count + :count,
                        updated_at = now()
                    WHERE domain_id = :domain_id
                      AND usage_date = CURRENT_DATE
                      AND reserved_count + :count <= daily_limit
                    RETURNING id, domain_id, usage_date, daily_limit, reserved_count, sent_count, failed_count
                    """
                ),
                {"domain_id": domain_id, "count": count},
            )
            row = usage.mappings().first()
        if row is None:
            raise AppError(code="QUOTA_EXCEEDED", message="域名当日发送配额不足", status_code=409)
        return {
            "id": str(row["id"]),
            "domain_id": str(row["domain_id"]),
            "usage_date": row["usage_date"].isoformat(),
            "daily_limit": row["daily_limit"],
            "reserved_count": row["reserved_count"],
            "sent_count": row["sent_count"],
            "failed_count": row["failed_count"],
        }

    async def _build_recipient_candidates(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        recipient_source: str,
        recipient_config: dict,
    ) -> list[dict]:
        if recipient_source == "group":
            rows = await self._recipients_from_group(conn, tenant_id, recipient_config)
        elif recipient_source == "manual":
            rows = await self._recipients_from_manual(conn, tenant_id, recipient_config)
        else:
            rows = await self._recipients_from_filter(conn, tenant_id, recipient_config)
        blacklist = await self._load_blacklist(conn, tenant_id)
        candidates = []
        for row in rows:
            excluded_reason = None
            if self._is_blacklisted(row, blacklist):
                excluded_reason = "blacklisted"
            elif row["contact_status"] in {"unsubscribed", "bounced"}:
                excluded_reason = row["contact_status"]
            elif not row.get("is_sendable", True):
                excluded_reason = "not_sendable"
            elif row["data_status"] != "ready":
                excluded_reason = "incomplete"
            elif not row["contact_email"] or row["is_valid_email"] is False:
                excluded_reason = "no_email"
            candidates.append(
                {
                    "tenant_company_id": str(row["tenant_company_id"]),
                    "tenant_contact_id": str(row["tenant_contact_id"]) if row["tenant_contact_id"] else None,
                    "company_name": row["company_name"],
                    "company_domain": row["company_domain"],
                    "contact_name": row["contact_name"],
                    "contact_email": row["contact_email"],
                    "contact_status": row["contact_status"],
                    "data_status": row["data_status"],
                    "source_type": recipient_source,
                    "source_ref": str(row["source_ref"]) if row["source_ref"] else None,
                    "excluded_reason": excluded_reason,
                    "level_display_name": row.get("level_display_name"),
                }
            )
        return candidates

    async def _normalize_complete_plan_payload(self, conn: AsyncConnection, tenant_id: str, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise AppError(code="VALIDATION_ERROR", message="请求参数非法", status_code=422)
        plan = payload.get("plan")
        if not isinstance(plan, dict):
            raise AppError(code="VALIDATION_ERROR", message="缺少发送计划配置", status_code=422)
        steps = payload.get("steps")
        if not isinstance(steps, list) or not steps:
            raise AppError(code="VALIDATION_ERROR", message="发送计划至少需要一个步骤", status_code=422)

        normalized_plan = dict(plan)
        for field, message in {
            "name": "发送计划名称不能为空",
            "recipient_source": "收件人来源不能为空",
            "recipient_config": "收件人配置不能为空",
            "sender_name": "发件人名称不能为空",
            "sender_email": "发件邮箱不能为空",
            "domain_id": "发送域名不能为空",
        }.items():
            value = normalized_plan.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise AppError(code="VALIDATION_ERROR", message=message, status_code=422)

        normalized_plan["name"] = normalized_plan["name"].strip()
        normalized_plan["sender_name"] = normalized_plan["sender_name"].strip()
        normalized_plan["sender_email"] = normalized_plan["sender_email"].strip()
        if normalized_plan.get("description"):
            normalized_plan["description"] = normalized_plan["description"].strip()

        recipient_source = normalized_plan["recipient_source"]
        if recipient_source not in {"group", "manual", "filter"}:
            raise AppError(code="VALIDATION_ERROR", message="收件人来源非法", status_code=422)
        if not isinstance(normalized_plan["recipient_config"], dict):
            raise AppError(code="VALIDATION_ERROR", message="收件人配置非法", status_code=422)

        try:
            domain = await self._load_domain(conn, tenant_id, str(normalized_plan["domain_id"]))
        except AppError as exc:
            if exc.code == "NOT_FOUND":
                raise AppError(code="VALIDATION_ERROR", message="发送域名不存在或不属于当前租户", status_code=422) from exc
            raise
        await self._validate_recipient_config(conn, tenant_id, recipient_source, normalized_plan["recipient_config"])

        normalized_steps = self._normalize_complete_plan_steps(steps)
        await self._validate_step_templates(conn, tenant_id, normalized_steps)
        candidates = await self._build_recipient_candidates(
            conn,
            tenant_id=tenant_id,
            recipient_source=recipient_source,
            recipient_config=normalized_plan["recipient_config"],
        )
        return {
            "plan": normalized_plan,
            "steps": normalized_steps,
            "lock_recipients": bool(payload.get("lock_recipients", False)),
            "domain": domain,
            "candidates": candidates,
        }

    def _normalize_complete_plan_steps(self, steps: list) -> list[dict]:
        normalized = []
        seen = set()
        for raw in steps:
            if not isinstance(raw, dict):
                raise AppError(code="VALIDATION_ERROR", message="发送步骤配置非法", status_code=422)
            if raw.get("step_number") is None:
                raise AppError(code="VALIDATION_ERROR", message="发送步骤编号不能为空", status_code=422)
            step_number = int(raw["step_number"])
            if step_number in seen:
                raise AppError(code="VALIDATION_ERROR", message="发送步骤编号不能重复", status_code=422)
            seen.add(step_number)
            template_id = raw.get("template_id")
            if not template_id:
                raise AppError(code="VALIDATION_ERROR", message="发送步骤模板不能为空", status_code=422)
            normalized.append(
                {
                    "step_number": step_number,
                    "template_id": str(template_id),
                    "delay_days": int(raw.get("delay_days", 0)),
                    "condition_type": raw.get("condition_type", "always" if step_number == 1 else "no_reply"),
                    "use_ai_personalization": bool(raw.get("use_ai_personalization", False)),
                    "ai_instructions": raw.get("ai_instructions"),
                }
            )

        normalized.sort(key=lambda item: item["step_number"])
        expected = list(range(1, len(normalized) + 1))
        actual = [item["step_number"] for item in normalized]
        if actual != expected:
            raise AppError(code="VALIDATION_ERROR", message="发送步骤编号必须从 1 开始连续", status_code=422)
        first = normalized[0]
        if first["step_number"] != 1 or first["delay_days"] != 0 or first["condition_type"] != "always":
            raise AppError(code="VALIDATION_ERROR", message="第一步必须为 always 且 delay_days=0", status_code=422)
        return normalized

    async def _validate_step_templates(self, conn: AsyncConnection, tenant_id: str, steps: list[dict]) -> None:
        template_ids = {item["template_id"] for item in steps}
        result = await conn.execute(
            text(
                """
                SELECT id
                FROM email_templates
                WHERE tenant_id = :tenant_id
                  AND id = ANY(CAST(:template_ids AS uuid[]))
                  AND deleted_at IS NULL
                """
            ),
            {"tenant_id": tenant_id, "template_ids": list(template_ids)},
        )
        found = {str(row["id"]) for row in result.mappings().all()}
        if found != template_ids:
            raise AppError(code="VALIDATION_ERROR", message="发送步骤模板不存在或不属于当前租户", status_code=422)

    async def _validate_recipient_config(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        recipient_source: str,
        recipient_config: dict,
    ) -> None:
        if recipient_source != "group":
            return
        group_id = recipient_config.get("group_id")
        if not group_id:
            raise AppError(code="VALIDATION_ERROR", message="收件人分组不能为空", status_code=422)
        result = await conn.execute(
            text(
                """
                SELECT id
                FROM groups
                WHERE tenant_id = :tenant_id
                  AND id = :group_id
                  AND deleted_at IS NULL
                """
            ),
            {"tenant_id": tenant_id, "group_id": str(group_id)},
        )
        if result.mappings().first() is None:
            raise AppError(code="VALIDATION_ERROR", message="收件人分组不存在或不属于当前租户", status_code=422)

    async def _recipients_from_group(self, conn: AsyncConnection, tenant_id: str, config: dict) -> list[dict]:
        if not config.get("group_id"):
            return []
        gm_result = await conn.execute(
            text(
                """
                SELECT DISTINCT gm.tenant_company_id
                FROM group_members gm
                JOIN tenant_companies tco ON tco.id = gm.tenant_company_id
                WHERE gm.tenant_id = :tenant_id
                  AND gm.group_id = :group_id
                """
            ),
            {"tenant_id": tenant_id, "group_id": config["group_id"]},
        )
        for row in gm_result.mappings():
            await ensure_contacts_from_wmt(conn, tenant_id, int(row["tenant_company_id"]))
        result = await conn.execute(
            text(
                """
                WITH base AS (
                    SELECT gm.tenant_company_id, tc.id AS tenant_contact_id,
                           gm.group_id AS source_ref, cc.company_name, cc.website AS company_domain,
                           shc.name AS contact_name, shc.email AS contact_email,
                           tc.contact_status, tco.data_status,
                           COALESCE(pcl.is_sendable, true) AS is_sendable,
                           pcl.display_name AS level_display_name,
                           COALESCE(pcl.sort_order, -1) AS level_sort_order,
                           true AS is_valid_email
                    FROM group_members gm
                    JOIN tenant_companies tco ON tco.id = gm.tenant_company_id
                    JOIN tenant_contacts tc ON tc.tenant_id = gm.tenant_id
                      AND tc.clean_company_id = tco.clean_company_id
                    JOIN waimaotong_clean_companies cc ON cc.id = tco.clean_company_id
                    JOIN waimaotong_clean_contacts shc ON shc.id = tc.clean_contact_id
                    LEFT JOIN v_tenant_contact_classified vcc ON vcc.contact_id = shc.id
                    LEFT JOIN position_classification_levels pcl ON pcl.id = vcc.level_id
                    WHERE gm.tenant_id = :tenant_id
                      AND gm.group_id = :group_id
                      AND shc.email IS NOT NULL
                      AND tc.contact_status NOT IN ('unsubscribed', 'bounced')
                      AND tco.data_status = 'ready'
                      AND COALESCE(pcl.is_sendable, true) = true
                ),
                deduped AS (
                    SELECT DISTINCT ON (tenant_company_id, contact_email)
                           *
                    FROM base
                    ORDER BY tenant_company_id, contact_email,
                             level_sort_order DESC, tenant_contact_id ASC
                ),
                ranked AS (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY tenant_company_id
                               ORDER BY level_sort_order DESC,
                                        tenant_contact_id ASC
                           ) AS rn
                    FROM deduped
                )
                SELECT tenant_company_id, tenant_contact_id, source_ref,
                       company_name, company_domain, contact_name, contact_email,
                       contact_status, is_sendable, data_status, is_valid_email,
                       level_display_name
                FROM ranked
                WHERE rn <= 8
                ORDER BY tenant_company_id, level_sort_order DESC, tenant_contact_id ASC
                """
            ),
            {"tenant_id": tenant_id, "group_id": config["group_id"]},
        )
        return result.mappings().all()

    async def _recipients_from_manual(self, conn: AsyncConnection, tenant_id: str, config: dict) -> list[dict]:
        contact_ids = config.get("tenant_contact_ids", [])
        company_ids = config.get("tenant_company_ids", [])
        rows = []
        for contact_id in contact_ids:
            result = await conn.execute(
                text(
                    """
                    SELECT tc.id AS tenant_company_id, tco.id AS tenant_contact_id, NULL AS source_ref,
                           cc.company_name, cc.website AS company_domain, shc.name AS contact_name,
                           shc.email AS contact_email, tco.contact_status, tco.is_sendable, tc.data_status,
                           (shc.email IS NOT NULL) AS is_valid_email
                    FROM tenant_contacts tco
                    JOIN tenant_companies tc
                      ON tc.clean_company_id = tco.clean_company_id
                     AND tc.tenant_id = tco.tenant_id
                    JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
                    LEFT JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id
                    WHERE tco.tenant_id = :tenant_id
                      AND tco.id = :contact_id
                    """
                ),
                {"tenant_id": tenant_id, "contact_id": contact_id},
            )
            row = result.mappings().first()
            if row:
                rows.append(row)
        if company_ids:
            for cid in company_ids:
                await ensure_contacts_from_wmt(conn, tenant_id, int(cid))
            result = await conn.execute(
                text(
                    """
                    SELECT tc.id AS tenant_company_id, tco.id AS tenant_contact_id, NULL AS source_ref,
                           cc.company_name, cc.website AS company_domain,
                           shc.name AS contact_name, shc.email AS contact_email,
                           tco.contact_status, tco.is_sendable, tc.data_status,
                           (shc.email IS NOT NULL) AS is_valid_email
                    FROM tenant_companies tc
                    JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
                    JOIN tenant_contacts tco ON tco.clean_company_id = tc.clean_company_id
                      AND tco.tenant_id = tc.tenant_id
                    JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id
                    WHERE tc.tenant_id = :tenant_id
                      AND tc.id = ANY(:company_ids)
                      AND shc.email IS NOT NULL
                    """
                ),
                {"tenant_id": tenant_id, "company_ids": [int(cid) for cid in company_ids]},
            )
            rows.extend(result.mappings().all())
        return rows

    async def _recipients_from_filter(self, conn: AsyncConnection, tenant_id: str, config: dict) -> list[dict]:
        params = {
            "tenant_id": tenant_id,
            "business_status": config.get("business_status"),
            "country": config.get("country"),
        }
        company_result = await conn.execute(
            text(
                """
                SELECT tc.id AS tenant_company_id
                FROM tenant_companies tc
                JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
                WHERE tc.tenant_id = :tenant_id
                  AND (CAST(:business_status AS text) IS NULL OR tc.business_status = :business_status)
                  AND (CAST(:country AS text) IS NULL OR cc.country_iso3 = :country)
                """
            ),
            params,
        )
        for row in company_result:
            await ensure_contacts_from_wmt(conn, tenant_id, int(row["tenant_company_id"]))
        result = await conn.execute(
            text(
                """
                SELECT tc.id AS tenant_company_id, tco.id AS tenant_contact_id, NULL AS source_ref,
                       cc.company_name, cc.website AS company_domain,
                       shc.name AS contact_name, shc.email AS contact_email,
                       tco.contact_status, tco.is_sendable, tc.data_status,
                       (shc.email IS NOT NULL) AS is_valid_email
                FROM tenant_companies tc
                JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
                JOIN tenant_contacts tco ON tco.clean_company_id = tc.clean_company_id
                  AND tco.tenant_id = tc.tenant_id
                JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id
                WHERE tc.tenant_id = :tenant_id
                  AND shc.email IS NOT NULL
                  AND (CAST(:business_status AS text) IS NULL OR tc.business_status = :business_status)
                  AND (CAST(:country AS text) IS NULL OR cc.country_iso3 = :country)
                """
            ),
            params,
        )
        return result.mappings().all()

    async def _load_blacklist(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT shared_company_id, match_domain, match_name_pattern
                FROM company_blacklist
                WHERE tenant_id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(row) for row in result.mappings().all()]

    def _is_blacklisted(self, row, blacklist: list[dict]) -> bool:
        for item in blacklist:
            if item["shared_company_id"] and str(item["shared_company_id"]) == str(row.get("shared_company_id", "")):
                return True
            if item["match_domain"] and item["match_domain"] == row["company_domain"]:
                return True
            if item["match_name_pattern"] and item["match_name_pattern"] in row["company_name"]:
                return True
        return False

    async def _step_condition_satisfied(self, conn: AsyncConnection, row) -> bool:
        condition = row["condition_type"]
        if row["step_number"] == 1 or condition == "always":
            return True
        previous_email_result = await conn.execute(
            text(
                """
                SELECT status
                FROM emails
                WHERE enrollment_id = :enrollment_id AND step_number = :previous_step
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"enrollment_id": row["enrollment_id"], "previous_step": row["step_number"] - 1},
        )
        previous = previous_email_result.mappings().first()
        if previous is None:
            return False
        status = previous["status"]
        if condition == "no_reply":
            return status not in {"replied", "bounced", "unsubscribed"}
        if condition == "opened":
            return status in {"opened", "clicked", "replied"}
        if condition == "clicked":
            return status in {"clicked", "replied"}
        if condition == "no_open":
            return status in {"sent", "delivered"}
        return True

    async def _get_ai_model_for_scene(self, conn: AsyncConnection, scene: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT m.id, m.display_name
                FROM ai_scene_defaults s
                JOIN ai_models m ON m.id = s.model_id
                WHERE s.scene = :scene AND m.is_active = true
                """
            ),
            {"scene": scene},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="VALIDATION_ERROR", message="当前未配置可用 AI 模型", status_code=422)
        return {"id": str(row["id"]), "display_name": row["display_name"]}

    async def _update_plan_status(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        plan_id: str,
        status: str,
        *,
        completed: bool = False,
    ) -> None:
        completed_clause = ", completed_at = now()" if completed else ""
        await conn.execute(
            text(
                f"""
                UPDATE sending_plans
                SET status = :status, updated_at = now(){completed_clause}
                WHERE tenant_id = :tenant_id AND id = :plan_id
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id, "status": status},
        )

    async def _load_plan_row(
        self,
        conn: AsyncConnection,
        tenant_id: str,
        plan_id: str,
        *,
        for_update: bool = False,
    ):
        suffix = " FOR UPDATE" if for_update else ""
        result = await conn.execute(
            text(
                f"""
                SELECT *
                FROM sending_plans
                WHERE tenant_id = :tenant_id AND id = :plan_id AND deleted_at IS NULL{suffix}
                """
            ),
            {"tenant_id": tenant_id, "plan_id": plan_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="发送计划不存在", status_code=404)
        return row

    async def _load_domain(self, conn: AsyncConnection, tenant_id: str, domain_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, verification_status
                FROM domain_warmup_status
                WHERE tenant_id = :tenant_id AND id = :domain_id
                """
            ),
            {"tenant_id": tenant_id, "domain_id": domain_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="发送域名不存在", status_code=404)
        return {"id": str(row["id"]), "verification_status": row["verification_status"]}

    async def _load_email(self, conn: AsyncConnection, email_id: str):
        result = await conn.execute(
            text(
                """
                SELECT *
                FROM emails
                WHERE id = :email_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"email_id": email_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="邮件不存在", status_code=404)
        return row

    def _serialize_template(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "category": row["category"],
            "source_type": row["source_type"],
            "platform_template_id": str(row["platform_template_id"]) if row["platform_template_id"] else None,
            "subject": row["subject"],
            "body_html": row["body_html"],
            "body_text": row["body_text"],
            "variables": row["variables"],
            "is_ai_generated": row["is_ai_generated"],
            "ai_prompt": row["ai_prompt"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_plan(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"],
            "status": row["status"],
            "recipient_source": row["recipient_source"],
            "recipient_config": row["recipient_config"],
            "send_strategy": row["send_strategy"],
            "sender_name": row["sender_name"],
            "sender_email": row["sender_email"],
            "domain_id": str(row["domain_id"]) if row["domain_id"] else None,
            "total_recipients": row["total_recipients"],
            "sent_count": row["sent_count"],
            "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_email(self, row, *, include_body: bool = False) -> dict:
        data = {
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
            "plan_id": str(row["plan_id"]) if row["plan_id"] else None,
            "step_id": str(row["step_id"]) if row["step_id"] else None,
            "step_number": row["step_number"],
            "template_id": str(row["template_id"]) if row["template_id"] else None,
            "enrollment_id": str(row["enrollment_id"]) if row["enrollment_id"] else None,
            "tenant_contact_id": str(row["tenant_contact_id"]),
            "from_email": row["from_email"],
            "to_email": row["to_email"],
            "subject": row["subject"],
            "status": row["status"],
            "plan_name": row.get("plan_name"),
            "template_name": row.get("template_name"),
            "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
            "opened_at": row["opened_at"].isoformat() if row["opened_at"] else None,
            "clicked_at": row["clicked_at"].isoformat() if row["clicked_at"] else None,
            "replied_at": row["replied_at"].isoformat() if row["replied_at"] else None,
            "bounced_at": row["bounced_at"].isoformat() if row["bounced_at"] else None,
        }
        if include_body:
            data["body_html"] = row["body_html"]
            data["body_text"] = row["body_text"]
            data["reply_body_text"] = row["reply_body_text"]
            data["reply_subject"] = row["reply_subject"]
            data["reply_from_email"] = row["reply_from_email"]
        return data

    def _render_text(self, template: str, mapping: dict) -> str:
        result = template or ""
        for key, value in mapping.items():
            result = result.replace(f"{{{{{key}}}}}", str(value or ""))
        return result

    def _sanitize_template_content(self, payload: dict) -> dict:
        return {
            "subject": sanitize_subject(payload.get("subject")),
            "body_html": sanitize_html(payload.get("body_html")),
            "body_text": sanitize_plain_text(payload.get("body_text")),
        }

    def _encode_email_cursor(self, *, created_at: datetime, email_id: str) -> str:
        raw = json.dumps({"created_at": created_at.isoformat(), "id": email_id}, ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _decode_email_cursor(self, cursor: str) -> dict:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
            data = json.loads(raw)
            return {"created_at": datetime.fromisoformat(data["created_at"]), "id": data["id"]}
        except Exception as exc:  # pragma: no cover - malformed cursor
            raise AppError(code="VALIDATION_ERROR", message="cursor 非法", status_code=422) from exc

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _parse_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
