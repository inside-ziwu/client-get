"""mark_email_sent / mark_email_failed 幂等闸门测试。

闸门语义：email_send_locks 上 `status = 'locked'` 的条件更新是唯一入场券——
0 行即重复/迟到回调，直接幂等返回，跳过全部副作用（计数、enrollment 推进、配额释放）。
闸门必须放锁表而非 emails.status：webhook 可能先于回调把 emails.status 推进到
delivered 等后续态，那不是重复回调。
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.tenant_messaging_service import TenantMessagingService

EMAIL_ROW = {
    "id": "email-001",
    "created_at": datetime(2026, 7, 23, 8, 0, 0, tzinfo=timezone.utc),
    "status": "queued",
    "tenant_contact_id": "contact-001",
    "plan_id": "plan-001",
    "step_number": 1,
    "enrollment_id": "enroll-001",
}


def _result(first=None):
    result = MagicMock()
    result.mappings.return_value.first.return_value = first
    return result


def _conn(results: list) -> AsyncMock:
    conn = AsyncMock()
    conn.execute.side_effect = results
    return conn


def _executed_sql(conn: AsyncMock) -> str:
    return "\n".join(str(call.args[0]) for call in conn.execute.call_args_list)


class TestMarkEmailSentIdempotency:
    @pytest.mark.asyncio
    async def test_first_call_runs_full_side_effects(self):
        conn = _conn(
            [
                _result(dict(EMAIL_ROW)),                          # _load_email
                _result({"id": "lock-001"}),                       # 闸门命中
                _result(),                                         # emails UPDATE
                _result(),                                         # tenant_contacts UPDATE
                _result({"step_number": 2, "delay_days": 3}),      # 下一步存在
                _result(),                                         # enrollment 推进
                _result(),                                         # sent_count + 1
            ]
        )
        service = TenantMessagingService()
        result = await service.mark_email_sent(conn, email_id="email-001", payload={})

        assert result == {"email_id": "email-001", "status": "sent"}
        assert conn.execute.await_count == 7
        assert "sent_count = sent_count + 1" in _executed_sql(conn)

    @pytest.mark.asyncio
    async def test_duplicate_call_skips_all_side_effects(self):
        conn = _conn(
            [
                _result({**EMAIL_ROW, "status": "sent"}),  # _load_email
                _result(None),                             # 闸门 0 行：锁已终结
            ]
        )
        service = TenantMessagingService()
        result = await service.mark_email_sent(conn, email_id="email-001", payload={})

        assert result == {"email_id": "email-001", "status": "sent", "duplicate": True}
        assert conn.execute.await_count == 2
        assert "sent_count" not in _executed_sql(conn)

    @pytest.mark.asyncio
    async def test_webhook_racing_ahead_is_not_treated_as_duplicate(self):
        """webhook 先把 emails.status 推到 delivered，但锁仍是 locked——必须照常计数。"""
        conn = _conn(
            [
                _result({**EMAIL_ROW, "status": "delivered"}),
                _result({"id": "lock-001"}),
                _result(),
                _result(),
                _result({"step_number": 2, "delay_days": 3}),
                _result(),
                _result(),
            ]
        )
        service = TenantMessagingService()
        result = await service.mark_email_sent(conn, email_id="email-001", payload={})

        assert result == {"email_id": "email-001", "status": "sent"}
        assert "sent_count = sent_count + 1" in _executed_sql(conn)
        # emails 状态推进带 queued 门槛，不把 delivered 回退成 sent
        assert "CASE WHEN status = 'queued' THEN 'sent' ELSE status END" in _executed_sql(conn)


class TestMarkEmailFailedIdempotency:
    @pytest.mark.asyncio
    async def test_first_temporary_failure_schedules_retry(self):
        conn = _conn(
            [
                _result(dict(EMAIL_ROW)),              # _load_email
                _result({"id": "lock-001"}),           # 闸门命中
                _result(),                             # emails UPDATE
                _result(None),                         # 配额释放：plan 无 domain，early return
                _result({"send_attempt_count": 0}),    # enrollment FOR UPDATE
                _result(),                             # enrollment 改期
            ]
        )
        service = TenantMessagingService()
        result = await service.mark_email_failed(
            conn, email_id="email-001", payload={"reason": "smtp timeout"}
        )

        assert result == {
            "email_id": "email-001",
            "status": "retry_scheduled",
            "reason": "smtp timeout",
            "send_attempt_count": 1,
            "retry_seconds": 900,
        }
        assert conn.execute.await_count == 6

    @pytest.mark.asyncio
    async def test_duplicate_call_does_not_consume_retry_budget(self):
        conn = _conn(
            [
                _result({**EMAIL_ROW, "status": "failed"}),  # _load_email
                _result(None),                               # 闸门 0 行
                _result({"send_attempt_count": 2}),          # 仅读当前计数用于回显
            ]
        )
        service = TenantMessagingService()
        result = await service.mark_email_failed(
            conn, email_id="email-001", payload={"reason": "smtp timeout"}
        )

        assert result == {
            "email_id": "email-001",
            "status": "failed",
            "reason": "smtp timeout",
            "send_attempt_count": 2,
            "duplicate": True,
        }
        assert conn.execute.await_count == 3
        sql = _executed_sql(conn)
        assert "UPDATE sequence_enrollments" not in sql
        assert "domain_daily_usage" not in sql
