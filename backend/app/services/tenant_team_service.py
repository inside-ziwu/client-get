import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.security.passwords import hash_password
from app.services.audit_service import AuditService

_EMAIL_RE = re.compile(r"^.+@.+\..+$")


class TenantTeamService:
    allowed_roles = {"admin", "operator", "viewer"}

    def __init__(self) -> None:
        self.audit = AuditService()

    async def list_users(self, conn: AsyncConnection, tenant_id: str) -> list[dict]:
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

    async def create_user(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        actor_user_id: str,
        payload: dict,
    ) -> dict:
        roles = payload.get("roles", ["viewer"])
        self._validate_roles(roles)
        user_id = str(new_uuid())
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
                {"id": str(new_uuid()), "tenant_id": tenant_id, "user_id": user_id, "role": role},
            )
        created = await self.get_user(conn, tenant_id, user_id)
        await self.audit.write(
            conn,
            action="create",
            entity_type="tenant_user",
            entity_id=user_id,
            tenant_id=tenant_id,
            user_id=actor_user_id,
            new_value=created,
        )
        return created

    async def update_user(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        actor_user_id: str,
        payload: dict,
    ) -> dict:
        before = await self.get_user(conn, tenant_id, user_id)
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
            self._validate_roles(payload["roles"])
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
                    {"id": str(new_uuid()), "tenant_id": tenant_id, "user_id": user_id, "role": role},
                )
        after = await self.get_user(conn, tenant_id, user_id)
        await self.audit.write(
            conn,
            action="update",
            entity_type="tenant_user",
            entity_id=user_id,
            tenant_id=tenant_id,
            user_id=actor_user_id,
            old_value=before,
            new_value=after,
        )
        return after

    async def delete_user(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        actor_user_id: str,
    ) -> None:
        before = await self.get_user(conn, tenant_id, user_id)
        await conn.execute(
            text("DELETE FROM users WHERE tenant_id = :tenant_id AND id = :user_id"),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        await self.audit.write(
            conn,
            action="delete",
            entity_type="tenant_user",
            entity_id=user_id,
            tenant_id=tenant_id,
            user_id=actor_user_id,
            old_value=before,
        )

    async def get_user(self, conn: AsyncConnection, tenant_id: str, user_id: str) -> dict:
        users = await self.list_users(conn, tenant_id)
        for item in users:
            if item["id"] == user_id:
                return item
        raise AppError(code="NOT_FOUND", message="租户用户不存在", status_code=404)

    async def update_test_email(self, conn: AsyncConnection, user_id: str, test_email: str) -> None:
        if not test_email or not _EMAIL_RE.match(test_email):
            raise AppError(code="VALIDATION_ERROR", message="邮箱格式不正确", status_code=422)
        await conn.execute(
            text("UPDATE users SET test_email = :test_email WHERE id = :user_id"),
            {"test_email": test_email, "user_id": user_id},
        )

    async def get_test_email(self, conn: AsyncConnection, user_id: str) -> str | None:
        result = await conn.execute(
            text("SELECT test_email FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        return result.scalar_one_or_none()

    def _validate_roles(self, roles: list[str]) -> None:
        if not roles:
            raise AppError(code="VALIDATION_ERROR", message="至少需要一个角色", status_code=422)
        invalid = [role for role in roles if role not in self.allowed_roles]
        if invalid:
            raise AppError(code="VALIDATION_ERROR", message=f"无效角色: {', '.join(invalid)}", status_code=422)
