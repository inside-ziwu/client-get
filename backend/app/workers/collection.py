import asyncio
from contextlib import suppress

from app.core.errors import AppError
from app.integrations.collection.base import CollectionTask
from app.integrations.collection.router import CollectionProviderRouter
from app.services.collection_service import CollectionService


class CollectionWorker:
    def __init__(
        self,
        *,
        service: CollectionService | None = None,
        provider_router: CollectionProviderRouter | None = None,
    ) -> None:
        self.service = service or CollectionService()
        self.provider_router = provider_router or CollectionProviderRouter()

    async def run_once(
        self,
        engine,
        *,
        service_instance: str,
        limit: int = 20,
        lease_seconds: int = 300,
        heartbeat_interval_seconds: int = 30,
    ) -> dict:
        async with engine.begin() as conn:
            claimed = await self.service.claim_tasks(
                conn,
                service_instance=service_instance,
                limit=limit,
                lease_seconds=lease_seconds,
            )

        processed = []
        for item in claimed["tasks"]:
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(
                    engine,
                    task_id=item["id"],
                    lease_id=claimed["lease_id"],
                    lease_seconds=lease_seconds,
                    heartbeat_interval_seconds=heartbeat_interval_seconds,
                )
            )
            try:
                on_partial = None
                on_company_enriched = None
                if "lixiaoyun" in (item.get("source_types") or []):
                    task_id_cap = item["id"]
                    svc = self.service

                    async def _on_partial(basic_competitors: list[dict]) -> None:
                        async with engine.begin() as _conn:
                            await svc.save_competitors_partial(
                                _conn, task_id=task_id_cap, competitors=basic_competitors,
                            )

                    async def _on_company_enriched(competitor: dict) -> None:
                        async with engine.begin() as _conn:
                            await svc.save_competitor_enriched(
                                _conn, task_id=task_id_cap, competitor=competitor,
                            )

                    on_partial = _on_partial
                    on_company_enriched = _on_company_enriched

                task = CollectionTask(
                    id=item["id"],
                    keyword=item["keyword"],
                    source_types=item["source_types"],
                    task_type=item.get("task_type", "competitor_search"),
                    competitor_names=item.get("context", {}).get("competitor_names", []),
                    params=item.get("context", {}).get("params") or item.get("context", {}),
                    on_partial=on_partial,
                    on_company_enriched=on_company_enriched,
                )
                payload = await self.provider_router.collect(task)
                async with engine.begin() as conn:
                    result = await self.service.submit_result(
                        conn,
                        task_id=item["id"],
                        lease_id=claimed["lease_id"],
                        companies=payload.companies,
                        contacts=payload.contacts,
                        competitors=payload.competitors,
                        cursor=payload.cursor,
                        skip_source_ids=payload.skip_source_ids,
                        request_id=f"collection-worker:{item['id']}:{claimed['lease_id']}",
                        service_name="collection-service",
                    )
                processed.append(result | {"status": "completed"})
            except AppError as exc:
                async with engine.begin() as conn:
                    result = await self.service.mark_failed(
                        conn,
                        task_id=item["id"],
                        lease_id=claimed["lease_id"],
                        error_code=exc.code,
                        error_message=exc.message,
                        retryable=exc.code not in {"NOT_FOUND", "VALIDATION_ERROR", "LEASE_INVALID"},
                    )
                processed.append(result)
            except Exception as exc:  # pragma: no cover - defensive fallback
                error_message = str(exc) or exc.__class__.__name__
                async with engine.begin() as conn:
                    result = await self.service.mark_failed(
                        conn,
                        task_id=item["id"],
                        lease_id=claimed["lease_id"],
                        error_message=error_message,
                        retryable=True,
                    )
                processed.append(result)
            finally:
                heartbeat_task.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat_task

        return {
            "claimed_count": len(claimed["tasks"]),
            "processed_count": len(processed),
            "recovery": claimed["recovery"],
            "items": processed,
        }

    async def _heartbeat_loop(
        self,
        engine,
        *,
        task_id: str,
        lease_id: str,
        lease_seconds: int,
        heartbeat_interval_seconds: int,
    ) -> None:
        while True:
            await asyncio.sleep(heartbeat_interval_seconds)
            async with engine.begin() as conn:
                await self.service.heartbeat(
                    conn,
                    task_id=task_id,
                    lease_id=lease_id,
                    lease_seconds=lease_seconds,
                )
