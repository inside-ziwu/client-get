import asyncio

from app.core.config import get_settings
from app.db.pools import close_engines, get_engine, initialize_engines
from app.services.collection_scheduler_service import CollectionSchedulerService


async def main() -> None:
    settings = get_settings()
    initialize_engines(settings)
    service = CollectionSchedulerService()
    async with get_engine().begin() as conn:
        result = await service.schedule_due_tasks(conn)
    await close_engines()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
