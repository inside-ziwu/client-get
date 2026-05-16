from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin.router import router as admin_router
from app.api.internal.router import router as internal_router
from app.api.tenant.router import router as tenant_router
from app.api.webhooks.router import router as webhook_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.core.request_context import RequestContextMiddleware
from app.core.responses import success_response
from app.db.partitions import ensure_partitions
from app.db.pools import close_engines, get_engine, initialize_engines


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    initialize_engines(settings)
    await ensure_partitions(get_engine())
    yield
    await close_engines()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/health")
    async def health() -> dict:
        return success_response({"status": "ok"})

    app.include_router(admin_router, prefix="/admin/api/v1", tags=["admin"])
    app.include_router(tenant_router, prefix="/t/{slug}/api/v1", tags=["tenant"])
    app.include_router(internal_router, prefix="/internal/api/v1", tags=["internal"])
    app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
    return app


app = create_app()
