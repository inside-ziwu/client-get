"""CleanupWorker — 消费 cleanup_queue，将 raw 数据写入 clean_companies / tenant_companies。

使用方式：
    uv run python scripts/run_cleanup_worker.py --once     # 单次处理一批
    uv run python scripts/run_cleanup_worker.py            # 持续轮询
"""

import asyncio
import logging

from app.services.cleanup_service import CleanupService

logger = logging.getLogger(__name__)


class CleanupWorker:
    """封装 CleanupService 的 worker loop，供脚本和测试使用。"""

    def __init__(self, *, service: CleanupService | None = None) -> None:
        self.service = service or CleanupService()

    async def run_once(
        self,
        engine,
        *,
        service_instance: str = "cleanup-worker-1",
        batch_size: int = 100,
    ) -> dict:
        """处理一批 pending 条目并返回统计。"""
        async with engine.begin() as conn:
            recovered = await self.service.recover_stuck(conn)
            processed = await self.service.process_one_batch(conn, batch_size=batch_size)
        return {
            "service_instance": service_instance,
            "recovered": recovered,
            "processed": processed,
        }

    async def run_loop(
        self,
        engine,
        *,
        service_instance: str = "cleanup-worker-1",
        batch_size: int = 100,
        sleep_seconds: float = 2.0,
        reset_interval_seconds: float = 300.0,
    ) -> None:
        """持续轮询 cleanup_queue。"""
        last_reset = asyncio.get_event_loop().time()
        while True:
            try:
                async with engine.begin() as conn:
                    processed = await self.service.process_one_batch(conn, batch_size=batch_size)

                if processed == 0:
                    await asyncio.sleep(sleep_seconds)
                else:
                    logger.info(
                        "cleanup worker [%s]: processed=%d", service_instance, processed
                    )
            except Exception as exc:
                logger.error("cleanup worker [%s]: loop error: %s", service_instance, exc)
                await asyncio.sleep(sleep_seconds)

            now = asyncio.get_event_loop().time()
            if now - last_reset >= reset_interval_seconds:
                try:
                    async with engine.begin() as conn:
                        recovered = await self.service.recover_stuck(conn)
                        if recovered:
                            logger.info(
                                "cleanup worker [%s]: recovered %d stuck entries",
                                service_instance, recovered,
                            )
                    last_reset = now
                except Exception as exc:
                    logger.warning(
                        "cleanup worker [%s]: recover error: %s", service_instance, exc
                    )
