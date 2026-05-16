from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import text

from app.core.responses import success_response
from app.db.pools import get_connection
from app.schemas.auth import (
    AuthTokenResponse,
    ChangePasswordRequest,
    TenantLoginRequest,
    TenantMeResponse,
)
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["tenant-auth"])
service = AuthService()


@router.post("/login")
async def login(
    slug: str,
    payload: TenantLoginRequest,
    conn: AsyncConnection = Depends(get_connection),
) -> dict:
    token = await service.tenant_login(conn, slug, payload.email, payload.password)
    return success_response(AuthTokenResponse(access_token=token).model_dump())


@router.get("/me")
async def me(context: TenantAuthContext = Depends(get_current_tenant_user)) -> dict:
    tenant_row = await context.connection.execute(
        text(
            """
        SELECT needs_onboarding
        FROM tenants
        WHERE id = :tenant_id
        """
        ),
        {"tenant_id": context.tenant_id},
    )
    needs_onboarding = tenant_row.scalar_one()
    return success_response(
        TenantMeResponse(
            id=context.user_id,
            tenant_id=context.tenant_id,
            slug=context.tenant_slug,
            email=context.email,
            name=context.name,
            roles=context.roles,
            needs_onboarding=needs_onboarding,
            must_change_pwd=context.must_change_pwd,
        ).model_dump()
    )


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    await service.change_password(
        context.connection,
        user_id=context.user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return success_response({"changed": True})
