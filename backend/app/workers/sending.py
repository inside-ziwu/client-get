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
from app.utils.beijing_time import beijing_day_bounds

logger = logging.getLogger(__name__)


QUOTA_KEYWORDS = (
    "balance is not enough",
    "recharge soon",
    '"code": 30877',
    '"code":30877',
    "code 30877",
    "daily quota",
    "quota exceeded",
    "配额",
    "余额不足",
    "已达上限",
)
QUOTA_STATUS_CODES: frozenset[int] = frozenset()
RATE_LIMIT_SIGNALS = ("rate limit", "too many requests")


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
        self.domain_quota_paused: dict[str, datetime] = {}
        self.domain_rate_limit_hits: dict[str, list[datetime]] = {}
        self.enrollment_quota_defer_counts: dict[str, int] = {}
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
        self._prune_quota_state(now, active_domains)
        for domain_id in domain_ids:
            self.domain_clocks.setdefault(domain_id, now)

        if not domain_ids:
            self._log({"event": "no_running_domains"})
            if idle_poll_seconds > 0:
                await self.sleep(idle_poll_seconds)
            return {"claimed_count": 0, "processed_count": 0, "items": []}

        available_domain_ids = self._available_domain_ids(domain_ids, now)
        if not available_domain_ids:
            self._log(
                {
                    "event": "all_domains_quota_paused",
                    "domain_ids": domain_ids,
                    "sleep_seconds": idle_poll_seconds,
                }
            )
            if idle_poll_seconds > 0:
                await self.sleep(idle_poll_seconds)
            return {"claimed_count": 0, "processed_count": 0, "items": []}

        selected_domain = self._select_due_domain(available_domain_ids, now)
        if selected_domain is None:
            earliest_domain = min(available_domain_ids, key=lambda item: self.domain_clocks[item])
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
                self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
                self._log(
                    {
                        "event": "send_ok",
                        "domain_id": item["domain_id"],
                        "email_id": item["email_id"],
                        "elapsed_ms": self._elapsed_ms(started_at),
                    }
                )

            except EngageLabSendError as exc:
                classification = self._classify_provider_error(exc.status_code, str(exc))
                if (
                    classification["error_type"] == "rate_limit"
                    and self._record_rate_limit_hit(item["domain_id"], self._now()) >= 3
                ):
                    classification = {
                        "is_permanent": False,
                        "error_type": "quota",
                        "error_category": "quota",
                    }
                if classification["error_type"] == "quota":
                    if self.enrollment_quota_defer_counts.get(item["enrollment_id"], 0) < 3:
                        paused_until = self._open_quota_circuit(item=item, exc=exc)
                        outcome = await self._defer_for_quota(
                            engine,
                            item=item,
                            exc=exc,
                            paused_until=paused_until,
                        )
                        result = outcome["result"]
                        if outcome["deferred"]:
                            processed.append(result | {"provider_status": "quota_deferred"})
                            continue
                        processed.append(result | {"provider_status": "failed"})
                        if result.get("status") == "failed":
                            self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
                        self._log(
                            {
                                "event": "send_failed",
                                "domain_id": item["domain_id"],
                                "email_id": item["email_id"],
                                "error_type": "quota",
                                "status_code": exc.status_code,
                                "attempt": result.get("send_attempt_count"),
                                "elapsed_ms": self._elapsed_ms(started_at),
                            }
                        )
                        continue
                    # 连续配额失败日的计数只被成功发送中断；同进程跨 3 个北京日后降级为临时失败，
                    # 且不熔断域名——毒药防护：若关键词误判了永久性错误，熔断会让单封邮件
                    # 连续多日封锁整域；真实额度耗尽时下一封 count<3 的邮件会立即重新熔断。
                    self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
                    classification = {
                        "is_permanent": False,
                        "error_type": "temporary",
                        "error_category": classification["error_category"],
                    }
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
                if classification["is_permanent"] or result.get("status") == "failed":
                    self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
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
            self.domain_clocks[selected_domain] = self._now() + timedelta(seconds=idle_poll_seconds)
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
            domain_id for domain_id in domain_ids if self.domain_clocks.get(domain_id, now) <= now
        ]
        if not due_domains:
            return None
        return min(due_domains, key=lambda item: self.domain_clocks[item])

    def _available_domain_ids(self, domain_ids: list[str], now: datetime) -> list[str]:
        available = []
        for domain_id in domain_ids:
            paused_until = self.domain_quota_paused.get(domain_id)
            if paused_until is None:
                available.append(domain_id)
                continue
            if now < paused_until:
                continue
            self.domain_quota_paused.pop(domain_id, None)
            self._log(
                {
                    "event": "quota_circuit_closed",
                    "domain_id": domain_id,
                    "paused_until": paused_until,
                }
            )
            available.append(domain_id)
        return available

    async def _defer_for_quota(
        self, engine, *, item: dict, exc: EngageLabSendError, paused_until: datetime
    ) -> dict:
        now = self._now()
        try:
            async with engine.begin() as conn:
                result = await self.service.defer_email_for_quota(
                    conn,
                    email_id=item["email_id"],
                    resume_at=paused_until,
                    now_utc=now,
                )
        except Exception as defer_exc:
            self._log(
                {
                    "event": "quota_defer_failed",
                    "domain_id": item["domain_id"],
                    "email_id": item["email_id"],
                    "error": str(defer_exc),
                }
            )
            try:
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "reason": str(exc),
                            "error_code": "ENGAGELAB_ERROR",
                            "error_message": str(exc),
                            "status_code": exc.status_code,
                            "is_permanent": False,
                            "error_category": "quota",
                            "domain_id": item["domain_id"],
                        },
                    )
            except Exception as fallback_exc:
                self._log(
                    {
                        "event": "quota_defer_fallback_failed",
                        "domain_id": item["domain_id"],
                        "email_id": item["email_id"],
                        "defer_error": str(defer_exc),
                        "fallback_error": str(fallback_exc),
                    }
                )
                return {
                    "deferred": False,
                    "result": {
                        "email_id": item["email_id"],
                        "status": "quota_defer_fallback_failed",
                        "reason": str(exc),
                    },
                }
            return {"deferred": False, "result": result}

        self.enrollment_quota_defer_counts[item["enrollment_id"]] = (
            self.enrollment_quota_defer_counts.get(item["enrollment_id"], 0) + 1
        )
        return {"deferred": True, "result": result}

    def _open_quota_circuit(self, *, item: dict, exc: Exception) -> datetime:
        paused_until = self._next_beijing_midnight(self._now())
        self.domain_quota_paused[item["domain_id"]] = paused_until
        self._log(
            {
                "event": "quota_circuit_open",
                "domain_id": item["domain_id"],
                "email_id": item["email_id"],
                "paused_until": paused_until,
                "error": str(exc),
            }
        )
        return paused_until

    def _prune_quota_state(self, now: datetime, active_domains: set[str]) -> None:
        for domain_id, paused_until in list(self.domain_quota_paused.items()):
            if paused_until <= now and domain_id not in active_domains:
                self.domain_quota_paused.pop(domain_id, None)
        cutoff = now - timedelta(minutes=10)
        self.domain_rate_limit_hits = {
            domain_id: [hit for hit in hits if hit >= cutoff]
            for domain_id, hits in self.domain_rate_limit_hits.items()
            if any(hit >= cutoff for hit in hits)
        }

    def _record_rate_limit_hit(self, domain_id: str, now: datetime) -> int:
        cutoff = now - timedelta(minutes=10)
        hits = [hit for hit in self.domain_rate_limit_hits.get(domain_id, []) if hit >= cutoff]
        hits.append(now)
        self.domain_rate_limit_hits[domain_id] = hits
        return len(hits)

    def _next_beijing_midnight(self, now: datetime) -> datetime:
        _, tomorrow = beijing_day_bounds(now)
        return tomorrow.astimezone(UTC)

    def _delay_seconds(self, send_strategy: dict | None) -> float:
        interval = (send_strategy or {}).get("interval_seconds") or [1, 1]
        if not isinstance(interval, list | tuple) or len(interval) != 2:
            interval = [1, 1]
        low = max(float(interval[0]), 0)
        high = max(float(interval[1]), low)
        return self.random_between(low, high)

    def _classify_provider_error(
        self, status_code: int | None, error_message: str | None = None
    ) -> dict[str, Any]:
        normalized_message = (error_message or "").casefold()
        is_client_error = status_code is not None and 400 <= status_code < 500
        if is_client_error and any(
            keyword.casefold() in normalized_message for keyword in QUOTA_KEYWORDS
        ):
            return {"is_permanent": False, "error_type": "quota", "error_category": "quota"}
        if status_code in QUOTA_STATUS_CODES:
            return {"is_permanent": False, "error_type": "quota", "error_category": "quota"}
        if status_code == 429 or (
            is_client_error and any(signal in normalized_message for signal in RATE_LIMIT_SIGNALS)
        ):
            return {"is_permanent": False, "error_type": "rate_limit", "error_category": None}
        if status_code is None:
            return {"is_permanent": False, "error_type": "temporary", "error_category": None}
        if status_code in {401, 403} or status_code >= 500:
            return {"is_permanent": False, "error_type": "temporary", "error_category": None}
        if status_code == 422:
            return {"is_permanent": True, "error_type": "permanent", "error_category": "invalid"}
        if 400 <= status_code < 500:
            return {"is_permanent": False, "error_type": "temporary", "error_category": None}
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
