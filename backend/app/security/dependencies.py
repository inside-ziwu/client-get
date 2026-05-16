from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.db.pools import get_connection
from app.db.rls import set_current_tenant
from app.security.jwt import decode_access_token

http_bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class PlatformAuthContext:
    platform_user_id: str
    email: str
    name: str
    roles: list[str]
    connection: AsyncConnection


@dataclass(slots=True)
class TenantAuthContext:
    tenant_id: str
    tenant_slug: str
    user_id: str
    email: str
    name: str
    roles: list[str]
    must_change_pwd: bool
    connection: AsyncConnection


def _extract_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(code="UNAUTHORIZED", message="缺少授权令牌", status_code=401)
    return credentials.credentials


async def get_current_platform_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    conn: AsyncConnection = Depends(get_connection),
) -> PlatformAuthContext:
    payload = decode_access_token(_extract_token(credentials))
    if payload.get("kind") != "platform":
        raise AppError(code="FORBIDDEN", message="平台令牌类型不正确", status_code=403)

    result = await conn.execute(
        text(
            """
            SELECT id, email, name, status
            FROM platform_users
            WHERE id = :user_id
            """
        ),
        {"user_id": payload["sub"]},
    )
    row = result.mappings().first()
    if row is None or row["status"] != "active":
        raise AppError(code="UNAUTHORIZED", message="平台用户不存在或已禁用", status_code=401)

    return PlatformAuthContext(
        platform_user_id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        roles=["platform_admin"],
        connection=conn,
    )


async def get_current_tenant_user(
    slug: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    conn: AsyncConnection = Depends(get_connection),
) -> TenantAuthContext:
    payload = decode_access_token(_extract_token(credentials))
    if payload.get("kind") != "tenant":
        raise AppError(code="FORBIDDEN", message="租户令牌类型不正确", status_code=403)
    if payload.get("slug") != slug:
        raise AppError(code="FORBIDDEN", message="租户 slug 与令牌不匹配", status_code=403)

    result = await conn.execute(
        text(
            """
            SELECT u.id, u.email, u.name, u.status, u.must_change_pwd, t.id AS tenant_id, t.slug, t.status AS tenant_status
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE u.id = :user_id AND t.id = :tenant_id
            """
        ),
        {"user_id": payload["sub"], "tenant_id": payload["tid"]},
    )
    row = result.mappings().first()
    if row is None or row["status"] != "active" or row["tenant_status"] != "active":
        raise AppError(code="UNAUTHORIZED", message="租户用户不存在或已禁用", status_code=401)

    role_result = await conn.execute(
        text(
            """
            SELECT role
            FROM user_roles
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            ORDER BY role
            """
        ),
        {"user_id": row["id"], "tenant_id": row["tenant_id"]},
    )
    roles = [item[0] for item in role_result.all()]
    if sorted(roles) != sorted(payload.get("roles", [])):
        raise AppError(code="UNAUTHORIZED", message="租户角色与令牌不一致", status_code=401)

    await set_current_tenant(conn, str(row["tenant_id"]))
    return TenantAuthContext(
        tenant_id=str(row["tenant_id"]),
        tenant_slug=row["slug"],
        user_id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        roles=roles,
        must_change_pwd=row["must_change_pwd"],
        connection=conn,
    )


def require_tenant_roles(*allowed_roles: str):
    async def dependency(context: TenantAuthContext = Depends(get_current_tenant_user)) -> TenantAuthContext:
        if not set(context.roles).intersection(allowed_roles):
            raise AppError(code="FORBIDDEN", message="当前角色无权访问该资源", status_code=403)
        return context

    return dependency

