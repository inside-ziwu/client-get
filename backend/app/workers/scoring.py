from app.core.errors import AppError
from app.services.scoring_service import ScoringService


class ScoringWorker:
    def __init__(self, *, service: ScoringService | None = None) -> None:
        self.service = service or ScoringService()

    async def run_once(
        self,
        engine,
        *,
        service_instance: str,
        limit: int = 20,
        lease_seconds: int = 300,
    ) -> dict:
        async with engine.begin() as conn:
            claimed = await self.service.claim_jobs(
                conn,
                service_instance=service_instance,
                limit=limit,
                lease_seconds=lease_seconds,
            )

        processed = []
        for item in claimed["items"]:
            try:
                async with engine.begin() as conn:
                    prepared = await self.service.prepare_score_result(
                        conn,
                        tenant_company_id=item["tenant_company_id"],
                    )
                    result = await self.service.submit_job_result(
                        conn,
                        job_id=item["job_id"],
                        lease_id=item["lease_id"],
                        score_result=prepared,
                    )
                processed.append(result)
            except AppError as exc:
                async with engine.begin() as conn:
                    result = await self.service.submit_job_result(
                        conn,
                        job_id=item["job_id"],
                        lease_id=item["lease_id"],
                        error=exc.message,
                        retryable=exc.code not in {"NOT_FOUND", "VALIDATION_ERROR", "LEASE_INVALID"},
                    )
                processed.append(result)
            except Exception as exc:  # pragma: no cover - defensive fallback
                async with engine.begin() as conn:
                    result = await self.service.submit_job_result(
                        conn,
                        job_id=item["job_id"],
                        lease_id=item["lease_id"],
                        error=str(exc),
                        retryable=True,
                    )
                processed.append(result)

        return {
            "claimed_count": len(claimed["items"]),
            "processed_count": len(processed),
            "items": processed,
        }
