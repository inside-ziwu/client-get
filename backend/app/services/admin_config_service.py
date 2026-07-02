import json
import logging
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.errors import AppError
from app.core.ids import new_uuid
from app.security.passwords import hash_password
from app.services.audit_service import AuditService
from app.services.scoring_engine_service import ScoringEngineService
from app.utils.html_sanitizer import sanitize_html, sanitize_plain_text, sanitize_subject

_scoring_engine = ScoringEngineService()
_logger = logging.getLogger(__name__)


class AdminConfigService:
    def __init__(self) -> None:
        self.audit = AuditService()

    async def list_data_sources(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT ds.id, ds.source_type, ds.name, ds.alias_code, ds.purpose, ds.is_active, ds.config,
                       ds.landing_rules,
                       count(dsc.id) FILTER (WHERE dsc.is_active) AS active_credentials_count
                FROM data_sources ds
                LEFT JOIN data_source_credentials dsc ON dsc.source_type = ds.source_type AND dsc.instance_id = ds.instance_id
                WHERE ds.instance_id = :instance_id
                GROUP BY ds.id
                ORDER BY ds.source_type
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        return [self._serialize_data_source(row) for row in result.mappings().all()]

    async def create_data_source(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        source_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO data_sources
                  (id, source_type, name, alias_code, purpose, is_active, config, landing_rules, instance_id)
                VALUES
                  (:id, :source_type, :name, :alias_code, :purpose, :is_active,
                   CAST(:config AS jsonb), CAST(:landing_rules AS jsonb), :instance_id)
                """
            ),
            {
                "id": source_id,
                "source_type": payload["source_type"],
                "name": payload["name"],
                "alias_code": payload.get("alias_code", payload["source_type"]),
                "purpose": payload.get("purpose"),
                "is_active": payload.get("is_active", True),
                "config": self._to_json(payload.get("config", {})),
                "landing_rules": self._to_json(payload.get("landing_rules", {})),
                "instance_id": get_settings().instance_id,
            },
        )
        row = await self.get_data_source(conn, payload["source_type"])
        await self.audit.write(
            conn,
            action="create",
            entity_type="data_source",
            entity_id=source_id,
            platform_user_id=platform_user_id,
            new_value=row,
        )
        return row

    async def get_data_source(self, conn: AsyncConnection, source_type: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT ds.id, ds.source_type, ds.name, ds.alias_code, ds.purpose, ds.is_active, ds.config,
                       ds.landing_rules,
                       count(dsc.id) FILTER (WHERE dsc.is_active) AS active_credentials_count
                FROM data_sources ds
                LEFT JOIN data_source_credentials dsc ON dsc.source_type = ds.source_type AND dsc.instance_id = ds.instance_id
                WHERE ds.source_type = :source_type AND ds.instance_id = :instance_id
                GROUP BY ds.id
                """
            ),
            {"source_type": source_type, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="数据源不存在", status_code=404)
        return self._serialize_data_source(row)

    async def patch_data_source(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_data_source(conn, source_type)
        await conn.execute(
            text(
                """
                UPDATE data_sources
                SET name = COALESCE(:name, name),
                    alias_code = COALESCE(:alias_code, alias_code),
                    purpose = COALESCE(:purpose, purpose),
                    is_active = COALESCE(:is_active, is_active),
                    updated_at = now()
                WHERE source_type = :source_type AND instance_id = :instance_id
                """
            ),
            {
                "source_type": source_type,
                "name": payload.get("name"),
                "alias_code": payload.get("alias_code"),
                "purpose": payload.get("purpose"),
                "is_active": payload.get("is_active"),
                "instance_id": get_settings().instance_id,
            },
        )
        after = await self.get_data_source(conn, source_type)
        await self.audit.write(
            conn,
            action="update",
            entity_type="data_source",
            entity_id=after["id"],
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def patch_data_source_config(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        row = await self.get_data_source(conn, source_type)
        next_config = payload.get("config", row["config"])
        next_landing_rules = payload.get("landing_rules", row["landing_rules"])
        await conn.execute(
            text(
                """
                UPDATE data_sources
                SET config = CAST(:config AS jsonb),
                    landing_rules = CAST(:landing_rules AS jsonb),
                    updated_at = now()
                WHERE source_type = :source_type AND instance_id = :instance_id
                """
            ),
            {
                "source_type": source_type,
                "config": self._to_json(next_config),
                "landing_rules": self._to_json(next_landing_rules),
                "instance_id": get_settings().instance_id,
            },
        )
        after = await self.get_data_source(conn, source_type)
        await self.audit.write(
            conn,
            action="update",
            entity_type="data_source_config",
            entity_id=after["id"],
            platform_user_id=platform_user_id,
            old_value=row,
            new_value=after,
        )
        return after

    async def list_data_source_credentials(self, conn: AsyncConnection, source_type: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, source_type, account_no, username, credentials_encrypted, encryption_key_version,
                       rotation_order, daily_quota, current_day_used, current_day_reset_at, is_active,
                       last_used_at, last_error_at, last_error_message, consecutive_error_count, created_at
                FROM data_source_credentials
                WHERE source_type = :source_type AND instance_id = :instance_id
                ORDER BY rotation_order ASC, created_at ASC
                """
            ),
            {"source_type": source_type, "instance_id": get_settings().instance_id},
        )
        return [self._serialize_credential(row) for row in result.mappings().all()]

    async def create_data_source_credential(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        credential_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO data_source_credentials
                  (id, source_type, account_no, username, credentials_encrypted, encryption_key_version,
                   rotation_order, daily_quota, current_day_used, current_day_reset_at, is_active, instance_id)
                VALUES
                  (:id, :source_type, :account_no, :username, :credentials_encrypted, 1,
                   :rotation_order, :daily_quota, 0, CURRENT_DATE, :is_active, :instance_id)
                """
            ),
            {
                "id": credential_id,
                "source_type": source_type,
                "account_no": payload["account_no"],
                "username": payload["username"],
                "credentials_encrypted": encrypt_secret(
                    json.dumps(payload["raw_config"], ensure_ascii=False)
                    if payload.get("raw_config")
                    else payload.get("secret", "")
                ),
                "rotation_order": payload.get("rotation_order", 0),
                "daily_quota": payload.get("daily_quota"),
                "is_active": payload.get("is_active", True),
                "instance_id": get_settings().instance_id,
            },
        )
        rows = await self.list_data_source_credentials(conn, source_type)
        created = next(item for item in rows if item["id"] == credential_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="data_source_credential",
            entity_id=credential_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def patch_data_source_credential(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        credential_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self._load_credential_row(conn, source_type, credential_id)
        encrypted_value = before["credentials_encrypted"]
        if payload.get("raw_config"):
            encrypted_value = encrypt_secret(json.dumps(payload["raw_config"], ensure_ascii=False))
        elif payload.get("secret"):
            encrypted_value = encrypt_secret(payload["secret"])
        await conn.execute(
            text(
                """
                UPDATE data_source_credentials
                SET account_no = COALESCE(:account_no, account_no),
                    username = COALESCE(:username, username),
                    credentials_encrypted = :credentials_encrypted,
                    rotation_order = COALESCE(:rotation_order, rotation_order),
                    daily_quota = COALESCE(:daily_quota, daily_quota),
                    is_active = COALESCE(:is_active, is_active),
                    updated_at = now()
                WHERE id = :credential_id AND source_type = :source_type AND instance_id = :instance_id
                """
            ),
            {
                "credential_id": credential_id,
                "source_type": source_type,
                "account_no": payload.get("account_no"),
                "username": payload.get("username"),
                "credentials_encrypted": encrypted_value,
                "rotation_order": payload.get("rotation_order"),
                "daily_quota": payload.get("daily_quota"),
                "is_active": payload.get("is_active"),
                "instance_id": get_settings().instance_id,
            },
        )
        after = self._serialize_credential(await self._load_credential_row(conn, source_type, credential_id))
        await self.audit.write(
            conn,
            action="update",
            entity_type="data_source_credential",
            entity_id=credential_id,
            platform_user_id=platform_user_id,
            old_value=self._serialize_credential(before),
            new_value=after,
        )
        return after

    async def delete_data_source_credential(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        credential_id: str,
        platform_user_id: str,
    ) -> None:
        before = await self._load_credential_row(conn, source_type, credential_id)
        await conn.execute(
            text("DELETE FROM data_source_credentials WHERE id = :credential_id AND source_type = :source_type AND instance_id = :instance_id"),
            {"credential_id": credential_id, "source_type": source_type, "instance_id": get_settings().instance_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="data_source_credential",
            entity_id=credential_id,
            platform_user_id=platform_user_id,
            old_value=self._serialize_credential(before),
        )

    async def get_data_source_credential_secret(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        credential_id: str,
    ) -> dict:
        row = await self._load_credential_row(conn, source_type, credential_id)
        return {
            "id": str(row["id"]),
            "source_type": row["source_type"],
            "account_no": row["account_no"],
            "username": row["username"],
            "secret": decrypt_secret(row["credentials_encrypted"]),
        }

    async def list_platform_scoring_templates(
        self,
        conn: AsyncConnection,
        *,
        industry: str | None = None,
    ) -> list[dict]:
        _iid = get_settings().instance_id
        if industry is not None:
            query = """
                SELECT id, industry, name, description, is_active, dimensions, grade_thresholds, version, created_at, updated_at
                FROM platform_scoring_templates
                WHERE industry = :industry AND instance_id = :instance_id
                ORDER BY updated_at DESC
            """
            result = await conn.execute(text(query), {"industry": industry, "instance_id": _iid})
        else:
            query = """
                SELECT id, industry, name, description, is_active, dimensions, grade_thresholds, version, created_at, updated_at
                FROM platform_scoring_templates
                WHERE instance_id = :instance_id
                ORDER BY updated_at DESC
            """
            result = await conn.execute(text(query), {"instance_id": _iid})
        return [self._serialize_scoring_template(row) for row in result.mappings().all()]

    async def create_platform_scoring_template(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        template_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO platform_scoring_templates
                  (id, industry, name, description, is_active, dimensions, grade_thresholds, version, created_by, instance_id)
                VALUES
                  (:id, :industry, :name, :description, :is_active,
                   CAST(:dimensions AS jsonb), CAST(:grade_thresholds AS jsonb), 1, :created_by, :instance_id)
                """
            ),
            {
                "id": template_id,
                "industry": payload["industry"],
                "name": payload["name"],
                "description": payload.get("description"),
                "is_active": payload.get("is_active", True),
                "dimensions": self._to_json(payload["dimensions"]),
                "grade_thresholds": self._to_json(payload.get("grade_thresholds", {"S": 90, "A": 80, "B": 60, "C": 40, "D": 0})),
                "created_by": platform_user_id,
                "instance_id": get_settings().instance_id,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO platform_scoring_template_versions
                  (id, template_id, version, dimensions, grade_thresholds, changed_by, change_reason)
                VALUES
                  (:id, :template_id, 1, CAST(:dimensions AS jsonb), CAST(:grade_thresholds AS jsonb), :changed_by, 'create')
                """
            ),
            {
                "id": str(new_uuid()),
                "template_id": template_id,
                "dimensions": self._to_json(payload["dimensions"]),
                "grade_thresholds": self._to_json(payload.get("grade_thresholds", {"S": 90, "A": 80, "B": 60, "C": 40, "D": 0})),
                "changed_by": platform_user_id,
            },
        )
        created = await self.get_platform_scoring_template(conn, template_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="platform_scoring_template",
            entity_id=template_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def get_platform_scoring_template(self, conn: AsyncConnection, template_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, industry, name, description, is_active, dimensions, grade_thresholds, version, created_at, updated_at
                FROM platform_scoring_templates
                WHERE id = :template_id AND instance_id = :instance_id
                """
            ),
            {"template_id": template_id, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="平台评分模板不存在", status_code=404)
        return self._serialize_scoring_template(row)

    async def update_platform_scoring_template(
        self,
        conn: AsyncConnection,
        *,
        template_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_platform_scoring_template(conn, template_id)
        version = before["version"] + 1
        dimensions = payload.get("dimensions", before["dimensions"])
        grade_thresholds = payload.get("grade_thresholds", before["grade_thresholds"])
        await conn.execute(
            text(
                """
                UPDATE platform_scoring_templates
                SET industry = COALESCE(:industry, industry),
                    name = COALESCE(:name, name),
                    description = COALESCE(:description, description),
                    is_active = COALESCE(:is_active, is_active),
                    dimensions = CAST(:dimensions AS jsonb),
                    grade_thresholds = CAST(:grade_thresholds AS jsonb),
                    version = :version,
                    updated_at = now()
                WHERE id = :template_id AND instance_id = :instance_id
                """
            ),
            {
                "template_id": template_id,
                "industry": payload.get("industry"),
                "name": payload.get("name"),
                "description": payload.get("description"),
                "is_active": payload.get("is_active"),
                "dimensions": self._to_json(dimensions),
                "grade_thresholds": self._to_json(grade_thresholds),
                "version": version,
                "instance_id": get_settings().instance_id,
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO platform_scoring_template_versions
                  (id, template_id, version, dimensions, grade_thresholds, changed_by, change_reason)
                VALUES
                  (:id, :template_id, :version, CAST(:dimensions AS jsonb), CAST(:grade_thresholds AS jsonb), :changed_by, 'update')
                """
            ),
            {
                "id": str(new_uuid()),
                "template_id": template_id,
                "version": version,
                "dimensions": self._to_json(dimensions),
                "grade_thresholds": self._to_json(grade_thresholds),
                "changed_by": platform_user_id,
            },
        )
        after = await self.get_platform_scoring_template(conn, template_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="platform_scoring_template",
            entity_id=template_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )

        await self._sync_platform_template_to_tenants(conn, template_id=template_id, platform_dimensions=dimensions)

        return after

    async def _sync_platform_template_to_tenants(
        self,
        conn: AsyncConnection,
        *,
        template_id: str,
        platform_dimensions: list | dict,
    ) -> None:
        """将平台模板维度结构同步到所有关联租户，保留租户阈值，同步后重新评分。"""
        tenants = await conn.execute(text("""
            SELECT st.id, st.tenant_id, st.dimensions, st.grade_thresholds, st.version
            FROM scoring_templates st
            JOIN tenants t ON t.id = st.tenant_id
            WHERE st.source_platform_template_id = CAST(:pid AS uuid)
              AND t.instance_id = :instance_id
        """), {"pid": template_id, "instance_id": get_settings().instance_id})

        if isinstance(platform_dimensions, str):
            platform_dimensions = json.loads(platform_dimensions)

        for t in tenants.mappings().all():
            new_version = t["version"] + 1
            dims_json = json.dumps(platform_dimensions)

            await conn.execute(text("""
                UPDATE scoring_templates
                SET dimensions = CAST(:dims AS jsonb),
                    version = :version,
                    updated_at = now()
                WHERE id = CAST(:id AS uuid)
            """), {"dims": dims_json, "version": new_version, "id": str(t["id"])})

            await conn.execute(text("""
                INSERT INTO scoring_template_versions
                    (id, tenant_id, template_id, version, dimensions, grade_thresholds, change_reason)
                VALUES
                    (CAST(:vid AS uuid), CAST(:tid AS uuid), CAST(:tmpl_id AS uuid),
                     :version, CAST(:dims AS jsonb), CAST(:thresholds AS jsonb), 'platform sync')
            """), {
                "vid": str(new_uuid()),
                "tid": str(t["tenant_id"]),
                "tmpl_id": str(t["id"]),
                "version": new_version,
                "dims": dims_json,
                "thresholds": json.dumps(t["grade_thresholds"]) if not isinstance(t["grade_thresholds"], str) else t["grade_thresholds"],
            })

            try:
                count = await _scoring_engine.rescore_tenant_all(conn, tenant_id=str(t["tenant_id"]))
                _logger.info("平台模板同步后重新评分: tenant=%s, scored=%d", t["tenant_id"], count)
            except Exception:
                _logger.exception("平台模板同步后重新评分失败: tenant=%s", t["tenant_id"])

    async def delete_platform_scoring_template(self, conn: AsyncConnection, template_id: str) -> None:
        await conn.execute(
            text("DELETE FROM platform_scoring_templates WHERE id = :id AND instance_id = :instance_id"),
            {"id": template_id, "instance_id": get_settings().instance_id},
        )

    async def list_platform_scoring_template_versions(self, conn: AsyncConnection, template_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT pv.id, pv.template_id, pv.version, pv.dimensions, pv.grade_thresholds, pv.change_reason, pv.created_at
                FROM platform_scoring_template_versions pv
                JOIN platform_scoring_templates pt ON pt.id = pv.template_id
                WHERE pv.template_id = :template_id AND pt.instance_id = :instance_id
                ORDER BY pv.version DESC
                """
            ),
            {"template_id": template_id, "instance_id": get_settings().instance_id},
        )
        return [
            {
                "id": str(row["id"]),
                "template_id": str(row["template_id"]),
                "version": row["version"],
                "dimensions": row["dimensions"],
                "grade_thresholds": row["grade_thresholds"],
                "change_reason": row["change_reason"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def list_platform_email_templates(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, industry, name, description, category, subject, body_html, body_text, variables, is_active, created_at, updated_at
                FROM platform_email_templates
                WHERE instance_id = :instance_id
                ORDER BY updated_at DESC
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        return [self._serialize_platform_email_template(row) for row in result.mappings().all()]

    async def create_platform_email_template(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        content = self._sanitize_template_content(payload)
        template_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO platform_email_templates
                  (id, industry, name, description, category, subject, body_html, body_text, variables, is_active, instance_id)
                VALUES
                  (:id, :industry, :name, :description, :category, :subject, :body_html, :body_text,
                   CAST(:variables AS jsonb), :is_active, :instance_id)
                """
            ),
            {
                "id": template_id,
                "industry": payload["industry"],
                "name": payload["name"],
                "description": payload.get("description"),
                "category": payload.get("category", "default"),
                "subject": content["subject"],
                "body_html": content["body_html"],
                "body_text": content["body_text"],
                "variables": self._to_json(payload.get("variables", [])),
                "is_active": payload.get("is_active", True),
                "instance_id": get_settings().instance_id,
            },
        )
        template = await self.get_platform_email_template(conn, template_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="platform_email_template",
            entity_id=template_id,
            platform_user_id=platform_user_id,
            new_value=template,
        )
        return template

    async def get_platform_email_template(self, conn: AsyncConnection, template_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, industry, name, description, category, subject, body_html, body_text, variables, is_active, created_at, updated_at
                FROM platform_email_templates
                WHERE id = :template_id AND instance_id = :instance_id
                """
            ),
            {"template_id": template_id, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="平台邮件模板不存在", status_code=404)
        return self._serialize_platform_email_template(row)

    async def update_platform_email_template(
        self,
        conn: AsyncConnection,
        *,
        template_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_platform_email_template(conn, template_id)
        content = self._sanitize_template_content(payload)
        await conn.execute(
            text(
                """
                UPDATE platform_email_templates
                SET industry = COALESCE(:industry, industry),
                    name = COALESCE(:name, name),
                    description = COALESCE(:description, description),
                    category = COALESCE(:category, category),
                    subject = COALESCE(:subject, subject),
                    body_html = COALESCE(:body_html, body_html),
                    body_text = COALESCE(:body_text, body_text),
                    variables = CAST(:variables AS jsonb),
                    is_active = COALESCE(:is_active, is_active),
                    updated_at = now()
                WHERE id = :template_id AND instance_id = :instance_id
                """
            ),
            {
                "template_id": template_id,
                "industry": payload.get("industry"),
                "name": payload.get("name"),
                "description": payload.get("description"),
                "category": payload.get("category"),
                "subject": content["subject"],
                "body_html": content["body_html"],
                "body_text": content["body_text"],
                "variables": self._to_json(payload.get("variables", before["variables"])),
                "is_active": payload.get("is_active"),
                "instance_id": get_settings().instance_id,
            },
        )
        after = await self.get_platform_email_template(conn, template_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="platform_email_template",
            entity_id=template_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_platform_email_template(
        self,
        conn: AsyncConnection,
        *,
        template_id: str,
        platform_user_id: str,
    ) -> None:
        before = await self.get_platform_email_template(conn, template_id)
        await conn.execute(
            text("DELETE FROM platform_email_templates WHERE id = :template_id AND instance_id = :instance_id"),
            {"template_id": template_id, "instance_id": get_settings().instance_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="platform_email_template",
            entity_id=template_id,
            platform_user_id=platform_user_id,
            old_value=before,
        )

    async def get_platform_email_template_preview(self, conn: AsyncConnection, template_id: str) -> dict:
        template = await self.get_platform_email_template(conn, template_id)
        return {
            "id": template["id"],
            "subject": template["subject"],
            "body_html": template["body_html"],
            "body_text": template["body_text"],
        }

    async def list_intelligence_sources(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, tenant_id, name, source_type, url, fetch_config, industry_tags, is_active,
                       last_fetched_at, error_count, deleted_at, created_at, updated_at
                FROM intelligence_sources
                WHERE deleted_at IS NULL AND tenant_id IS NULL
                ORDER BY updated_at DESC
                """
            )
        )
        return [self._serialize_intelligence_source(row) for row in result.mappings().all()]

    async def create_intelligence_source(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        source_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO intelligence_sources
                  (id, tenant_id, name, source_type, url, fetch_config, industry_tags, is_active)
                VALUES
                  (:id, NULL, :name, :source_type, :url, CAST(:fetch_config AS jsonb), CAST(:industry_tags AS jsonb), :is_active)
                """
            ),
            {
                "id": source_id,
                "name": payload["name"],
                "source_type": payload["source_type"],
                "url": payload.get("url"),
                "fetch_config": self._to_json(payload.get("fetch_config", {"frequency_hours": 24})),
                "industry_tags": self._to_json(payload.get("industry_tags", [])),
                "is_active": payload.get("is_active", True),
            },
        )
        created = await self.get_intelligence_source(conn, source_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="intelligence_source",
            entity_id=source_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def batch_import_intelligence_sources(
        self,
        conn: AsyncConnection,
        *,
        items: list[dict],
        platform_user_id: str,
    ) -> list[dict]:
        created = []
        for item in items:
            created.append(await self.create_intelligence_source(conn, payload=item, platform_user_id=platform_user_id))
        return created

    async def get_intelligence_source(self, conn: AsyncConnection, source_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, tenant_id, name, source_type, url, fetch_config, industry_tags, is_active,
                       last_fetched_at, error_count, deleted_at, created_at, updated_at
                FROM intelligence_sources
                WHERE id = :source_id AND deleted_at IS NULL
                """
            ),
            {"source_id": source_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="情报源不存在", status_code=404)
        return self._serialize_intelligence_source(row)

    async def patch_intelligence_source(
        self,
        conn: AsyncConnection,
        *,
        source_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_intelligence_source(conn, source_id)
        await conn.execute(
            text(
                """
                UPDATE intelligence_sources
                SET name = COALESCE(:name, name),
                    source_type = COALESCE(:source_type, source_type),
                    url = COALESCE(:url, url),
                    fetch_config = CAST(:fetch_config AS jsonb),
                    industry_tags = CAST(:industry_tags AS jsonb),
                    is_active = COALESCE(:is_active, is_active),
                    updated_at = now()
                WHERE id = :source_id
                """
            ),
            {
                "source_id": source_id,
                "name": payload.get("name"),
                "source_type": payload.get("source_type"),
                "url": payload.get("url"),
                "fetch_config": self._to_json(payload.get("fetch_config", before["fetch_config"])),
                "industry_tags": self._to_json(payload.get("industry_tags", before["industry_tags"])),
                "is_active": payload.get("is_active"),
            },
        )
        after = await self.get_intelligence_source(conn, source_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="intelligence_source",
            entity_id=source_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_intelligence_source(
        self,
        conn: AsyncConnection,
        *,
        source_id: str,
        platform_user_id: str,
    ) -> None:
        before = await self.get_intelligence_source(conn, source_id)
        await conn.execute(
            text(
                """
                UPDATE intelligence_sources
                SET deleted_at = now(), updated_at = now()
                WHERE id = :source_id
                """
            ),
            {"source_id": source_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="intelligence_source",
            entity_id=source_id,
            platform_user_id=platform_user_id,
            old_value=before,
        )

    async def list_warmup_rules(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, name, is_active, min_observation_emails, bounce_alert_rate, config, created_at, updated_at
                FROM warmup_rules
                WHERE instance_id = :instance_id
                ORDER BY is_active DESC, updated_at DESC
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        items = []
        for row in result.mappings().all():
            levels = await self._list_warmup_rule_levels(conn, str(row["id"]))
            items.append(
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "is_active": row["is_active"],
                    "min_observation_emails": row["min_observation_emails"],
                    "bounce_alert_rate": self._decimal_to_float(row["bounce_alert_rate"]),
                    "config": row["config"],
                    "levels": levels,
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }
            )
        return items

    async def put_warmup_rules(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        current_rules = await self.list_warmup_rules(conn)
        active = next((item for item in current_rules if item["is_active"]), None)
        if active is None:
            rule_id = str(new_uuid())
            await conn.execute(
                text(
                    """
                    INSERT INTO warmup_rules
                      (id, name, is_active, min_observation_emails, bounce_alert_rate, config, instance_id)
                    VALUES
                      (:id, :name, true, :min_observation_emails, :bounce_alert_rate, CAST(:config AS jsonb), :instance_id)
                    """
                ),
                {
                    "id": rule_id,
                    "name": payload["name"],
                    "min_observation_emails": payload.get("min_observation_emails", 20),
                    "bounce_alert_rate": payload.get("bounce_alert_rate", 0.05),
                    "config": self._to_json(payload.get("config", {})),
                    "instance_id": get_settings().instance_id,
                },
            )
        else:
            rule_id = active["id"]
            await conn.execute(
                text(
                    """
                    UPDATE warmup_rules
                    SET name = :name,
                        min_observation_emails = :min_observation_emails,
                        bounce_alert_rate = :bounce_alert_rate,
                        config = CAST(:config AS jsonb),
                        updated_at = now()
                    WHERE id = :rule_id AND instance_id = :instance_id
                    """
                ),
                {
                    "rule_id": rule_id,
                    "name": payload["name"],
                    "min_observation_emails": payload.get("min_observation_emails", 20),
                    "bounce_alert_rate": payload.get("bounce_alert_rate", 0.05),
                    "config": self._to_json(payload.get("config", {})),
                    "instance_id": get_settings().instance_id,
                },
            )
            await conn.execute(text("DELETE FROM warmup_rule_levels WHERE rule_id = :rule_id"), {"rule_id": rule_id})

        for level in payload.get("levels", []):
            await conn.execute(
                text(
                    """
                    INSERT INTO warmup_rule_levels
                      (id, rule_id, level, daily_limit, min_stay_days, min_delivery_rate, max_bounce_rate, max_complaint_rate)
                    VALUES
                      (:id, :rule_id, :level, :daily_limit, :min_stay_days, :min_delivery_rate, :max_bounce_rate, :max_complaint_rate)
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "rule_id": rule_id,
                    "level": level["level"],
                    "daily_limit": level["daily_limit"],
                    "min_stay_days": level.get("min_stay_days", 1),
                    "min_delivery_rate": level.get("min_delivery_rate", 0.95),
                    "max_bounce_rate": level.get("max_bounce_rate", 0.02),
                    "max_complaint_rate": level.get("max_complaint_rate", 0.001),
                },
            )
        after = next((item for item in await self.list_warmup_rules(conn) if item["id"] == rule_id), None)
        if after is None:
            raise AppError(code="INTERNAL_ERROR", message="预热规则保存失败", status_code=500)
        await self.audit.write(
            conn,
            action="update",
            entity_type="warmup_rule",
            entity_id=rule_id,
            platform_user_id=platform_user_id,
            old_value=active,
            new_value=after,
        )
        return after

    async def list_ai_models(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, provider, model_id, display_name, is_active, config, created_at, updated_at
                FROM ai_models
                WHERE instance_id = :instance_id
                ORDER BY created_at DESC
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        return [self._serialize_ai_model(row) for row in result.mappings().all()]

    async def create_ai_model(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        model_id = str(new_uuid())
        await conn.execute(
            text(
                """
                INSERT INTO ai_models
                  (id, provider, model_id, display_name, is_active, config, instance_id)
                VALUES
                  (:id, :provider, :model_code, :display_name, :is_active, CAST(:config AS jsonb), :instance_id)
                """
            ),
            {
                "id": model_id,
                "provider": payload.get("provider", "openrouter"),
                "model_code": payload["model_id"],
                "display_name": payload["display_name"],
                "is_active": payload.get("is_active", True),
                "config": self._to_json(payload.get("config", {})),
                "instance_id": get_settings().instance_id,
            },
        )
        created = await self.get_ai_model(conn, model_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="ai_model",
            entity_id=model_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def get_ai_model(self, conn: AsyncConnection, model_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, provider, model_id, display_name, is_active, config, created_at, updated_at
                FROM ai_models
                WHERE id = :model_id AND instance_id = :instance_id
                """
            ),
            {"model_id": model_id, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="AI 模型不存在", status_code=404)
        return self._serialize_ai_model(row)

    async def patch_ai_model(
        self,
        conn: AsyncConnection,
        *,
        model_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_ai_model(conn, model_id)
        await conn.execute(
            text(
                """
                UPDATE ai_models
                SET provider = COALESCE(:provider, provider),
                    model_id = COALESCE(:model_code, model_id),
                    display_name = COALESCE(:display_name, display_name),
                    is_active = COALESCE(:is_active, is_active),
                    config = CAST(:config AS jsonb),
                    updated_at = now()
                WHERE id = :model_id AND instance_id = :instance_id
                """
            ),
            {
                "model_id": model_id,
                "provider": payload.get("provider"),
                "model_code": payload.get("model_id"),
                "display_name": payload.get("display_name"),
                "is_active": payload.get("is_active"),
                "config": self._to_json(payload.get("config", before["config"])),
                "instance_id": get_settings().instance_id,
            },
        )
        after = await self.get_ai_model(conn, model_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="ai_model",
            entity_id=model_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_ai_model(
        self,
        conn: AsyncConnection,
        *,
        model_id: str,
        platform_user_id: str,
    ) -> None:
        used_scene = await conn.execute(
            text("SELECT 1 FROM ai_scene_defaults WHERE model_id = :model_id AND instance_id = :instance_id LIMIT 1"),
            {"model_id": model_id, "instance_id": get_settings().instance_id},
        )
        if used_scene.first() is not None:
            raise AppError(code="CONFLICT", message="该模型仍被场景默认配置引用，不能删除", status_code=409)
        before = await self.get_ai_model(conn, model_id)
        await conn.execute(text("DELETE FROM ai_models WHERE id = :model_id AND instance_id = :instance_id"), {"model_id": model_id, "instance_id": get_settings().instance_id})
        await self.audit.write(
            conn,
            action="delete",
            entity_type="ai_model",
            entity_id=model_id,
            platform_user_id=platform_user_id,
            old_value=before,
        )

    async def list_ai_scene_defaults(self, conn: AsyncConnection) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT s.id, s.scene, s.model_id, s.config, s.created_at, s.updated_at,
                       m.display_name, m.is_active
                FROM ai_scene_defaults s
                JOIN ai_models m ON m.id = s.model_id
                WHERE s.instance_id = :instance_id
                ORDER BY s.scene
                """
            ),
            {"instance_id": get_settings().instance_id},
        )
        return [
            {
                "id": str(row["id"]),
                "scene": row["scene"],
                "model_id": str(row["model_id"]),
                "model_display_name": row["display_name"],
                "model_is_active": row["is_active"],
                "config": row["config"],
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def put_ai_scene_defaults(
        self,
        conn: AsyncConnection,
        *,
        payload: list,
        platform_user_id: str,
    ) -> list[dict]:
        items = payload
        for item in items:
            _iid = get_settings().instance_id
            model_check = await conn.execute(
                text("SELECT is_active FROM ai_models WHERE id = :model_id AND instance_id = :instance_id"),
                {"model_id": item["model_id"], "instance_id": _iid},
            )
            row = model_check.mappings().first()
            if row is None:
                raise AppError(code="NOT_FOUND", message="默认模型不存在", status_code=404)
            if row["is_active"] is not True:
                raise AppError(code="VALIDATION_ERROR", message="场景默认模型不能引用 inactive 模型", status_code=422)
            existing = await conn.execute(
                text("SELECT id FROM ai_scene_defaults WHERE scene = :scene AND instance_id = :instance_id"),
                {"scene": item["scene"], "instance_id": _iid},
            )
            existing_row = existing.mappings().first()
            if existing_row is None:
                await conn.execute(
                    text(
                        """
                        INSERT INTO ai_scene_defaults
                          (id, scene, model_id, config, instance_id)
                        VALUES
                          (:id, :scene, :model_id, CAST(:config AS jsonb), :instance_id)
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "scene": item["scene"],
                        "model_id": item["model_id"],
                        "config": self._to_json(item.get("config", {})),
                        "instance_id": _iid,
                    },
                )
            else:
                await conn.execute(
                    text(
                        """
                        UPDATE ai_scene_defaults
                        SET model_id = :model_id,
                            config = CAST(:config AS jsonb),
                            updated_at = now()
                        WHERE scene = :scene AND instance_id = :instance_id
                        """
                    ),
                    {
                        "scene": item["scene"],
                        "model_id": item["model_id"],
                        "config": self._to_json(item.get("config", {})),
                        "instance_id": _iid,
                    },
                )
        after = await self.list_ai_scene_defaults(conn)
        await self.audit.write(
            conn,
            action="update",
            entity_type="ai_scene_defaults",
            platform_user_id=platform_user_id,
            new_value=after,
        )
        return after

    async def get_ai_pricing(self, conn: AsyncConnection) -> dict:
        models = await self.list_ai_models(conn)
        scenes = await self.list_ai_scene_defaults(conn)
        return {"models": models, "scene_defaults": scenes}

    async def put_ai_pricing(
        self,
        conn: AsyncConnection,
        *,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        # input_price / output_price columns have been removed; pricing is now managed per-model
        return await self.get_ai_pricing(conn)

    async def list_tenant_users(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT u.id, u.email, u.name, u.status, u.must_change_pwd, u.last_login_at, u.created_at,
                       array_remove(array_agg(ur.role ORDER BY ur.role), NULL) AS roles
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.id AND ur.tenant_id = u.tenant_id
                WHERE u.tenant_id = :tenant_id
                GROUP BY u.id
                ORDER BY u.created_at ASC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [
            {
                "id": str(row["id"]),
                "email": row["email"],
                "name": row["name"],
                "status": row["status"],
                "must_change_pwd": row["must_change_pwd"],
                "roles": list(row["roles"] or []),
                "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
                "created_at": row["created_at"].isoformat(),
            }
            for row in result.mappings().all()
        ]

    async def create_tenant_user(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        user_id = str(new_uuid())
        roles = payload.get("roles", ["viewer"])
        self._validate_tenant_roles(roles)
        await conn.execute(
            text(
                """
                INSERT INTO users
                  (id, tenant_id, email, password_hash, name, status, must_change_pwd)
                VALUES
                  (:id, :tenant_id, :email, :password_hash, :name, :status, :must_change_pwd)
                """
            ),
            {
                "id": user_id,
                "tenant_id": tenant_id,
                "email": payload["email"],
                "password_hash": hash_password(payload.get("password", "temporary-password")),
                "name": payload["name"],
                "status": payload.get("status", "active"),
                "must_change_pwd": payload.get("must_change_pwd", True),
            },
        )
        for role in roles:
            await conn.execute(
                text(
                    """
                    INSERT INTO user_roles (id, tenant_id, user_id, role)
                    VALUES (:id, :tenant_id, :user_id, CAST(:role AS user_role))
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "role": role,
                },
            )
        users = await self.list_tenant_users(conn, tenant_id)
        created = next(item for item in users if item["id"] == user_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="tenant_user",
            entity_id=user_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            new_value=created,
        )
        return created

    async def update_tenant_user(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self._get_tenant_user(conn, tenant_id, user_id)
        await conn.execute(
            text(
                """
                UPDATE users
                SET email = COALESCE(:email, email),
                    name = COALESCE(:name, name),
                    status = COALESCE(:status, status),
                    must_change_pwd = COALESCE(:must_change_pwd, must_change_pwd),
                    password_hash = COALESCE(:password_hash, password_hash),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :user_id
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "email": payload.get("email"),
                "name": payload.get("name"),
                "status": payload.get("status"),
                "must_change_pwd": payload.get("must_change_pwd"),
                "password_hash": hash_password(payload["password"]) if payload.get("password") else None,
            },
        )
        if "roles" in payload:
            self._validate_tenant_roles(payload["roles"])
            await conn.execute(
                text("DELETE FROM user_roles WHERE tenant_id = :tenant_id AND user_id = :user_id"),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
            for role in payload["roles"]:
                await conn.execute(
                    text(
                        """
                        INSERT INTO user_roles (id, tenant_id, user_id, role)
                        VALUES (:id, :tenant_id, :user_id, CAST(:role AS user_role))
                        """
                    ),
                    {
                        "id": str(new_uuid()),
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "role": role,
                    },
                )
        after = await self._get_tenant_user(conn, tenant_id, user_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="tenant_user",
            entity_id=user_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_tenant_user(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        platform_user_id: str,
    ) -> None:
        before = await self._get_tenant_user(conn, tenant_id, user_id)
        await conn.execute(text("DELETE FROM users WHERE tenant_id = :tenant_id AND id = :user_id"), {"tenant_id": tenant_id, "user_id": user_id})
        await self.audit.write(
            conn,
            action="delete",
            entity_type="tenant_user",
            entity_id=user_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            old_value=before,
        )

    async def list_tenant_domains(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT id, tenant_id, domain, verification_status, dns_verified_at, dns_last_checked_at,
                       warmup_rule_id, warmup_level, daily_limit, total_sent, bounce_rate, complaint_rate,
                       open_rate, level_changed_at, sender_email, created_at, updated_at
                FROM domain_warmup_status
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [self._serialize_domain(row) for row in result.mappings().all()]

    async def create_tenant_domain(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        domain_id = str(new_uuid())
        rule_id = payload.get("warmup_rule_id")
        warmup_level = payload.get("warmup_level")
        if rule_id is None or warmup_level is None:
            raise AppError(
                code="VALIDATION_ERROR",
                message="请选择有效的预热档位后再添加域名",
                status_code=422,
            )
        level_result = await conn.execute(
            text(
                """
                SELECT wrl.daily_limit
                FROM warmup_rules wr
                JOIN warmup_rule_levels wrl ON wrl.rule_id = wr.id
                WHERE wr.id = :rule_id
                  AND wr.is_active = true
                  AND wrl.level = :warmup_level
                """
            ),
            {"rule_id": rule_id, "warmup_level": warmup_level},
        )
        level_row = level_result.mappings().first()
        if level_row is None:
            raise AppError(
                code="VALIDATION_ERROR",
                message="预热规则或档位已变化，请刷新后重新选择预热档位",
                status_code=422,
            )
        daily_limit = level_row["daily_limit"]
        await conn.execute(
            text(
                """
                INSERT INTO domain_warmup_status
                  (id, tenant_id, domain, spf_record, dkim_record, dmarc_record, verification_status,
                   warmup_rule_id, warmup_level, daily_limit, sender_email, level_changed_at)
                VALUES
                  (:id, :tenant_id, :domain, :spf_record, :dkim_record, :dmarc_record, :verification_status,
                   :warmup_rule_id, :warmup_level, :daily_limit, :sender_email, now())
                """
            ),
            {
                "id": domain_id,
                "tenant_id": tenant_id,
                "domain": payload["domain"].lower(),
                "spf_record": payload.get("spf_record"),
                "dkim_record": payload.get("dkim_record"),
                "dmarc_record": payload.get("dmarc_record"),
                "verification_status": payload.get("verification_status", "pending"),
                "warmup_rule_id": rule_id,
                "warmup_level": warmup_level,
                "daily_limit": daily_limit,
                "sender_email": payload.get("sender_email"),
            },
        )
        await conn.execute(
            text(
                """
                INSERT INTO domain_warmup_history
                  (id, tenant_id, warmup_status_id, domain, warmup_level, daily_limit, total_sent, change_type, change_reason)
                VALUES
                  (:id, :tenant_id, :warmup_status_id, :domain, :warmup_level, :daily_limit, 0, 'manual_adjust', 'domain created')
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": tenant_id,
                "warmup_status_id": domain_id,
                "domain": payload["domain"].lower(),
                "warmup_level": warmup_level,
                "daily_limit": daily_limit,
            },
        )
        domain = await self.get_tenant_domain(conn, tenant_id, domain_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="tenant_domain",
            entity_id=domain_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            new_value=domain,
        )
        return domain

    async def update_tenant_domain(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        domain_id: str,
        payload: dict,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_tenant_domain(conn, tenant_id, domain_id)
        payload.pop("domain", None)

        rule_id = payload.get("warmup_rule_id")
        warmup_level = payload.get("warmup_level")
        if rule_id is not None and warmup_level is not None:
            level_result = await conn.execute(
                text(
                    """
                    SELECT wrl.daily_limit
                    FROM warmup_rules wr
                    JOIN warmup_rule_levels wrl ON wrl.rule_id = wr.id
                    WHERE wr.id = :rule_id
                      AND wr.is_active = true
                      AND wrl.level = :warmup_level
                    """
                ),
                {"rule_id": rule_id, "warmup_level": warmup_level},
            )
            level_row = level_result.mappings().first()
            if level_row is None:
                raise AppError(
                    code="VALIDATION_ERROR",
                    message="预热规则或档位已变化，请刷新后重新选择预热档位",
                    status_code=422,
                )
            daily_limit = level_row["daily_limit"]
            await conn.execute(
                text(
                    """
                    UPDATE domain_warmup_status
                    SET warmup_rule_id = :warmup_rule_id,
                        warmup_level = :warmup_level,
                        daily_limit = :daily_limit,
                        level_changed_at = now(),
                        updated_at = now()
                    WHERE id = :domain_id AND tenant_id = :tenant_id
                    """
                ),
                {
                    "warmup_rule_id": rule_id,
                    "warmup_level": warmup_level,
                    "daily_limit": daily_limit,
                    "domain_id": domain_id,
                    "tenant_id": tenant_id,
                },
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO domain_warmup_history
                      (id, tenant_id, warmup_status_id, domain, warmup_level, daily_limit, total_sent, change_type, change_reason)
                    VALUES
                      (:id, :tenant_id, :warmup_status_id, :domain, :warmup_level, :daily_limit, 0, 'manual_adjust', 'warmup config updated')
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": tenant_id,
                    "warmup_status_id": domain_id,
                    "domain": before["domain"],
                    "warmup_level": warmup_level,
                    "daily_limit": daily_limit,
                },
            )

        if "sender_email" in payload:
            await conn.execute(
                text(
                    """
                    UPDATE domain_warmup_status
                    SET sender_email = :sender_email, updated_at = now()
                    WHERE id = :domain_id AND tenant_id = :tenant_id
                    """
                ),
                {
                    "sender_email": payload["sender_email"],
                    "domain_id": domain_id,
                    "tenant_id": tenant_id,
                },
            )

        domain = await self.get_tenant_domain(conn, tenant_id, domain_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="tenant_domain",
            entity_id=domain_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=domain,
        )
        return domain

    async def delete_tenant_domain(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        domain_id: str,
        platform_user_id: str,
    ) -> None:
        domain = await self.get_tenant_domain(conn, tenant_id, domain_id)

        usage_result = await conn.execute(
            text("SELECT COUNT(*) FROM domain_daily_usage WHERE domain_id = :domain_id"),
            {"domain_id": domain_id},
        )
        if usage_result.scalar_one() > 0:
            raise AppError(
                code="CONFLICT",
                message="该域名存在关联数据，无法删除",
                status_code=409,
            )

        plan_result = await conn.execute(
            text("SELECT COUNT(*) FROM sending_plans WHERE domain_id = :domain_id"),
            {"domain_id": domain_id},
        )
        if plan_result.scalar_one() > 0:
            raise AppError(
                code="CONFLICT",
                message="该域名存在关联数据，无法删除",
                status_code=409,
            )

        await conn.execute(
            text("DELETE FROM domain_warmup_status WHERE id = :domain_id AND tenant_id = :tenant_id"),
            {"domain_id": domain_id, "tenant_id": tenant_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="tenant_domain",
            entity_id=domain_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            old_value=domain,
        )

    async def verify_tenant_domain(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        domain_id: str,
        platform_user_id: str,
    ) -> dict:
        before = await self.get_tenant_domain(conn, tenant_id, domain_id)
        await conn.execute(
            text(
                """
                UPDATE domain_warmup_status
                SET verification_status = 'verified',
                    dns_verified_at = now(),
                    dns_last_checked_at = now(),
                    updated_at = now()
                WHERE tenant_id = :tenant_id AND id = :domain_id
                """
            ),
            {"tenant_id": tenant_id, "domain_id": domain_id},
        )
        await conn.execute(
            text(
                """
                INSERT INTO domain_warmup_history
                  (id, tenant_id, warmup_status_id, domain, warmup_level, daily_limit, total_sent, change_type, change_reason)
                SELECT :id, tenant_id, id, domain, warmup_level, daily_limit, total_sent, 'manual_adjust', 'domain verified'
                FROM domain_warmup_status
                WHERE id = :domain_id
                """
            ),
            {"id": str(new_uuid()), "domain_id": domain_id},
        )
        after = await self.get_tenant_domain(conn, tenant_id, domain_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="tenant_domain",
            entity_id=domain_id,
            tenant_id=tenant_id,
            platform_user_id=platform_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def get_tenant_domain(self, conn: AsyncConnection, tenant_id: str, domain_id: str) -> dict:
        result = await conn.execute(
            text(
                """
                SELECT id, tenant_id, domain, verification_status, dns_verified_at, dns_last_checked_at,
                       warmup_rule_id, warmup_level, daily_limit, total_sent, bounce_rate, complaint_rate,
                       open_rate, level_changed_at, sender_email, created_at, updated_at
                FROM domain_warmup_status
                WHERE tenant_id = :tenant_id AND id = :domain_id
                """
            ),
            {"tenant_id": tenant_id, "domain_id": domain_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="租户域名不存在", status_code=404)
        return self._serialize_domain(row)

    async def get_platform_dashboard(self, conn: AsyncConnection) -> dict:
        _iid = get_settings().instance_id
        result = await conn.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM tenants WHERE status = 'active' AND instance_id = :instance_id) AS active_tenants,
                  (SELECT count(*) FROM users u JOIN tenants t ON t.id = u.tenant_id WHERE t.instance_id = :instance_id) AS total_users,
                  (SELECT count(*) FROM sending_plans sp JOIN tenants t ON t.id = sp.tenant_id WHERE sp.status = 'running' AND sp.deleted_at IS NULL AND t.instance_id = :instance_id) AS running_sending_plans,
                  (SELECT count(*) FROM intelligence_articles) AS total_articles,
                  (SELECT count(*) FROM tenant_ai_provider_configs c JOIN tenants t ON t.id = c.tenant_id WHERE c.provider = 'openrouter' AND t.instance_id = :instance_id) AS configured_openrouter_tenants
                """
            ),
            {"instance_id": _iid},
        )
        row = result.mappings().one()
        return {
            "active_tenants": row["active_tenants"],
            "total_users": row["total_users"],
            "running_collection_tasks": 0,
            "running_sending_plans": row["running_sending_plans"],
            "total_articles": row["total_articles"],
            "configured_openrouter_tenants": row["configured_openrouter_tenants"],
        }

    async def get_collection_task_monitor(self, conn: AsyncConnection) -> list[dict]:
        return []

    async def _get_tenant_user(self, conn: AsyncConnection, tenant_id: str, user_id: str) -> dict:
        users = await self.list_tenant_users(conn, tenant_id)
        item = next((user for user in users if user["id"] == user_id), None)
        if item is None:
            raise AppError(code="NOT_FOUND", message="租户用户不存在", status_code=404)
        return item

    async def _load_credential_row(self, conn: AsyncConnection, source_type: str, credential_id: str):
        result = await conn.execute(
            text(
                """
                SELECT id, source_type, account_no, username, credentials_encrypted, encryption_key_version,
                       rotation_order, daily_quota, current_day_used, current_day_reset_at, is_active,
                       last_used_at, last_error_at, last_error_message, consecutive_error_count, created_at
                FROM data_source_credentials
                WHERE source_type = :source_type AND id = :credential_id AND instance_id = :instance_id
                """
            ),
            {"source_type": source_type, "credential_id": credential_id, "instance_id": get_settings().instance_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="数据源凭证不存在", status_code=404)
        return row

    async def _list_warmup_rule_levels(self, conn: AsyncConnection, rule_id: str) -> list[dict]:
        result = await conn.execute(
            text(
                """
                SELECT level, daily_limit, min_stay_days, min_delivery_rate, max_bounce_rate, max_complaint_rate
                FROM warmup_rule_levels
                WHERE rule_id = :rule_id
                ORDER BY level ASC
                """
            ),
            {"rule_id": rule_id},
        )
        return [
            {
                "level": row["level"],
                "daily_limit": row["daily_limit"],
                "min_stay_days": row["min_stay_days"],
                "min_delivery_rate": self._decimal_to_float(row["min_delivery_rate"]),
                "max_bounce_rate": self._decimal_to_float(row["max_bounce_rate"]),
                "max_complaint_rate": self._decimal_to_float(row["max_complaint_rate"]),
            }
            for row in result.mappings().all()
        ]

    def _validate_tenant_roles(self, roles: list[str]) -> None:
        invalid = set(roles) - {"admin", "operator", "viewer"}
        if invalid:
            raise AppError(code="VALIDATION_ERROR", message="租户角色仅允许 admin/operator/viewer", status_code=422)

    def _serialize_data_source(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "source_type": row["source_type"],
            "name": row["name"],
            "alias_code": row["alias_code"],
            "purpose": row["purpose"],
            "is_active": row["is_active"],
            "config": row["config"],
            "landing_rules": row["landing_rules"],
            "active_credentials_count": row["active_credentials_count"],
        }

    def _serialize_credential(self, row) -> dict:
        decrypted = decrypt_secret(row["credentials_encrypted"])
        raw_config: dict | None = None
        secret_masked = ""
        try:
            parsed = json.loads(decrypted)
            if isinstance(parsed, dict):
                raw_config = parsed
        except (json.JSONDecodeError, TypeError):
            secret_masked = self._mask_secret(decrypted)
        return {
            "id": str(row["id"]),
            "source_type": row["source_type"],
            "account_no": row["account_no"],
            "username": row["username"],
            "secret_masked": secret_masked,
            "raw_config": raw_config,
            "rotation_order": row["rotation_order"],
            "daily_quota": row["daily_quota"],
            "current_day_used": row["current_day_used"],
            "current_day_reset_at": row["current_day_reset_at"].isoformat() if row["current_day_reset_at"] else None,
            "is_active": row["is_active"],
            "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
            "last_error_at": row["last_error_at"].isoformat() if row["last_error_at"] else None,
            "last_error_message": row["last_error_message"],
            "consecutive_error_count": row["consecutive_error_count"],
            "created_at": row["created_at"].isoformat(),
        }

    def _serialize_scoring_template(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "industry": row["industry"],
            "name": row["name"],
            "description": row["description"],
            "is_active": row["is_active"],
            "dimensions": row["dimensions"],
            "grade_thresholds": row["grade_thresholds"],
            "version": row["version"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_platform_email_template(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "industry": row["industry"],
            "name": row["name"],
            "description": row["description"],
            "category": row["category"],
            "subject": row["subject"],
            "body_html": row["body_html"],
            "body_text": row["body_text"],
            "variables": row["variables"],
            "is_active": row["is_active"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _sanitize_template_content(self, payload: dict) -> dict:
        return {
            "subject": sanitize_subject(payload.get("subject")),
            "body_html": sanitize_html(payload.get("body_html")),
            "body_text": sanitize_plain_text(payload.get("body_text")),
        }

    def _serialize_intelligence_source(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]) if row["tenant_id"] else None,
            "name": row["name"],
            "source_type": row["source_type"],
            "url": row["url"],
            "fetch_config": row["fetch_config"],
            "industry_tags": row["industry_tags"],
            "is_active": row["is_active"],
            "last_fetched_at": row["last_fetched_at"].isoformat() if row["last_fetched_at"] else None,
            "error_count": row["error_count"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_ai_model(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "provider": row["provider"],
            "model_id": row["model_id"],
            "display_name": row["display_name"],
            "is_active": row["is_active"],
            "config": row["config"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _serialize_domain(self, row) -> dict:
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "domain": row["domain"],
            "verification_status": row["verification_status"],
            "dns_verified_at": row["dns_verified_at"].isoformat() if row["dns_verified_at"] else None,
            "dns_last_checked_at": row["dns_last_checked_at"].isoformat() if row["dns_last_checked_at"] else None,
            "warmup_rule_id": str(row["warmup_rule_id"]) if row["warmup_rule_id"] else None,
            "warmup_level": row["warmup_level"],
            "daily_limit": row["daily_limit"],
            "total_sent": row["total_sent"],
            "bounce_rate": self._decimal_to_float(row["bounce_rate"]),
            "complaint_rate": self._decimal_to_float(row["complaint_rate"]),
            "open_rate": self._decimal_to_float(row["open_rate"]),
            "level_changed_at": row["level_changed_at"].isoformat() if row["level_changed_at"] else None,
            "sender_email": row["sender_email"],
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _mask_secret(self, value: str) -> str:
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:2]}***{value[-2:]}"

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _decimal_to_float(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None
