from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id


@dataclass(slots=True)
class ErrorDetail:
    field: str | None
    message: str


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int
    details: Sequence[ErrorDetail] = field(default_factory=tuple)


class CredentialExpiredError(AppError):
    def __init__(
        self,
        message: str = "凭证已过期，请重新登录并更新凭证",
        details: Sequence[ErrorDetail] = (),
    ) -> None:
        super().__init__(
            code="CREDENTIAL_EXPIRED",
            message=message,
            status_code=503,
            details=details,
        )


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Sequence[dict[str, Any]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
    )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=[{"field": detail.field, "message": detail.message} for detail in exc.details],
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return error_response(
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=detail,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="请求参数校验失败",
        details=details,
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="服务器内部错误",
        details=[{"field": None, "message": str(exc)}],
    )
