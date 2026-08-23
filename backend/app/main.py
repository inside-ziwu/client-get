import asyncio
from contextlib import asynccontextmanager, suppress

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
from app.workers.industry_news_fetch import run_industry_news_fetch_loop
from app.workers.wmt_lineage_repair import run_wmt_lineage_repair_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    initialize_engines(settings)
    engine = get_engine()
    await ensure_partitions(engine)
    repair_stop_event: asyncio.Event | None = None
    repair_task: asyncio.Task | None = None
    if settings.wmt_lineage_repair_enabled:
        repair_stop_event = asyncio.Event()
        repair_task = asyncio.create_task(
            run_wmt_lineage_repair_loop(
                engine,
                interval_seconds=settings.wmt_lineage_repair_interval_seconds,
                stop_event=repair_stop_event,
            )
        )
    news_stop_event: asyncio.Event | None = None
    news_task: asyncio.Task | None = None
    if settings.industry_news_fetch_enabled:
        news_stop_event = asyncio.Event()
        news_task = asyncio.create_task(
            run_industry_news_fetch_loop(
                engine,
                stop_event=news_stop_event,
            )
        )
    try:
        yield
    finally:
        if repair_stop_event is not None:
            repair_stop_event.set()
        if repair_task is not None:
            repair_task.cancel()
            with suppress(asyncio.CancelledError):
                await repair_task
        if news_stop_event is not None:
            news_stop_event.set()
        if news_task is not None:
            news_task.cancel()
            with suppress(asyncio.CancelledError):
                await news_task
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

    @app.get("/")
    async def root_health() -> dict:
        # Sealos 探活/负载均衡周期性请求根路径,返回 200 消除日志里的 404 噪音
        return {"status": "ok"}

    app.include_router(admin_router, prefix="/admin/api/v1", tags=["admin"])
    app.include_router(tenant_router, prefix="/t/{slug}/api/v1", tags=["tenant"])
    app.include_router(internal_router, prefix="/internal/api/v1", tags=["internal"])
    app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
    return app


app = create_app()
