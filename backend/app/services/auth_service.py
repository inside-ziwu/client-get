from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.pools import get_engine
from app.security.jwt import create_access_token, create_refresh_token
from app.security.passwords import hash_password, verify_password


class AuthService:
    lock_minutes = 15
    max_failed_attempts = 5

    async def platform_login(self, conn: AsyncConnection, email: str, password: str) -> tuple[str, str]:
        result = await conn.execute(
            text(
                """
                SELECT id, email, password_hash, name, status, failed_login_count, locked_until
                FROM platform_users
                WHERE lower(email) = lower(:email)
                  AND instance_id = :instance_id
                """
            ),
            {"email": email, "instance_id": get_settings().instance_id},
        )
        user = result.mappings().first()
        if user is None:
            raise AppError(code="INVALID_CREDENTIALS", message="邮箱或密码错误", status_code=401)
        await self._assert_loginable(user["status"], user["locked_until"])
        if not verify_password(password, user["password_hash"]):
            await self._record_failed_platform_login(conn, str(user["id"]), user["failed_login_count"])
            raise AppError(code="INVALID_CREDENTIALS", message="邮箱或密码错误", status_code=401)
        await self._record_platform_login_success(conn, str(user["id"]))
        claims = {
            "sub": str(user["id"]),
            "kind": "platform",
            "roles": ["platform_admin"],
        }
        return create_access_token(claims), create_refresh_token(claims)

    async def tenant_login(self, conn: AsyncConnection, slug: str, email: str, password: str) -> str:
        result = await conn.execute(
            text(
                """
                SELECT
                  u.id,
                  u.email,
                  u.password_hash,
                  u.name,
                  u.status,
                  u.must_change_pwd,
                  u.failed_login_count,
                  u.locked_until,
                  t.id AS tenant_id,
                  t.slug,
                  t.status AS tenant_status
                FROM users u
                JOIN tenants t ON t.id = u.tenant_id
                WHERE t.slug = :slug AND lower(u.email) = lower(:email)
                  AND t.instance_id = :instance_id
                """
            ),
            {"slug": slug, "email": email, "instance_id": get_settings().instance_id},
        )
        user = result.mappings().first()
        if user is None:
            raise AppError(code="INVALID_CREDENTIALS", message="邮箱或密码错误", status_code=401)
        if user["tenant_status"] != "active":
            raise AppError(code="TENANT_INACTIVE", message="租户不可用", status_code=403)
        await self._assert_loginable(user["status"], user["locked_until"])
        if not verify_password(password, user["password_hash"]):
            await self._record_failed_tenant_login(conn, str(user["id"]), user["failed_login_count"])
            raise AppError(code="INVALID_CREDENTIALS", message="邮箱或密码错误", status_code=401)

        role_result = await conn.execute(
            text(
                """
                SELECT role
                FROM user_roles
                WHERE user_id = :user_id AND tenant_id = :tenant_id
                ORDER BY role
                """
            ),
            {"user_id": user["id"], "tenant_id": user["tenant_id"]},
        )
        roles = [item[0] for item in role_result.all()]
        await self._record_tenant_login_success(conn, str(user["id"]))
        return create_access_token(
            {
                "sub": str(user["id"]),
                "kind": "tenant",
                "tid": str(user["tenant_id"]),
                "slug": user["slug"],
                "roles": roles,
            }
        )

    async def change_password(
        self,
        conn: AsyncConnection,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        result = await conn.execute(
            text("SELECT password_hash FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        row = result.mappings().first()
        if row is None or not verify_password(current_password, row["password_hash"]):
            raise AppError(code="INVALID_CREDENTIALS", message="当前密码错误", status_code=401)

        await conn.execute(
            text(
                """
                UPDATE users
                SET password_hash = :password_hash,
                    must_change_pwd = false,
                    updated_at = now()
                WHERE id = :user_id
                """
            ),
            {"user_id": user_id, "password_hash": hash_password(new_password)},
        )

    async def _assert_loginable(self, status: str, locked_until) -> None:
        if status != "active":
            raise AppError(code="ACCOUNT_DISABLED", message="账号已禁用", status_code=403)
        if locked_until is not None and locked_until > datetime.now(timezone.utc):
            raise AppError(code="ACCOUNT_LOCKED", message="账号已锁定，请稍后再试", status_code=423)

    async def _record_failed_platform_login(
        self,
        conn: AsyncConnection,
        user_id: str,
        failed_count: int,
    ) -> None:
        await self._record_failed_login("platform_users", user_id, failed_count)

    async def _record_failed_tenant_login(
        self,
        conn: AsyncConnection,
        user_id: str,
        failed_count: int,
    ) -> None:
        await self._record_failed_login("users", user_id, failed_count)

    async def _record_failed_login(
        self,
        table_name: str,
        user_id: str,
        failed_count: int,
    ) -> None:
        next_failed_count = failed_count + 1
        locked_until_sql = (
            "now() + interval '15 minutes'" if next_failed_count >= self.max_failed_attempts else "NULL"
        )
        async with get_engine().begin() as conn:
            await conn.execute(
                text(
                    f"""
                    UPDATE {table_name}
                    SET failed_login_count = :failed_count,
                        locked_until = {locked_until_sql},
                        updated_at = now()
                    WHERE id = :user_id
                    """
                ),
                {"user_id": user_id, "failed_count": next_failed_count},
            )

    async def _record_platform_login_success(self, conn: AsyncConnection, user_id: str) -> None:
        await self._record_login_success("platform_users", user_id)

    async def _record_tenant_login_success(self, conn: AsyncConnection, user_id: str) -> None:
        await self._record_login_success("users", user_id)

    async def _record_login_success(
        self,
        table_name: str,
        user_id: str,
    ) -> None:
        async with get_engine().begin() as conn:
            await conn.execute(
                text(
                    f"""
                    UPDATE {table_name}
                    SET failed_login_count = 0,
                        locked_until = NULL,
                        last_login_at = now(),
                        updated_at = now()
                    WHERE id = :user_id
                    """
                ),
                {"user_id": user_id},
            )
