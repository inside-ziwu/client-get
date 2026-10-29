"""邮件发送 Worker。"""

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError
from app.integrations.engagelab import EngageLabClient, EngageLabSendError, classify_send_error
from app.services.tenant_messaging_service import TenantMessagingService
from app.utils.beijing_time import beijing_day_bounds

logger = logging.getLogger(__name__)

RECEIPT_RETRY_DELAYS = (1, 5, 30)
PENDING_FINALIZE_LIMIT = 20
PENDING_FINALIZE_LEASE = timedelta(seconds=15)
PENDING_FINALIZE_BACKOFF = timedelta(seconds=60)
UNSENT_LOCK_STALE_MINUTES = 30
UNSENT_LOCK_RECOVERY_INTERVAL = timedelta(seconds=60)

_SAFE_LOG_KEYS = frozenset(
    {
        "event",
        "instance_id",
        "tenant_id",
        "domain_id",
        "email_id",
        "phase",
        "http_status",
        "provider_code",
        "error_class",
        "decision",
        "resume_at",
        "message_id_length",
        "count",
        "enrollment_ids",
        "isolated_count",
        "sleep_seconds",
        "domain_ids",
        "paused_until",
        "elapsed_ms",
        "finalized_count",
        "attempt",
    }
)
_PUBLIC_ITEM_KEYS = frozenset(
    {
        "email_id",
        "status",
        "provider_status",
        "duplicate",
        "send_attempt_count",
        "retry_seconds",
        "resume_at",
        "error_class",
        "decision",
        "provider_code",
        "http_status",
        "message_id_length",
    }
)


def sanitize_round_result(result: dict) -> dict:
    """轮次输出只留安全字段。reason / 回执原文 / SQL 不得进入 print。"""
    items = []
    for item in result.get("items") or []:
        if not isinstance(item, dict):
            continue
        items.append({key: item[key] for key in _PUBLIC_ITEM_KEYS if key in item})
    return {
        "claimed_count": result.get("claimed_count", 0),
        "processed_count": result.get("processed_count", 0),
        "finalized_count": result.get("finalized_count", 0),
        "items": items,
    }


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
        self._next_unsent_recovery_at: datetime | None = None

    async def run_once(
        self,
        engine,
        *,
        service_instance: str,
        idle_poll_seconds: int = 5,
    ) -> dict:
        """执行一轮：先本地恢复，再按域名领取并发送一封。"""
        if not self._stale_locks_recovered:
            async with engine.begin() as conn:
                recovered = await self.service.recover_stale_locks(conn)
            self._stale_locks_recovered = True
            if recovered["recovered_count"] or recovered.get("isolated_count"):
                self._log(
                    {
                        "event": "stale_lock_recovered",
                        "count": recovered["recovered_count"],
                        "isolated_count": recovered.get("isolated_count", 0),
                        "enrollment_ids": recovered["enrollment_ids"],
                    }
                )

        try:
            async with engine.begin() as conn:
                isolated = await self.service.isolate_timed_out_dispatches(conn)
            if isolated.get("isolated_count"):
                self._log(
                    {
                        "event": "send_outcome_uncertain",
                        "phase": "dispatch_timeout",
                        "error_class": "outcome_uncertain",
                        "decision": "isolate",
                        "count": isolated["isolated_count"],
                    }
                )
        except Exception:
            self._log(
                {
                    "event": "send_finalize_failed",
                    "phase": "dispatch_timeout",
                    "error_class": "internal_finalize",
                    "decision": "isolate",
                }
            )

        await self._release_unsent_locks_if_due(engine)
        finalized_count = await self._finalize_pending(engine)

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
            return sanitize_round_result(
                {
                    "claimed_count": 0,
                    "processed_count": 0,
                    "finalized_count": finalized_count,
                    "items": [],
                }
            )

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
            return sanitize_round_result(
                {
                    "claimed_count": 0,
                    "processed_count": 0,
                    "finalized_count": finalized_count,
                    "items": [],
                }
            )

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
            return sanitize_round_result(
                {
                    "claimed_count": 0,
                    "processed_count": 0,
                    "finalized_count": finalized_count,
                    "items": [],
                }
            )

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
                try:
                    async with engine.begin() as conn:
                        dispatch = await self.service.begin_dispatch(
                            conn,
                            email_id=item["email_id"],
                            tenant_id=item["tenant_id"],
                            enrollment_id=item["enrollment_id"],
                            step_id=item["step_id"],
                        )
                except Exception:
                    self._log(
                        self._safe_context(
                            item,
                            event="send_finalize_failed",
                            phase="begin_dispatch",
                            error_class="internal_finalize",
                            decision="isolate",
                        )
                    )
                    processed.append(
                        self._public_item(
                            item,
                            status="dispatch_not_started",
                            provider_status="not_sent",
                            error_class="internal_finalize",
                            decision="isolate",
                        )
                    )
                    continue
                if not dispatch.get("started"):
                    self._log(
                        self._safe_context(
                            item,
                            event="send_outcome_uncertain",
                            phase="begin_dispatch",
                            error_class="outcome_uncertain",
                            decision="isolate",
                        )
                    )
                    processed.append(
                        self._public_item(
                            item,
                            status="dispatch_not_started",
                            provider_status="not_sent",
                            error_class="outcome_uncertain",
                            decision="isolate",
                        )
                    )
                    continue

                try:
                    provider_result = await self.provider.send_email(self._provider_payload(item))
                except EngageLabSendError as exc:
                    if exc.outcome == "uncertain":
                        processed.append(
                            await self._isolate_uncertain(engine, item, exc, started_at)
                        )
                        continue
                    processed.append(
                        await self._handle_provider_rejection(engine, item, exc, started_at)
                    )
                    continue
                except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
                    processed.append(await self._isolate_uncertain(engine, item, None, started_at))
                    continue
                except Exception:
                    processed.append(await self._isolate_uncertain(engine, item, None, started_at))
                    continue

                message_id = provider_result["engagelab_message_id"]
                recorded = await self._persist_receipt(engine, item, message_id)
                if recorded is None:
                    self._log(
                        self._safe_context(
                            item,
                            event="send_finalize_failed",
                            phase="receipt",
                            error_class="internal_finalize",
                            decision="isolate",
                            message_id_length=len(message_id),
                            elapsed_ms=self._elapsed_ms(started_at),
                        )
                    )
                    processed.append(
                        self._public_item(
                            item,
                            status="accepted_unpersisted",
                            provider_status="accepted_unpersisted",
                            error_class="internal_finalize",
                            decision="isolate",
                            message_id_length=len(message_id),
                        )
                    )
                    continue

                try:
                    async with engine.begin() as conn:
                        result = await self.service.mark_email_sent(
                            conn,
                            email_id=item["email_id"],
                            payload={"engagelab_message_id": message_id},
                        )
                except Exception:
                    self._log(
                        self._safe_context(
                            item,
                            event="send_finalize_failed",
                            phase="finalize",
                            error_class="internal_finalize",
                            decision="isolate",
                            message_id_length=len(message_id),
                            elapsed_ms=self._elapsed_ms(started_at),
                        )
                    )
                    processed.append(
                        self._public_item(
                            item,
                            status="accepted_pending",
                            provider_status="accepted_pending",
                            error_class="internal_finalize",
                            decision="isolate",
                            message_id_length=len(message_id),
                        )
                    )
                    continue

                self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
                processed.append(
                    self._public_item(
                        result,
                        provider_status="sent",
                        error_class="accepted",
                        decision="sent",
                        message_id_length=len(message_id),
                    )
                )
                self._log(
                    self._safe_context(
                        item,
                        event="send_accepted",
                        phase="finalize",
                        error_class="accepted",
                        decision="sent",
                        message_id_length=len(message_id),
                        elapsed_ms=self._elapsed_ms(started_at),
                    )
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

        return sanitize_round_result(
            {
                "claimed_count": len(claimed["items"]),
                "processed_count": len(processed),
                "finalized_count": finalized_count,
                "items": processed,
            }
        )

    async def _release_unsent_locks_if_due(self, engine) -> None:
        """进程运行中也回收未外发的新锁。启动时那一次不够，且不能每轮全表扫。"""
        now = self._now()
        if self._next_unsent_recovery_at is not None and now < self._next_unsent_recovery_at:
            return
        self._next_unsent_recovery_at = now + UNSENT_LOCK_RECOVERY_INTERVAL
        try:
            async with engine.begin() as conn:
                released = await self.service.release_unsent_locks(
                    conn,
                    as_of=now,
                    stale_minutes=UNSENT_LOCK_STALE_MINUTES,
                )
        except Exception:
            self._log(
                {
                    "event": "send_finalize_failed",
                    "phase": "unsent_locked",
                    "error_class": "internal_finalize",
                    "decision": "isolate",
                }
            )
            return
        if released.get("recovered_count"):
            self._log(
                {
                    "event": "stale_lock_recovered",
                    "phase": "unsent_locked",
                    "count": released["recovered_count"],
                    "enrollment_ids": released.get("enrollment_ids") or [],
                }
            )

    async def _finalize_pending(self, engine) -> int:
        now = self._now()
        try:
            async with engine.begin() as conn:
                pending = await self.service.list_accepted_pending(
                    conn,
                    limit=PENDING_FINALIZE_LIMIT,
                    as_of=now,
                    lease_until=now + PENDING_FINALIZE_LEASE,
                )
        except Exception:
            self._log(
                {
                    "event": "send_finalize_failed",
                    "phase": "recovery",
                    "error_class": "internal_finalize",
                    "decision": "isolate",
                }
            )
            return 0

        finalized = 0
        for row in pending:
            message_id = row.get("provider_message_id") or ""
            payload = {"engagelab_message_id": message_id}
            accepted_at = row.get("provider_accepted_at")
            if isinstance(accepted_at, datetime):
                payload["sent_at"] = accepted_at
            try:
                async with engine.begin() as conn:
                    await self.service.mark_email_sent(
                        conn,
                        email_id=row["email_id"],
                        payload=payload,
                    )
            except Exception:
                self._log(
                    {
                        "event": "send_finalize_failed",
                        "phase": "recovery",
                        "error_class": "internal_finalize",
                        "decision": "isolate",
                        "tenant_id": row.get("tenant_id"),
                        "email_id": row.get("email_id"),
                        "message_id_length": len(message_id),
                    }
                )
                try:
                    async with engine.begin() as conn:
                        await self.service.defer_accepted_pending(
                            conn,
                            email_id=row["email_id"],
                            tenant_id=row["tenant_id"],
                            enrollment_id=row["enrollment_id"],
                            step_id=row["step_id"],
                            not_before=self._now() + PENDING_FINALIZE_BACKOFF,
                        )
                except Exception:
                    self._log(
                        {
                            "event": "send_finalize_failed",
                            "phase": "recovery_backoff",
                            "error_class": "internal_finalize",
                            "decision": "isolate",
                            "tenant_id": row.get("tenant_id"),
                            "email_id": row.get("email_id"),
                        }
                    )
                continue
            finalized += 1
            self._log(
                {
                    "event": "send_accepted",
                    "phase": "recovery",
                    "error_class": "accepted",
                    "decision": "sent",
                    "tenant_id": row.get("tenant_id"),
                    "email_id": row.get("email_id"),
                    "message_id_length": len(message_id),
                }
            )
        return finalized

    async def _persist_receipt(self, engine, item: dict, message_id: str) -> dict | None:
        attempts = 1 + len(RECEIPT_RETRY_DELAYS)
        accepted_at = self._now()
        for attempt in range(attempts):
            if attempt:
                await self.sleep(RECEIPT_RETRY_DELAYS[attempt - 1])
            try:
                async with engine.begin() as conn:
                    recorded = await self.service.record_provider_acceptance(
                        conn,
                        email_id=item["email_id"],
                        tenant_id=item["tenant_id"],
                        enrollment_id=item["enrollment_id"],
                        step_id=item["step_id"],
                        provider_message_id=message_id,
                        accepted_at=accepted_at,
                    )
            except AppError as exc:
                if exc.code == "RECEIPT_CONFLICT":
                    self._log(
                        self._safe_context(
                            item,
                            event="send_finalize_failed",
                            phase="receipt",
                            error_class="receipt_conflict",
                            decision="isolate",
                            message_id_length=len(message_id),
                        )
                    )
                    return None
                continue
            except Exception:
                continue
            if recorded.get("conflict"):
                self._log(
                    self._safe_context(
                        item,
                        event="send_finalize_failed",
                        phase="receipt",
                        error_class="receipt_conflict",
                        decision="isolate",
                        message_id_length=len(message_id),
                    )
                )
                return None
            if recorded.get("persisted"):
                return recorded
        return None

    async def _isolate_uncertain(
        self,
        engine,
        item: dict,
        exc: EngageLabSendError | None,
        started_at: datetime,
    ) -> dict:
        try:
            async with engine.begin() as conn:
                await self.service.mark_dispatch_uncertain(
                    conn,
                    email_id=item["email_id"],
                    tenant_id=item["tenant_id"],
                    enrollment_id=item["enrollment_id"],
                    step_id=item["step_id"],
                )
        except Exception:
            self._log(
                self._safe_context(
                    item,
                    event="send_finalize_failed",
                    phase="uncertain",
                    error_class="internal_finalize",
                    decision="isolate",
                    elapsed_ms=self._elapsed_ms(started_at),
                )
            )
        self._log(
            self._safe_context(
                item,
                event="send_outcome_uncertain",
                phase="send",
                error_class="outcome_uncertain",
                decision="isolate",
                http_status=exc.http_status if exc else None,
                provider_code=exc.provider_code if exc else None,
                elapsed_ms=self._elapsed_ms(started_at),
            )
        )
        return self._public_item(
            item,
            status="uncertain",
            provider_status="uncertain",
            error_class="outcome_uncertain",
            decision="isolate",
            http_status=exc.http_status if exc else None,
            provider_code=exc.provider_code if exc else None,
        )

    async def _handle_provider_rejection(
        self, engine, item: dict, exc: EngageLabSendError, started_at: datetime
    ) -> dict:
        classification = classify_send_error(exc)
        if (
            classification["error_type"] == "rate_limit"
            and self._record_rate_limit_hit(item["domain_id"], self._now()) >= 3
        ):
            classification = {
                **classification,
                "is_permanent": False,
                "error_type": "quota",
                "error_category": "quota",
                "error_class": "rate_limit",
                "decision": "defer_quota",
            }
        if classification["error_type"] == "quota":
            if self.enrollment_quota_defer_counts.get(item["enrollment_id"], 0) < 3:
                paused_until = self._open_quota_circuit(item=item, classification=classification)
                outcome = await self._defer_for_quota(
                    engine,
                    item=item,
                    exc=exc,
                    paused_until=paused_until,
                    classification=classification,
                )
                result = outcome["result"]
                if outcome["deferred"]:
                    return self._public_item(
                        result,
                        provider_status="quota_deferred",
                        error_class=classification["error_class"],
                        decision="defer_quota",
                        provider_code=classification["provider_code"],
                        http_status=classification["http_status"],
                    )
                if result.get("status") == "failed":
                    self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
                self._log(
                    self._safe_context(
                        item,
                        event="send_rejected",
                        phase="quota_fallback",
                        error_class=classification["error_class"],
                        decision="retry",
                        provider_code=classification["provider_code"],
                        http_status=classification["http_status"],
                        attempt=result.get("send_attempt_count"),
                        elapsed_ms=self._elapsed_ms(started_at),
                    )
                )
                return self._public_item(
                    result,
                    provider_status="failed",
                    error_class=classification["error_class"],
                    decision="retry",
                    provider_code=classification["provider_code"],
                    http_status=classification["http_status"],
                )
            self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
            classification = {
                **classification,
                "is_permanent": False,
                "error_type": "temporary",
                "error_class": classification["error_class"],
                "decision": "retry",
            }
        try:
            async with engine.begin() as conn:
                result = await self.service.mark_email_failed(
                    conn,
                    email_id=item["email_id"],
                    payload={
                        "error_code": "ENGAGELAB_ERROR",
                        "status_code": exc.status_code,
                        "is_permanent": classification["is_permanent"],
                        "error_category": classification["error_category"],
                        "domain_id": item["domain_id"],
                        "provider_code": classification["provider_code"],
                    },
                )
        except Exception:
            self._log(
                self._safe_context(
                    item,
                    event="send_finalize_failed",
                    phase="reject",
                    error_class="internal_finalize",
                    decision="isolate",
                    http_status=classification["http_status"],
                    provider_code=classification["provider_code"],
                    elapsed_ms=self._elapsed_ms(started_at),
                )
            )
            return self._public_item(
                item,
                status="reject_unrecorded",
                provider_status="failed",
                error_class="internal_finalize",
                decision="isolate",
                http_status=classification["http_status"],
                provider_code=classification["provider_code"],
            )
        if classification["is_permanent"] or result.get("status") == "failed":
            self.enrollment_quota_defer_counts.pop(item["enrollment_id"], None)
        self._log(
            self._safe_context(
                item,
                event="send_rejected",
                phase="provider",
                error_class=classification["error_class"],
                decision=classification["decision"],
                provider_code=classification["provider_code"],
                http_status=classification["http_status"],
                attempt=result.get("send_attempt_count"),
                elapsed_ms=self._elapsed_ms(started_at),
            )
        )
        return self._public_item(
            result,
            provider_status="failed",
            error_class=classification["error_class"],
            decision=classification["decision"],
            provider_code=classification["provider_code"],
            http_status=classification["http_status"],
        )

    def _provider_payload(self, item: dict) -> dict:
        return {
            "from_email": item["from_email"],
            "from_name": item.get("from_name"),
            "to_email": item["to_email"],
            "to_name": item.get("to_name"),
            "subject": item["subject"],
            "body_html": item["body_html"],
            "body_text": item.get("body_text"),
            "idempotency_key": f"{item['enrollment_id']}:{item['step_id']}",
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
        self,
        engine,
        *,
        item: dict,
        exc: EngageLabSendError,
        paused_until: datetime,
        classification: dict,
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
        except Exception:
            self._log(
                self._safe_context(
                    item,
                    event="quota_defer_failed",
                    phase="quota",
                    error_class=classification["error_class"],
                    decision="retry",
                    provider_code=classification["provider_code"],
                    http_status=classification["http_status"],
                )
            )
            try:
                async with engine.begin() as conn:
                    result = await self.service.mark_email_failed(
                        conn,
                        email_id=item["email_id"],
                        payload={
                            "error_code": "ENGAGELAB_ERROR",
                            "status_code": exc.status_code,
                            "is_permanent": False,
                            "error_category": "quota",
                            "domain_id": item["domain_id"],
                            "provider_code": classification["provider_code"],
                        },
                    )
            except Exception:
                self._log(
                    self._safe_context(
                        item,
                        event="quota_defer_fallback_failed",
                        phase="quota",
                        error_class="internal_finalize",
                        decision="isolate",
                        provider_code=classification["provider_code"],
                        http_status=classification["http_status"],
                    )
                )
                return {
                    "deferred": False,
                    "result": {
                        "email_id": item["email_id"],
                        "status": "quota_defer_fallback_failed",
                    },
                }
            return {"deferred": False, "result": result}

        self.enrollment_quota_defer_counts[item["enrollment_id"]] = (
            self.enrollment_quota_defer_counts.get(item["enrollment_id"], 0) + 1
        )
        return {"deferred": True, "result": result}

    def _open_quota_circuit(self, *, item: dict, classification: dict) -> datetime:
        paused_until = self._next_beijing_midnight(self._now())
        self.domain_quota_paused[item["domain_id"]] = paused_until
        self._log(
            self._safe_context(
                item,
                event="quota_circuit_open",
                phase="quota",
                error_class=classification["error_class"],
                decision="defer_quota",
                provider_code=classification["provider_code"],
                http_status=classification["http_status"],
                paused_until=paused_until,
                resume_at=paused_until,
            )
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
        interval = (send_strategy or {}).get("interval_seconds") or [3, 3]
        if not isinstance(interval, list | tuple) or len(interval) != 2:
            interval = [3, 3]
        low = max(float(interval[0]), 0)
        high = max(float(interval[1]), low)
        return self.random_between(low, high)

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _elapsed_ms(self, started_at: datetime) -> int:
        return int((self._now() - started_at).total_seconds() * 1000)

    def _safe_context(self, item: dict, **fields: Any) -> dict[str, Any]:
        return {
            "tenant_id": item.get("tenant_id"),
            "domain_id": item.get("domain_id"),
            "email_id": item.get("email_id"),
            **fields,
        }

    def _public_item(self, result: dict, **extra: Any) -> dict[str, Any]:
        merged = {**result, **extra}
        return {key: merged[key] for key in _PUBLIC_ITEM_KEYS if key in merged}

    def _log(self, record: dict[str, Any]) -> None:
        safe = {key: record[key] for key in _SAFE_LOG_KEYS if key in record}
        safe.setdefault("instance_id", get_settings().instance_id)
        if self.log_sink:
            self.log_sink(safe)
            return
        logger.info(json.dumps(safe, ensure_ascii=False, default=str))
