import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.core.config import Settings

_engine: AsyncEngine | None = None
_engine_loop_id: int | None = None


def initialize_engines(settings: Settings) -> None:
    global _engine, _engine_loop_id
    loop_id = id(asyncio.get_running_loop())
    if _engine is None or _engine_loop_id != loop_id:
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        _engine_loop_id = loop_id


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")
    return _engine


async def get_connection() -> AsyncIterator[AsyncConnection]:
    async with get_engine().begin() as conn:
        yield conn


async def close_engines() -> None:
    global _engine, _engine_loop_id
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _engine_loop_id = None
