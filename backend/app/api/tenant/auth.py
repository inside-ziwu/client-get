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
    UpdateTestEmailRequest,
)
from app.security.dependencies import TenantAuthContext, get_current_tenant_user
from app.services.auth_service import AuthService
from app.services.tenant_team_service import TenantTeamService

router = APIRouter(prefix="/auth", tags=["tenant-auth"])
service = AuthService()
team_service = TenantTeamService()


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
        SELECT needs_onboarding, name
        FROM tenants
        WHERE id = :tenant_id
        """
        ),
        {"tenant_id": context.tenant_id},
    )
    row = tenant_row.mappings().first()
    return success_response(
        TenantMeResponse(
            id=context.user_id,
            tenant_id=context.tenant_id,
            slug=context.tenant_slug,
            email=context.email,
            name=context.name,
            roles=context.roles,
            needs_onboarding=row["needs_onboarding"],
            must_change_pwd=context.must_change_pwd,
            tenant_name=row["name"],
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


@router.patch("/me/test-email")
async def update_test_email(
    payload: UpdateTestEmailRequest,
    context: TenantAuthContext = Depends(get_current_tenant_user),
) -> dict:
    await team_service.update_test_email(context.connection, context.user_id, payload.test_email)
    return success_response({"test_email": payload.test_email})
