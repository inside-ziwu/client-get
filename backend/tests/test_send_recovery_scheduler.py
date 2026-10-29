"""恢复状态机：跨轮回收未外发锁、失败退避让出队列、接单时间不随恢复漂移。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.email_reconciliation_service import EmailReconciliationService
from app.services.tenant_messaging_service import TenantMessagingService
from app.utils.beijing_time import beijing_today
from app.workers.sending import PENDING_FINALIZE_BACKOFF, SendingWorker
from tests.test_sending_worker import _Engine, _Provider

HELD = {"locked", "sent", "dispatching", "accepted_pending", "uncertain"}
ACCEPTED_AT = datetime(2026, 10, 26, 15, 30, tzinfo=UTC)
RECOVERY_AT = datetime(2026, 10, 27, 2, 0, tzinfo=UTC)


def _window_config() -> dict:
    rule = {
        "id": "rule-1",
        "name": "weekday",
        "work_days": [0, 1, 2, 3, 4],
        "time_segments": [{"start": "09:00", "end": "23:59"}],
        "is_default": True,
    }
    return {
        "rules": {"rule-1": rule},
        "default_rule": rule,
        "countries": {"CHN": {"timezone": "Asia/Shanghai", "rule_set_id": "rule-1"}},
        "holidays": set(),
    }


def _result(*, first=None):
    mappings = MagicMock()
    mappings.first.return_value = first
    mappings.all.return_value = []
    result = MagicMock()
    result.mappings.return_value = mappings
    return result


class _Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs) -> None:
        self.value += timedelta(**kwargs)


class _Lock:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class _RecoveryState:
    """跨 run_once 保留锁、退避和额度。不是每轮返回同一份列表。"""

    def __init__(self, clock: _Clock) -> None:
        self.clock = clock
        self.locks: dict[str, _Lock] = {}
        self.quota_releases: list = []
        self.window_skips: list[str] = []
        self.fail_finalize: set[str] = set()
        self.step_advances: dict[str, int] = {}
        self.sent_facts: dict[str, datetime] = {}
        self.fail_begin_dispatch = False
        self.allow_claim = True
        self.recover_calls = 0
        self.timezone_config = _window_config()

    def add(self, row: _Lock) -> None:
        self.locks[row.id] = row

    async def recover_stale_locks(self, conn):
        self.recover_calls += 1
        return {"recovered_count": 0, "enrollment_ids": [], "isolated_count": 0}

    async def isolate_timed_out_dispatches(self, conn, *, stale_minutes=30):
        del stale_minutes
        return {"isolated_count": 0, "enrollment_ids": []}

    async def release_unsent_locks(self, conn, *, as_of, stale_minutes=30):
        cutoff = as_of - timedelta(minutes=stale_minutes)
        released = []
        for row in self.locks.values():
            never_sent = (
                row.status == "locked"
                and row.quota_usage_date is not None
                and row.dispatch_started_at is None
                and row.provider_message_id is None
                and row.provider_accepted_at is None
                and row.locked_at < cutoff
            )
            if not never_sent:
                continue
            row.status = "released"
            released.append(row)
            self.quota_releases.append(row.quota_usage_date)
        return {
            "recovered_count": len(released),
            "enrollment_ids": [row.enrollment_id for row in released],
        }

    async def list_accepted_pending(self, conn, *, limit=20, as_of=None, lease_until=None):
        moment = as_of or self.clock()
        due = [
            row
            for row in self.locks.values()
            if row.status == "accepted_pending"
            and row.provider_message_id
            and row.email_id
            and (row.finalize_not_before is None or row.finalize_not_before <= moment)
        ]
        due.sort(key=lambda row: (row.provider_accepted_at, row.id))
        chosen = due[:limit]
        if lease_until is not None:
            for row in chosen:
                row.finalize_not_before = lease_until
        return [
            {
                "email_id": row.email_id,
                "tenant_id": row.tenant_id,
                "enrollment_id": row.enrollment_id,
                "step_id": row.step_id,
                "provider_message_id": row.provider_message_id,
                "provider_accepted_at": row.provider_accepted_at,
            }
            for row in chosen
        ]

    async def defer_accepted_pending(
        self, conn, *, email_id, tenant_id, enrollment_id, step_id, not_before
    ):
        for row in self.locks.values():
            if (
                row.email_id == email_id
                and row.tenant_id == tenant_id
                and row.enrollment_id == enrollment_id
                and row.step_id == step_id
                and row.status == "accepted_pending"
            ):
                row.finalize_not_before = not_before
                return {"deferred": True}
        return {"deferred": False}

    async def begin_dispatch(self, conn, *, email_id, tenant_id, enrollment_id, step_id):
        if self.fail_begin_dispatch:
            self.fail_begin_dispatch = False
            raise RuntimeError("begin_dispatch failed")
        for row in self.locks.values():
            if row.email_id == email_id and row.status == "locked":
                row.status = "dispatching"
                row.dispatch_started_at = self.clock()
        return {"started": True}

    async def mark_email_sent(self, conn, *, email_id, payload):
        row = next((item for item in self.locks.values() if item.email_id == email_id), None)
        if row is None or row.status != "accepted_pending":
            return {"email_id": email_id, "status": "sent", "duplicate": True}
        if email_id in self.fail_finalize:
            raise RuntimeError("finalize failed")
        row.status = "sent"
        send_at = payload.get("sent_at") or row.provider_accepted_at
        self.sent_facts[email_id] = send_at
        self.step_advances[row.enrollment_id] = self.step_advances.get(row.enrollment_id, 0) + 1
        return {"email_id": email_id, "status": "sent", "duplicate": False}

    async def list_running_domain_ids(self, conn):
        return ["domain-a"]

    async def load_timezone_config(self, conn):
        return self.timezone_config

    async def claim_due_emails(self, conn, **kwargs):
        del kwargs
        sendable, reason, _next = TenantMessagingService().is_sendable_now(
            "CHN", self.timezone_config, now_utc=self.clock()
        )
        if not sendable:
            self.window_skips.append(reason or "closed")
            return {"items": []}
        if not self.allow_claim:
            return {"items": []}
        held = [
            row
            for row in self.locks.values()
            if row.enrollment_id == "enrollment-new" and row.status in HELD
        ]
        if held:
            return {"items": []}
        now = self.clock()
        row = _Lock(
            id="lock-new",
            status="locked",
            locked_at=now,
            quota_usage_date=beijing_today(now),
            dispatch_started_at=None,
            provider_message_id=None,
            provider_accepted_at=None,
            finalize_not_before=None,
            email_id="email-new",
            tenant_id="tenant-new",
            enrollment_id="enrollment-new",
            step_id="step-new",
        )
        self.locks[row.id] = row
        return {
            "items": [
                {
                    "email_id": row.email_id,
                    "tenant_id": row.tenant_id,
                    "enrollment_id": row.enrollment_id,
                    "plan_id": "plan-new",
                    "step_id": row.step_id,
                    "domain_id": "domain-a",
                    "send_strategy": {"interval_seconds": [0, 0]},
                    "tenant_contact_id": "contact-new",
                    "from_email": "sales@example.com",
                    "from_name": "Sales",
                    "to_email": "buyer@example.com",
                    "to_name": "Buyer",
                    "subject": "Hello",
                    "body_html": "<p>Hello</p>",
                    "body_text": "Hello",
                }
            ]
        }

    async def record_provider_acceptance(self, conn, **kwargs):
        raise AssertionError("未外发恢复不能写回执")

    async def mark_email_failed(self, conn, **kwargs):
        raise AssertionError("未外发恢复不能走失败重试")

    async def defer_email_for_quota(self, conn, **kwargs):
        raise AssertionError("未外发恢复不能记配额熔断")

    async def mark_dispatch_uncertain(self, conn, **kwargs):
        raise AssertionError("这条路径不应把未外发锁改成 uncertain")


def _worker(clock: _Clock, state: _RecoveryState, provider=None) -> SendingWorker:
    return SendingWorker(
        service=state,
        provider=provider or _Provider(),
        clock=clock,
        sleep=AsyncMock(),
        random_between=lambda low, high: 0,
        log_sink=lambda record: None,
    )


def _seed_untouched(state: _RecoveryState, moment: datetime) -> None:
    state.add(
        _Lock(
            id="lock-legacy",
            status="locked",
            locked_at=moment - timedelta(hours=2),
            quota_usage_date=None,
            dispatch_started_at=None,
            provider_message_id=None,
            provider_accepted_at=None,
            finalize_not_before=None,
            email_id="email-legacy",
            tenant_id="tenant-legacy",
            enrollment_id="enrollment-legacy",
            step_id="step-legacy",
        )
    )
    state.add(
        _Lock(
            id="lock-uncertain",
            status="uncertain",
            locked_at=moment - timedelta(hours=2),
            quota_usage_date=beijing_today(moment),
            dispatch_started_at=moment - timedelta(hours=2),
            provider_message_id=None,
            provider_accepted_at=None,
            finalize_not_before=None,
            email_id="email-uncertain",
            tenant_id="tenant-uncertain",
            enrollment_id="enrollment-uncertain",
            step_id="step-uncertain",
        )
    )
    state.add(
        _Lock(
            id="lock-accepted",
            status="accepted_pending",
            locked_at=moment - timedelta(hours=2),
            quota_usage_date=beijing_today(moment),
            dispatch_started_at=moment - timedelta(hours=2),
            provider_message_id="accepted-message",
            provider_accepted_at=ACCEPTED_AT,
            finalize_not_before=None,
            email_id="email-accepted",
            tenant_id="tenant-accepted",
            enrollment_id="enrollment-accepted",
            step_id="step-accepted",
        )
    )
    state.fail_finalize.add("email-accepted")


@pytest.mark.asyncio
async def test_unsent_lock_is_released_after_threshold_without_restart():
    clock = _Clock(datetime(2026, 10, 23, 15, 50, tzinfo=UTC))
    state = _RecoveryState(clock)
    state.fail_begin_dispatch = True
    _seed_untouched(state, clock())
    provider = _Provider()
    worker = _worker(clock, state, provider)

    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)

    assert state.recover_calls == 1
    assert state.locks["lock-new"].status == "locked"
    assert state.quota_releases == []
    assert provider.payloads == []

    clock.advance(minutes=31)
    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)

    assert state.recover_calls == 1
    assert state.locks["lock-new"].status == "released"
    assert state.quota_releases == [beijing_today(datetime(2026, 10, 23, 15, 50, tzinfo=UTC))]
    assert state.locks["lock-legacy"].status == "locked"
    assert state.locks["lock-uncertain"].status == "uncertain"
    assert state.locks["lock-accepted"].status == "accepted_pending"
    assert state.locks["lock-accepted"].provider_message_id == "accepted-message"
    assert state.window_skips
    assert provider.payloads == []

    clock.value = datetime(2026, 10, 26, 2, 0, tzinfo=UTC)
    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)

    assert state.quota_releases == [beijing_today(datetime(2026, 10, 23, 15, 50, tzinfo=UTC))]
    assert len(provider.payloads) == 1
    assert state.locks["lock-uncertain"].status == "uncertain"
    assert state.locks["lock-legacy"].status == "locked"


@pytest.mark.asyncio
async def test_failed_finalize_backoff_reaches_later_pending_across_restart():
    clock = _Clock(datetime(2026, 10, 27, 2, 0, tzinfo=UTC))
    state = _RecoveryState(clock)
    state.allow_claim = False
    for index in range(21):
        email_id = f"email-{index:02d}"
        state.add(
            _Lock(
                id=f"lock-{index:02d}",
                status="accepted_pending",
                locked_at=clock(),
                quota_usage_date=None,
                dispatch_started_at=clock(),
                provider_message_id=f"message-{index:02d}",
                provider_accepted_at=ACCEPTED_AT + timedelta(seconds=index),
                finalize_not_before=None,
                email_id=email_id,
                tenant_id="tenant-1",
                enrollment_id=f"enrollment-{index:02d}",
                step_id="step-1",
            )
        )
        if index < 20:
            state.fail_finalize.add(email_id)
    provider = _Provider()
    worker = _worker(clock, state, provider)

    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)
    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)
    await worker.run_once(_Engine(), service_instance="worker-1", idle_poll_seconds=0)

    assert state.step_advances == {"enrollment-20": 1}
    assert state.sent_facts["email-20"] == ACCEPTED_AT + timedelta(seconds=20)
    assert state.locks["lock-00"].status == "accepted_pending"
    assert state.locks["lock-00"].finalize_not_before == clock() + PENDING_FINALIZE_BACKOFF
    assert provider.payloads == []

    restarted = _worker(clock, state, provider)
    await restarted.run_once(_Engine(), service_instance="worker-2", idle_poll_seconds=0)

    assert state.step_advances == {"enrollment-20": 1}
    assert state.locks["lock-00"].status == "accepted_pending"
    assert provider.payloads == []

    clock.advance(seconds=61)
    await restarted.run_once(_Engine(), service_instance="worker-2", idle_poll_seconds=0)

    assert state.locks["lock-00"].finalize_not_before == clock() + PENDING_FINALIZE_BACKOFF
    assert state.step_advances["enrollment-20"] == 1


@pytest.mark.asyncio
async def test_pending_lease_does_not_hand_the_same_rows_to_a_second_reader():
    clock = _Clock(datetime(2026, 10, 27, 2, 0, tzinfo=UTC))
    state = _RecoveryState(clock)
    for index in range(21):
        state.add(
            _Lock(
                id=f"lock-{index:02d}",
                status="accepted_pending",
                locked_at=clock(),
                quota_usage_date=None,
                dispatch_started_at=clock(),
                provider_message_id=f"message-{index:02d}",
                provider_accepted_at=ACCEPTED_AT + timedelta(seconds=index),
                finalize_not_before=None,
                email_id=f"email-{index:02d}",
                tenant_id="tenant-1",
                enrollment_id=f"enrollment-{index:02d}",
                step_id="step-1",
            )
        )

    first = await state.list_accepted_pending(
        None, limit=20, as_of=clock(), lease_until=clock() + timedelta(seconds=15)
    )
    second = await state.list_accepted_pending(
        None, limit=20, as_of=clock(), lease_until=clock() + timedelta(seconds=15)
    )

    first_ids = {row["email_id"] for row in first}
    second_ids = {row["email_id"] for row in second}
    assert len(first_ids) == 20
    assert first_ids.isdisjoint(second_ids)
    assert second_ids == {"email-20"}


@pytest.mark.asyncio
async def test_receipt_retries_keep_the_original_acceptance_time():
    clock = _Clock(datetime(2026, 10, 26, 15, 30, tzinfo=UTC))
    seen: list[datetime] = []

    class _Acceptance:
        def __init__(self) -> None:
            self.left = 2

        async def record_provider_acceptance(self, conn, **kwargs):
            seen.append(kwargs["accepted_at"])
            if self.left:
                self.left -= 1
                raise RuntimeError("receipt db unavailable")
            return {"persisted": True, "duplicate": False, "conflict": False}

    async def sleep(seconds: float) -> None:
        clock.advance(seconds=seconds)

    worker = SendingWorker(
        service=_Acceptance(),
        provider=_Provider(),
        clock=clock,
        sleep=sleep,
        log_sink=lambda record: None,
    )
    recorded = await worker._persist_receipt(
        _Engine(),
        {
            "email_id": "email-1",
            "tenant_id": "tenant-1",
            "enrollment_id": "enrollment-1",
            "step_id": "step-1",
        },
        "m" * 107,
    )

    assert recorded["persisted"] is True
    assert seen == [datetime(2026, 10, 26, 15, 30, tzinfo=UTC)] * 3


@pytest.mark.asyncio
async def test_mark_email_sent_uses_stored_acceptance_time_across_midnight(monkeypatch):
    service = TenantMessagingService()
    calls: list[tuple[str, dict]] = []

    async def execute(statement, params=None):
        sql = str(statement)
        calls.append((sql, params or {}))
        if "UPDATE email_send_locks" in sql and "accepted_pending" in sql:
            return _result(
                first={
                    "id": "lock-1",
                    "provider_message_id": "m" * 107,
                    "provider_accepted_at": ACCEPTED_AT,
                }
            )
        if "FROM sequence_steps" in sql:
            return _result(first={"step_number": 2, "delay_days": 2})
        return _result()

    conn = AsyncMock()
    conn.execute.side_effect = execute
    monkeypatch.setattr(
        service,
        "_load_email",
        AsyncMock(
            return_value={
                "id": "email-1",
                "created_at": ACCEPTED_AT,
                "status": "queued",
                "tenant_id": "tenant-1",
                "tenant_contact_id": "contact-1",
                "plan_id": "plan-1",
                "step_number": 1,
                "step_id": "step-1",
                "enrollment_id": "enrollment-1",
            }
        ),
    )
    await service.mark_email_sent(
        conn,
        email_id="email-1",
        payload={"engagelab_message_id": "m" * 107, "sent_at": RECOVERY_AT},
    )

    email_params = next(params for sql, params in calls if "UPDATE emails" in sql)
    enrollment_params = next(
        params for sql, params in calls if "UPDATE sequence_enrollments" in sql
    )
    assert email_params["send_at"] == ACCEPTED_AT
    assert enrollment_params["send_at"] == ACCEPTED_AT
    assert enrollment_params["delay_days"] == 2
    enrollment_sql = next(sql for sql, _params in calls if "UPDATE sequence_enrollments" in sql)
    assert "CAST(:send_at AS timestamptz)" in enrollment_sql
    assert "make_interval(days => :delay_days)" in enrollment_sql
    assert "last_step_sent_at = now()" not in enrollment_sql
    assert "next_step_due_at = now()" not in enrollment_sql

    grouped = EmailReconciliationService()._group_by_send_date_cst(
        [{"sent_at": email_params["send_at"], "engagelab_message_id": "m" * 107}]
    )
    assert list(grouped) == ["2026-10-26"]

    calls.clear()

    async def duplicate(statement, params=None):
        sql = str(statement)
        calls.append((sql, params or {}))
        return _result(first=None)

    conn.execute.side_effect = duplicate
    result = await service.mark_email_sent(
        conn,
        email_id="email-1",
        payload={"engagelab_message_id": "m" * 107, "sent_at": RECOVERY_AT},
    )
    assert result["duplicate"] is True
    assert not any("UPDATE sequence_enrollments" in sql for sql, _params in calls)
    assert not any("sent_count" in sql for sql, _params in calls)
