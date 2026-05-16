from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.pools import get_engine


async def transaction() -> AsyncIterator[AsyncConnection]:
    async with get_engine().begin() as conn:
        yield conn

