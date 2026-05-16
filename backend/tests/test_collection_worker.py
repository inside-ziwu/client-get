from uuid import uuid4

from sqlalchemy import text

from app.core.errors import AppError
from app.integrations.collection.base import CollectionPayload, CollectionTask
from app.workers.collection import CollectionWorker
from tests.helpers import make_engine
from tests.test_collection_internal_api import prepare_collection_task


class SuccessfulRouter:
    async def collect(self, task: CollectionTask) -> CollectionPayload:
        return CollectionPayload(
            companies=[
                {
                    # new-style: routes to waimaotong_raw_companies
                    "target_table": "waimaotong_raw_companies",
                    "source_id": f"src-{task.id}",
                    "collection_type": "direct_search",
                    "name": "Worker PCB GmbH",
                    "country_iso3": "DEU",
                    "domain": "worker-pcb.example.com",
                    "industry": "PCB",
                    "raw_payload": {},
                }
            ],
        )


class FailingRouter:
    async def collect(self, task: CollectionTask) -> CollectionPayload:
        raise AppError(code="COLLECTION_PROVIDER_FAILURE", message=f"provider failed for {task.id}", status_code=502)


class EmptyMessageFailingRouter:
    async def collect(self, task: CollectionTask) -> CollectionPayload:
        raise TimeoutError()


class CapturingRouter:
    def __init__(self) -> None:
        self.task: CollectionTask | None = None

    async def collect(self, task: CollectionTask) -> CollectionPayload:
        self.task = task
        return CollectionPayload()


class FakeConnectionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def begin(self):
        return FakeConnectionContext()


class FakeCollectionService:
    async def claim_tasks(self, _conn, *, service_instance: str, limit: int, lease_seconds: int) -> dict:
        return {
            "lease_id": "lease-empty-error",
            "recovery": {"expired_count": 0, "requeued_count": 0, "failed_count": 0},
            "tasks": [
                {
                    "id": "task-empty-error",
                    "keyword": "pcb",
                    "source_types": ["lixiaoyun"],
                    "task_type": "competitor_search",
                    "context": {},
                }
            ],
        }

    async def mark_failed(
        self,
        _conn,
        *,
        task_id: str,
        lease_id: str,
        error_message: str,
        retryable: bool,
        error_code: str | None = None,
    ) -> dict:
        return {"task_id": task_id, "status": "pending", "retryable": retryable, "reason": error_message}

    async def heartbeat(self, *_args, **_kwargs) -> dict:
        return {}


class ContextFakeCollectionService(FakeCollectionService):
    async def claim_tasks(self, _conn, *, service_instance: str, limit: int, lease_seconds: int) -> dict:
        result = await super().claim_tasks(
            _conn,
            service_instance=service_instance,
            limit=limit,
            lease_seconds=lease_seconds,
        )
        result["tasks"][0]["context"] = {"max_competitors": 2}
        return result

    async def submit_result(self, *_args, **_kwargs) -> dict:
        return {"task_id": "task-empty-error", "summary": {}}


async def test_collection_worker_submits_success_result() -> None:
    slug = f"collection-worker-ok-{uuid4().hex[:8]}"
    await prepare_collection_task(slug)
    engine = make_engine()

    worker = CollectionWorker(provider_router=SuccessfulRouter())
    result = await worker.run_once(
        engine,
        service_instance="collection-worker-test",
        limit=1,
        lease_seconds=300,
        heartbeat_interval_seconds=1,
    )
    task_id = result["items"][0]["task_id"]

    async with engine.begin() as conn:
        task_row = (
            await conn.execute(
                text(
                    """
                    SELECT status, completed_at, result_summary
                    FROM collection_tasks
                    WHERE id = :task_id
                    """
                ),
                {"task_id": task_id},
            )
        ).mappings().one()
        raw_count = (
            await conn.execute(
                text("SELECT count(*) FROM waimaotong_raw_companies WHERE source_id = :source_id"),
                {"source_id": f"src-{task_id}"},
            )
        ).scalar_one()
    await engine.dispose()

    assert result["claimed_count"] == 1
    assert result["items"][0]["status"] == "completed"
    assert task_row["status"] == "completed"
    assert task_row["completed_at"] is not None
    assert task_row["result_summary"]["companies_count"] == 1
    # cleanup worker runs separately; verify raw row was written
    assert raw_count >= 1


async def test_collection_worker_marks_failed_when_provider_raises() -> None:
    slug = f"collection-worker-fail-{uuid4().hex[:8]}"
    await prepare_collection_task(slug)
    engine = make_engine()

    worker = CollectionWorker(provider_router=FailingRouter())
    result = await worker.run_once(
        engine,
        service_instance="collection-worker-test",
        limit=1,
        lease_seconds=300,
        heartbeat_interval_seconds=1,
    )
    task_id = result["items"][0]["task_id"]

    async with engine.begin() as conn:
        task_row = (
            await conn.execute(
                text(
                    """
                    SELECT status, error_message
                    FROM collection_tasks
                    WHERE id = :task_id
                    """
                ),
                {"task_id": task_id},
            )
        ).mappings().one()
    await engine.dispose()

    assert result["claimed_count"] == 1
    assert result["items"][0]["status"] == "pending"
    assert task_row["status"] == "pending"
    assert "COLLECTION_PROVIDER_FAILURE" in task_row["error_message"]


async def test_collection_worker_records_exception_type_when_message_is_empty() -> None:
    worker = CollectionWorker(
        service=FakeCollectionService(),
        provider_router=EmptyMessageFailingRouter(),
    )
    result = await worker.run_once(
        FakeEngine(),
        service_instance="collection-worker-test",
        limit=1,
        lease_seconds=300,
        heartbeat_interval_seconds=1,
    )

    assert result["items"][0]["status"] == "pending"
    assert result["items"][0]["reason"] == "TimeoutError"


async def test_collection_worker_passes_flat_context_as_provider_params() -> None:
    router = CapturingRouter()
    worker = CollectionWorker(
        service=ContextFakeCollectionService(),
        provider_router=router,
    )

    result = await worker.run_once(
        FakeEngine(),
        service_instance="collection-worker-test",
        limit=1,
        lease_seconds=300,
        heartbeat_interval_seconds=1,
    )

    assert result["items"][0]["status"] == "completed"
    assert router.task is not None
    assert router.task.params == {"max_competitors": 2}
