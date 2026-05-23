from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.responses import success_response
from app.db.pools import get_connection
from app.schemas.auth import AdminLoginRequest, AdminMeResponse, AuthTokenResponse
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["admin-auth"])
service = AuthService()


def _set_refresh_cookie(response: JSONResponse, token: str) -> None:
    settings = get_settings()
    is_prod = settings.app_env.lower() in ("prod", "production")
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/admin/api/v1/auth",
        max_age=settings.refresh_token_expire_days * 86400,
        domain=".xinanpcb.com" if is_prod else None,
    )


@router.post("/login")
async def login(
    payload: AdminLoginRequest,
    conn: AsyncConnection = Depends(get_connection),
) -> JSONResponse:
    access_token, refresh_token = await service.platform_login(conn, payload.email, payload.password)
    response = JSONResponse(content={"data": {"access_token": access_token}})
    _set_refresh_cookie(response, refresh_token)
    return response


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
