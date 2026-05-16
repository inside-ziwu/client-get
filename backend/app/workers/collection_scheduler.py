from app.services.collection_scheduler_service import CollectionSchedulerService
from app.services.collection_service import CollectionService


class CollectionSchedulerWorker:
    def __init__(
        self,
        *,
        scheduler: CollectionSchedulerService | None = None,
        collection_service: CollectionService | None = None,
    ) -> None:
        self.scheduler = scheduler or CollectionSchedulerService()
        self.collection_service = collection_service or CollectionService()

    async def run_once(self, engine) -> dict:
        async with engine.begin() as conn:
            recovery = await self.collection_service.recover_expired_tasks(conn)
            scheduled = await self.scheduler.schedule_due_tasks(conn)
        return {
            "recovery": recovery,
            "scheduled_count": scheduled["scheduled_count"],
            "items": scheduled["items"],
        }
