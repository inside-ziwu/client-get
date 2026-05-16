from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.security.jwt import decode_access_token

http_bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class ServiceAuthContext:
    subject: str
    service_name: str
    scopes: list[str]


def _extract_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(code="UNAUTHORIZED", message="缺少服务授权令牌", status_code=401)
    return credentials.credentials


def require_service_scopes(*required_scopes: str):
    async def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
        service_name_header: str | None = Header(default=None, alias="X-Service-Name"),
    ) -> ServiceAuthContext:
        payload = decode_access_token(_extract_token(credentials))
        if payload.get("kind") != "service":
            raise AppError(code="FORBIDDEN", message="服务令牌类型不正确", status_code=403)
        service_name = payload.get("service_name")
        if not service_name or service_name_header != service_name:
            raise AppError(code="FORBIDDEN", message="服务名校验失败", status_code=403)
        scopes = payload.get("scopes", [])
        if not set(required_scopes).issubset(set(scopes)):
            raise AppError(code="FORBIDDEN", message="服务 scope 不足", status_code=403)
        return ServiceAuthContext(
            subject=payload["sub"],
            service_name=service_name,
            scopes=scopes,
        )

    return dependency

