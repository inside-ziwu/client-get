import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.ids import new_uuid
from app.security.passwords import hash_password

DEFAULT_SCORING_DIMENSIONS = [
    {
        "id": "company_type",
        "name": "工厂性质",
        "type": "rule",
        "weight": 20,
        "rules": [
            {"condition": "manufacturer", "score": 100},
            {"condition": "default", "score": 50},
        ],
    },
    {
        "id": "company_size",
        "name": "公司规模",
        "type": "rule",
        "weight": 20,
        "rules": [
            {"condition": "employee_count_gte", "value": 200, "score": 100},
            {"condition": "default", "score": 30},
        ],
    },
    {
        "id": "product_match",
        "name": "产品匹配度",
        "type": "llm",
        "weight": 20,
        "prompt_template": "根据公司资料判断与租户行业的匹配度，返回 score 和 reasoning。",
        "expected_json_schema": {"score": "number", "reasoning": "string"},
    },
]

DEFAULT_CONTACT_RULES = {
    "prefer_grade_order": ["A", "B", "C", "D"],
    "valid_email_required": True,
    "default_contact_selection": "highest_grade_then_valid_email",
}


class TenantService:
    async def list_tenants(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, slug, industry, status, needs_onboarding, created_at, updated_at
                FROM tenants
                WHERE status != 'archived'
                  AND instance_id = :instance_id
                ORDER BY created_at DESC
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        return [self._serialize_tenant(row) for row in result.mappings().all()]

    async def get_tenant(self, conn: AsyncConnection, tenant_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, name, slug, industry, status, needs_onboarding,
                       contact_name, contact_phone, contact_email, created_at, updated_at
                FROM tenants
                WHERE id = :tenant_id
                  AND instance_id = :instance_id
                """
            ),
            {"tenant_id": tenant_id, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="租户不存在", status_code=404)
        return self._serialize_tenant(row)

    async def update_tenant(self, conn: AsyncConnection, *, tenant_id: str, payload: dict) -> dict:
        await self.get_tenant(conn, tenant_id)
        await conn.execute(
            text(
                """
                UPDATE tenants
                SET name = COALESCE(:name, name),
                    industry = COALESCE(:industry, industry),
                    contact_name = COALESCE(:contact_name, contact_name),
                    contact_phone = COALESCE(:contact_phone, contact_phone),
                    contact_email = COALESCE(:contact_email, contact_email),
                    updated_at = now()
                WHERE id = :tenant_id
                  AND instance_id = :instance_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "instance_id": get_settings().instance_id,
                "name": payload.get("name"),
                "industry": payload.get("industry"),
                "contact_name": payload.get("contact_name"),
                "contact_phone": payload.get("contact_phone"),
                "contact_email": payload.get("contact_email"),
            },
        )
        return await self.get_tenant(conn, tenant_id)

    async def set_tenant_status(self, conn: AsyncConnection, *, tenant_id: str, status: str) -> dict:
        await self.get_tenant(conn, tenant_id)
        await conn.execute(
            text(
                """
                UPDATE tenants
                SET status = :status,
                    updated_at = now()
                WHERE id = :tenant_id
                  AND instance_id = :instance_id
                """
            ),
            {"tenant_id": tenant_id, "status": status, "instance_id": get_settings().instance_id},
        )
        return await self.get_tenant(conn, tenant_id)

    async def create_tenant(
        self,
        conn: AsyncConnection,
        *,
        platform_user_id: str,
        payload: dict,
    ) -> dict:
        slug = payload.get("slug")
        if not slug:
            slug = "t-" + str(new_uuid()).replace("-", "")[:8]

        existing = await conn.execute(
            text("SELECT id FROM tenants WHERE slug = :slug AND instance_id = :instance_id"),
            {"slug": slug, "instance_id": get_settings().instance_id},
        )
        if existing.first() is not None:
            raise AppError(code="CONFLICT", message="租户 slug 已存在", status_code=409)

        tenant_id = str(new_uuid())
        user_id = str(new_uuid())
        scoring_template_id = str(new_uuid())
        scoring_version_id = str(new_uuid())
        contact_rule_id = str(new_uuid())

        await conn.execute(
            text(
                """
                INSERT INTO tenants (id, name, slug, industry, contact_name, contact_phone, contact_email, status, settings, needs_onboarding, instance_id)
                VALUES (:id, :name, :slug, :industry, :contact_name, :contact_phone, :contact_email, 'active', '{}'::jsonb, true, :instance_id)
                """
            ),
            {
                "id": tenant_id,
                "name": payload["name"],
                "slug": slug,
                "industry": payload["industry"],
                "contact_name": payload.get("contact_name"),
                "contact_phone": payload.get("contact_phone"),
                "contact_email": payload["admin_email"],
                "instance_id": get_settings().instance_id,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES (:id, :tenant_id, :email, :password_hash, :name, 'active', true)
                """
            ),
            {
                "id": user_id,
                "tenant_id": tenant_id,
                "email": payload["admin_email"],
                "password_hash": hash_password(payload["admin_password"]),
                "name": payload["admin_name"],
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO user_roles (id, tenant_id, user_id, role)
                VALUES (:id, :tenant_id, :user_id, 'admin')
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": tenant_id,
                "user_id": user_id,
            },
        )

        template_copied = await self._copy_platform_scoring_template(
            conn,
            tenant_id=tenant_id,
            industry=payload["industry"],
            template_id=scoring_template_id,
            version_id=scoring_version_id,
        )
        if not template_copied:
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_templates
                      (id, tenant_id, name, is_active, dimensions, grade_thresholds, version)
                    VALUES
                      (:id, :tenant_id, :name, true, CAST(:dimensions AS jsonb),
                       CAST(:grade_thresholds AS jsonb), 1)
                    """
                ),
                {
                    "id": scoring_template_id,
                    "tenant_id": tenant_id,
                    "name": f"{payload['industry']} 默认评分模板",
                    "dimensions": self._to_json(DEFAULT_SCORING_DIMENSIONS),
                    "grade_thresholds": self._to_json({"S": 90, "A": 80, "B": 60, "C": 40, "D": 0}),
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO scoring_template_versions
                      (id, tenant_id, template_id, version, dimensions, grade_thresholds, changed_by, change_reason)
                    VALUES
                      (:id, :tenant_id, :template_id, 1, CAST(:dimensions AS jsonb),
                       CAST(:grade_thresholds AS jsonb), :changed_by, 'tenant bootstrap')
                    """
                ),
                {
                    "id": scoring_version_id,
                    "tenant_id": tenant_id,
                    "template_id": scoring_template_id,
                    "dimensions": self._to_json(DEFAULT_SCORING_DIMENSIONS),
                    "grade_thresholds": self._to_json({"S": 90, "A": 80, "B": 60, "C": 40, "D": 0}),
                    "changed_by": user_id,
                },
            )

        await self._copy_platform_email_templates(conn, tenant_id=tenant_id, industry=payload["industry"])

        await conn.execute(
            text(
                """
                INSERT INTO contact_rules (id, tenant_id, name, is_active, rules, version)
                VALUES (:id, :tenant_id, :name, true, CAST(:rules AS jsonb), 1)
                """
            ),
            {
                "id": contact_rule_id,
                "tenant_id": tenant_id,
                "name": "默认联系人规则",
                "rules": self._to_json(DEFAULT_CONTACT_RULES),
            },
        )

        # D-031：创建租户时同步初始化发件域名预热记录
        # 若 payload 带有 sender_domain，则在 domain_warmup_status 中建立初始行；
        # 档位与日发送上限以当前实例激活预热规则（warmup_rules + warmup_rule_levels）为准，
        # 档位不存在时整体报错回滚，不做静默降档
        sender_domain = (payload.get("sender_domain") or "").strip()
        warmup_level = int(payload.get("warmup_level") or 1)

        if sender_domain:
            level_result = await conn.execute(
                text(
                    """
                    SELECT wr.id AS rule_id, wrl.daily_limit
                    FROM warmup_rules wr
                    JOIN warmup_rule_levels wrl ON wrl.rule_id = wr.id
                    WHERE wr.instance_id = :instance_id
                      AND wr.is_active = true
                      AND wrl.level = :warmup_level
                    ORDER BY wr.updated_at DESC
                    LIMIT 1
                    """
                ),
                {"instance_id": get_settings().instance_id, "warmup_level": warmup_level},
            )
            level_row = level_result.mappings().first()
            if level_row is None:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message=(
                        f"预热档位 {warmup_level} 在当前实例激活预热规则中不存在，"
                        "请检查预热规则配置后重试"
                    ),
                    status_code=422,
                )
            await conn.execute(
                text(
                    """
                    INSERT INTO domain_warmup_status
                      (id, tenant_id, domain, verification_status,
                       warmup_rule_id, warmup_level, daily_limit, level_changed_at)
                    VALUES
                      (:id, :tenant_id, :domain, 'pending',
                       :warmup_rule_id, :warmup_level, :daily_limit, now())
                    ON CONFLICT (tenant_id, domain) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "domain": sender_domain,
                    "warmup_rule_id": str(level_row["rule_id"]),
                    "warmup_level": warmup_level,
                    "daily_limit": level_row["daily_limit"],
                },
            )

        return await self.get_tenant(conn, tenant_id)

    async def _copy_platform_scoring_template(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        industry: str,
        template_id: str,
        version_id: str,
    ) -> bool:
        result = await conn.execute(
            text(
                """
                SELECT id, name, dimensions, grade_thresholds, version
                FROM platform_scoring_templates
                WHERE industry = :industry AND is_active = true
                  AND instance_id = :instance_id
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"industry": industry, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            return False

        await conn.execute(
            text(
                """
                INSERT INTO scoring_templates
                  (id, tenant_id, source_platform_template_id, name, is_active, dimensions, grade_thresholds, version)
                VALUES
                  (:id, :tenant_id, :source_platform_template_id, :name, true, CAST(:dimensions AS jsonb), CAST(:grade_thresholds AS jsonb), :version)
                """
            ),
            {
                "id": template_id,
                "tenant_id": tenant_id,
                "source_platform_template_id": row["id"],
                "name": row["name"],
                "dimensions": self._to_json(row["dimensions"]),
                "grade_thresholds": self._to_json(row["grade_thresholds"]),
                "version": row["version"],
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO scoring_template_versions
                  (id, tenant_id, template_id, version, dimensions, grade_thresholds, change_reason)
                VALUES
                  (:id, :tenant_id, :template_id, :version, CAST(:dimensions AS jsonb), CAST(:grade_thresholds AS jsonb), 'copied from platform template')
                """
            ),
            {
                "id": version_id,
                "tenant_id": tenant_id,
                "template_id": template_id,
                "version": row["version"],
                "dimensions": self._to_json(row["dimensions"]),
                "grade_thresholds": self._to_json(row["grade_thresholds"]),
            },
        )
        return True

    async def _copy_platform_email_templates(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        industry: str,
    ) -> None:
        result = await conn.execute(
            text(
                """
                SELECT id, name, category, subject, body_html, body_text, variables
                FROM platform_email_templates
                WHERE industry = :industry AND is_active = true
                  AND instance_id = :instance_id
                """
            ),
            {"industry": industry, "instance_id": get_settings().instance_id},
        )
        for row in result.mappings().all():
            await conn.execute(
                text(
                    """
                    INSERT INTO email_templates
                      (id, tenant_id, source_type, platform_template_id, name, category, subject, body_html, body_text, variables)
                    VALUES
                      (:id, :tenant_id, 'platform_copy', :platform_template_id, :name, :category, :subject, :body_html, :body_text, CAST(:variables AS jsonb))
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "platform_template_id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "subject": row["subject"],
                    "body_html": row["body_html"],
                    "body_text": row["body_text"],
                    "variables": self._to_json(row["variables"]),
                },
            )

    def _serialize_tenant(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "slug": row["slug"],
            "industry": row["industry"],
            "status": row["status"],
            "needs_onboarding": row["needs_onboarding"],
            "contact_name": row.get("contact_name"),
            "contact_phone": row.get("contact_phone"),
            "contact_email": row.get("contact_email"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        }

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)
