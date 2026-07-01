"""邮件发送 Worker。"""

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.integrations.engagelab import EngageLabClient, EngageLabSendError
from app.services.tenant_messaging_service import TenantMessagingService

logger = logging.getLogger(__name__)


class SendingWorker:
    def __init__(
        self,
        *,
        service: TenantMessagingService | None = None,
        provider: EngageLabClient | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        random_between: Callable[[float, float], float] | None = None,
        log_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.service = service or TenantMessagingService()
        self.provider = provider or EngageLabClient()
        self.clock = clock or (lambda: datetime.now(UTC))
        self.sleep = sleep or asyncio.sleep
        self.random_between = random_between or random.uniform
        self.log_sink = log_sink
        self.domain_clocks: dict[str, datetime] = {}
        self._stale_locks_recovered = False

    async def run_once(
        self,
        engine,
        *,
        service_instance: str,
        idle_poll_seconds: int = 5,
    ) -> dict:
        """执行一轮发送任务：发现域名、选择一个到期域名、领取并发送一封。"""
        if not self._stale_locks_recovered:
            async with engine.begin() as conn:
                recovered = await self.service.recover_stale_locks(conn)
            self._stale_locks_recovered = True
            if recovered["recovered_count"]:
                self._log(
                    {
                        "event": "stale_lock_recovered",
                        "count": recovered["recovered_count"],
                        "enrollment_ids": recovered["enrollment_ids"],
                    }
                )

        async with engine.begin() as conn:
            domain_ids = await self.service.list_running_domain_ids(conn)

        now = self._now()
        active_domains = set(domain_ids)
        self.domain_clocks = {
            domain_id: clock_at
            for domain_id, clock_at in self.domain_clocks.items()
            if domain_id in active_domains
        }
        for domain_id in domain_ids:
            self.domain_clocks.setdefault(domain_id, now)

        if not domain_ids:
            self._log({"event": "no_running_domains"})
            if idle_poll_seconds > 0:
                await self.sleep(idle_poll_seconds)
            return {"claimed_count": 0, "processed_count": 0, "items": []}

        selected_domain = self._select_due_domain(domain_ids, now)
        if selected_domain is None:
            earliest_domain = min(domain_ids, key=lambda item: self.domain_clocks[item])
            sleep_seconds = min(
                max((self.domain_clocks[earliest_domain] - now).total_seconds(), 0),
                idle_poll_seconds,
            )
            self._log(
                {
                    "event": "throttle_sleep",
                    "domain_id": earliest_domain,
                    "sleep_seconds": round(sleep_seconds, 3),
                }
            )
            if sleep_seconds > 0:
                await self.sleep(sleep_seconds)
            return {"claimed_count": 0, "processed_count": 0, "items": []}

        async with engine.begin() as conn:
            timezone_config = await self.service.load_timezone_config(conn)
            claimed = await self.service.claim_due_emails(
                conn,
                service_instance=service_instance,
                limit=1,
                domain_id=selected_domain,
                timezone_config=timezone_config,
            )

        processed = []
        for item in claimed["items"]:
            started_at = self._now()
            try:
                provider_result = await self.provider.send_email(
                    {
                        "from_email": item["from_email"],
                        "from_name": item.get("from_name"),
                        "to_email": item["to_email"],
                        "to_name": item.get("to_name"),
                        "subject": item["subject"],
                        "body_html": item["body_html"],
                        "body_text": item.get("body_text"),
                        "idempotency_key": f"{item['enrollment_id']}:{item['step_id']}",
                    }
                )
                async with engine.begin() as conn:
                    result = await self.service.mark_email_sent(
                        conn,
                        email_id=item["email_id"],
                        payload={"engagelab_message_id": provider_result["engagelab_message_id"]},
                    )
                processed.append(result | {"provider_status": "sent"})
                self._log(
                    {
                        "event": "send_ok",
                        "domain_id": item["domain_id"],
                        "email_id": item["email_id"],
                        "elapsed_ms": self._elapsed_ms(started_at),
                    }
                )

            except EngageLabSendError as exc:
                classification = self._classify_provider_error(exc.status_code)
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "reason": str(exc),
                            "error_code": "ENGAGELAB_ERROR",
                            "error_message": str(exc),
                            "status_code": exc.status_code,
                            "is_permanent": classification["is_permanent"],
                            "error_category": classification["error_category"],
                            "domain_id": item["domain_id"],
                        },
                    )
                processed.append(result | {"provider_status": "failed"})
                self._log(
                    {
                        "event": "send_failed",
                        "domain_id": item["domain_id"],
                        "email_id": item["email_id"],
                        "error_type": classification["error_type"],
                        "status_code": exc.status_code,
                        "attempt": result.get("send_attempt_count"),
                        "elapsed_ms": self._elapsed_ms(started_at),
                    }
                )

            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "reason": str(exc),
                            "error_code": "UNKNOWN_ERROR",
                            "error_message": str(exc),
                            "is_permanent": False,
                            "domain_id": item["domain_id"],
                        },
                    )
                processed.append(result | {"provider_status": "failed"})
                self._log(
                    {
                        "event": "send_failed",
                        "domain_id": item["domain_id"],
                        "email_id": item["email_id"],
                        "error_type": "temporary",
                        "status_code": None,
                        "attempt": result.get("send_attempt_count"),
                        "elapsed_ms": self._elapsed_ms(started_at),
                    }
                )

            except Exception as exc:  # pragma: no cover - 未知异常保守走临时重试
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "reason": str(exc),
                            "error_code": "UNKNOWN_ERROR",
                            "error_message": str(exc),
                            "is_permanent": False,
                            "domain_id": item["domain_id"],
                        },
                    )
                processed.append(result | {"provider_status": "failed"})
                self._log(
                    {
                        "event": "send_failed",
                        "domain_id": item["domain_id"],
                        "email_id": item["email_id"],
                        "error_type": "temporary",
                        "status_code": None,
                        "attempt": result.get("send_attempt_count"),
                        "elapsed_ms": self._elapsed_ms(started_at),
                    }
                )

            finally:
                self.domain_clocks[selected_domain] = self._now() + timedelta(
                    seconds=self._delay_seconds(item.get("send_strategy"))
                )

        if not claimed["items"]:
            self.domain_clocks[selected_domain] = self._now() + timedelta(
                seconds=idle_poll_seconds
            )
            self._log(
                {
                    "event": "domain_idle",
                    "domain_id": selected_domain,
                    "sleep_seconds": idle_poll_seconds,
                }
            )

        return {
            "claimed_count": len(claimed["items"]),
            "processed_count": len(processed),
            "items": processed,
        }

    def _select_due_domain(self, domain_ids: list[str], now: datetime) -> str | None:
        due_domains = [
            domain_id
            for domain_id in domain_ids
            if self.domain_clocks.get(domain_id, now) <= now
        ]
        if not due_domains:
            return None
        return min(due_domains, key=lambda item: self.domain_clocks[item])

    def _delay_seconds(self, send_strategy: dict | None) -> float:
        interval = (send_strategy or {}).get("interval_seconds") or [1, 1]
        if not isinstance(interval, list | tuple) or len(interval) != 2:
            interval = [1, 1]
        low = max(float(interval[0]), 0)
        high = max(float(interval[1]), low)
        return self.random_between(low, high)

    def _classify_provider_error(self, status_code: int | None) -> dict[str, Any]:
        if status_code is None:
            return {"is_permanent": False, "error_type": "temporary", "error_category": None}
        if status_code in {401, 403, 429} or status_code >= 500:
            return {"is_permanent": False, "error_type": "temporary", "error_category": None}
        if status_code == 422:
            return {"is_permanent": True, "error_type": "permanent", "error_category": "invalid"}
        if 400 <= status_code < 500:
            return {"is_permanent": True, "error_type": "permanent", "error_category": None}
        return {"is_permanent": False, "error_type": "temporary", "error_category": None}

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _elapsed_ms(self, started_at: datetime) -> int:
        return int((self._now() - started_at).total_seconds() * 1000)

    def _log(self, record: dict[str, Any]) -> None:
        if self.log_sink:
            self.log_sink(record)
            return
        logger.info(json.dumps(record, ensure_ascii=False, default=str))
