from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.responses import success_response
from app.db.pools import get_connection
from app.schemas.auth import AdminLoginRequest, AdminMeResponse, AuthTokenResponse
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["admin-auth"])
service = AuthService()


@router.post("/login")
async def login(
    payload: AdminLoginRequest,
    conn: AsyncConnection = Depends(get_connection),
) -> dict:
    token = await service.platform_login(conn, payload.email, payload.password)
    return success_response(AuthTokenResponse(access_token=token).model_dump())


@router.get("/me")
async def me(context: PlatformAuthContext = Depends(get_current_platform_user)) -> dict:
    return success_response(
        AdminMeResponse(
            id=context.platform_user_id,
            email=context.email,
            name=context.name,
            roles=context.roles,
        ).model_dump()
    )

