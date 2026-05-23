from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.responses import success_response
from app.db.pools import get_connection
from app.schemas.auth import AdminLoginRequest, AdminMeResponse
from app.security.dependencies import PlatformAuthContext, get_current_platform_user
from app.security.jwt import create_access_token, decode_refresh_token
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


def _delete_refresh_cookie(response: JSONResponse) -> None:
    settings = get_settings()
    is_prod = settings.app_env.lower() in ("prod", "production")
    response.delete_cookie(
        key="refresh_token",
        path="/admin/api/v1/auth",
        domain=".xinanpcb.com" if is_prod else None,
    )


@router.post("/refresh")
async def refresh(
    request: Request,
    conn: AsyncConnection = Depends(get_connection),
) -> JSONResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise AppError(code="UNAUTHORIZED", message="缺少刷新令牌", status_code=401)
    payload = decode_refresh_token(token)
    result = await conn.execute(
        text("SELECT status FROM platform_users WHERE id = :user_id"),
        {"user_id": payload["sub"]},
    )
    user = result.mappings().first()
    if not user or user["status"] != "active":
        raise AppError(code="UNAUTHORIZED", message="用户不可用", status_code=401)
    new_access_token = create_access_token({
        "sub": payload["sub"],
        "kind": payload["kind"],
        "roles": payload.get("roles", []),
    })
    return JSONResponse(content={"data": {"access_token": new_access_token}})


@router.post("/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(content={"data": {"ok": True}})
    _delete_refresh_cookie(response)
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
