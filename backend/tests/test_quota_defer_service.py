from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.tenant_messaging_service import TenantMessagingService

EMAIL_ID = UUID("019f2b25-1111-7111-8111-111111111111")
EMAIL_CREATED_AT = datetime(2026, 7, 2, 15, 31, tzinfo=UTC)
PLAN_ID = UUID("019f2b25-2222-7222-8222-222222222222")
ENROLLMENT_ID = UUID("019f2b25-3333-7333-8333-333333333333")
CONTACT_ID = UUID("019f2b25-4444-7444-8444-444444444444")
DOMAIN_ID = UUID("019f2b25-5555-7555-8555-555555555555")
RESUME_AT = datetime(2026, 7, 2, 16, 0, tzinfo=UTC)
DEFAULT_EMAIL = object()


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


class FakeQuotaDeferConn:
    def __init__(self, *, email=DEFAULT_EMAIL):
        self.email = _email_row() if email is DEFAULT_EMAIL else email
        self.executions = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.executions.append((sql, params))

        if "FROM emails" in sql:
            return FakeResult(self.email)

        if "SELECT domain_id FROM sending_plans" in sql:
            return FakeResult({"domain_id": DOMAIN_ID})

        return FakeResult(None)

    def statements_containing(self, needle: str):
        return [(sql, params) for sql, params in self.executions if needle in sql]


def _email_row(**overrides) -> dict:
    row = {
        "id": EMAIL_ID,
        "created_at": EMAIL_CREATED_AT,
        "plan_id": PLAN_ID,
        "enrollment_id": ENROLLMENT_ID,
        "tenant_contact_id": CONTACT_ID,
        "sent_at": None,
        "engagelab_message_id": None,
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_defer_email_for_quota_deletes_unsent_email_and_defers_enrollment():
    """覆盖 AE11：配额 defer 删除未发出邮件，不留 failed 记录，次日重新生成。"""
    conn = FakeQuotaDeferConn()

    result = await TenantMessagingService().defer_email_for_quota(
        conn,
        email_id=str(EMAIL_ID),
        resume_at=RESUME_AT,
    )

    assert result == {
        "email_id": str(EMAIL_ID),
        "status": "deferred_for_quota",
        "resume_at": RESUME_AT.isoformat(),
    }

    delete_sql, delete_params = conn.statements_containing("DELETE FROM emails")[0]
    assert "WHERE id = :email_id AND created_at = :created_at" in " ".join(delete_sql.split())
    assert delete_params == {"email_id": EMAIL_ID, "created_at": EMAIL_CREATED_AT}

    lock_sql, lock_params = conn.statements_containing("UPDATE email_send_locks")[0]
    normalized_lock_sql = " ".join(lock_sql.split())
    assert "status = 'released'" in normalized_lock_sql
    assert "email_id = NULL" in normalized_lock_sql
    assert lock_params == {"email_id": str(EMAIL_ID)}

    enrollment_sql, enrollment_params = conn.statements_containing("UPDATE sequence_enrollments")[0]
    normalized_enrollment_sql = " ".join(enrollment_sql.split())
    assert "next_step_due_at = :resume_at" in normalized_enrollment_sql
    assert "status = 'active'" in normalized_enrollment_sql
    assert "send_attempt_count" not in normalized_enrollment_sql
    assert enrollment_params == {"enrollment_id": ENROLLMENT_ID, "resume_at": RESUME_AT}


@pytest.mark.asyncio
async def test_defer_email_for_quota_releases_reserved_quota_by_plan_domain_lookup():
    """覆盖 AE12：配额 defer 必须回退本地预留配额。"""
    conn = FakeQuotaDeferConn()

    await TenantMessagingService().defer_email_for_quota(
        conn,
        email_id=str(EMAIL_ID),
        resume_at=RESUME_AT,
        now_utc=datetime(2026, 7, 2, 16, 30, tzinfo=UTC),
    )

    quota_sql, quota_params = conn.statements_containing("UPDATE domain_daily_usage")[0]
    normalized_quota_sql = " ".join(quota_sql.split())
    assert "reserved_count = GREATEST(reserved_count - 1, 0)" in normalized_quota_sql
    assert quota_params == {"domain_id": str(DOMAIN_ID), "usage_date": date(2026, 7, 3)}


@pytest.mark.asyncio
async def test_defer_email_for_quota_rejects_already_sent_email_without_writes():
    """配额 defer 只允许处理尚未交付服务商的邮件。"""
    conn = FakeQuotaDeferConn(email=_email_row(sent_at=datetime(2026, 7, 2, 15, 32, tzinfo=UTC)))

    with pytest.raises(AppError) as exc_info:
        await TenantMessagingService().defer_email_for_quota(
            conn,
            email_id=str(EMAIL_ID),
            resume_at=RESUME_AT,
        )

    assert exc_info.value.code == "INVALID_STATE"
    write_statements = [
        sql for sql, _ in conn.executions if sql.lstrip().startswith(("UPDATE", "DELETE", "INSERT"))
    ]
    assert write_statements == []


@pytest.mark.asyncio
async def test_defer_email_for_quota_reports_missing_email():
    """邮件不存在时沿用 _load_email 的明确 NOT_FOUND 错误。"""
    conn = FakeQuotaDeferConn(email=None)

    with pytest.raises(AppError) as exc_info:
        await TenantMessagingService().defer_email_for_quota(
            conn,
            email_id=str(EMAIL_ID),
            resume_at=RESUME_AT,
        )

    assert exc_info.value.code == "NOT_FOUND"
