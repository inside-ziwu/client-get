"""开发库事务内验证恢复状态机，结束时回滚。未设置开发库连接则跳过。"""

import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.email_reconciliation_service import EmailReconciliationService
from app.services.tenant_messaging_service import TenantMessagingService

ACCEPTED_AT = datetime(2026, 10, 26, 15, 30, tzinfo=UTC)
RECOVERY_AT = datetime(2026, 10, 27, 2, 0, tzinfo=UTC)
SYNTHETIC_ID = "rehearsal-20261028-" + ("m" * 76) + "@example.com"


def _async_url(raw: str) -> str:
    clean = raw.split("://", 1)[-1]
    base = clean.split("?")[0]
    if "sslmode=require" in raw or "ssl=require" in raw:
        return f"postgresql+asyncpg://{base}?ssl=require"
    return f"postgresql+asyncpg://{base}"


def _require_dev_url() -> str:
    dev_url = os.environ.get("CLIENTGET_DEV_DATABASE_URL")
    if not dev_url:
        pytest.skip("未设置 CLIENTGET_DEV_DATABASE_URL")
    prod_url = os.environ.get("CLIENTGET_PROD_DATABASE_URL")
    dev_host = (urlparse(dev_url).hostname or "").lower()
    prod_host = (urlparse(prod_url).hostname or "").lower() if prod_url else ""
    if not dev_host or (prod_host and dev_host == prod_host):
        pytest.fail("拒绝连接：开发库主机缺失或与生产主机相同")
    if len(SYNTHETIC_ID) != 107:
        pytest.fail(f"合成 ID 长度不是 107：{len(SYNTHETIC_ID)}")
    return dev_url


async def _column_exists(conn, column: str) -> bool:
    row = (
        await conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'email_send_locks'
                  AND column_name = :column
                """
            ),
            {"column": column},
        )
    ).first()
    return row is not None


async def _apply_recovery_ddl(conn) -> str:
    """在当前事务内补齐恢复列。返回 existing、column 或 full。"""
    await conn.execute(text("SET LOCAL lock_timeout = '5s'"))
    await conn.execute(text("SET LOCAL statement_timeout = '60s'"))
    if await _column_exists(conn, "finalize_not_before"):
        return "existing"
    if not await _column_exists(conn, "provider_message_id"):
        await _apply_dispatch_columns(conn)
        return "full"
    await conn.execute(
        text("ALTER TABLE email_send_locks ADD COLUMN finalize_not_before timestamptz")
    )
    return "column"


async def _apply_dispatch_columns(conn) -> None:
    await conn.execute(
        text(
            """
            ALTER TABLE emails
              ALTER COLUMN engagelab_message_id TYPE text
            """
        )
    )
    await conn.execute(
        text(
            """
            ALTER TABLE email_send_locks
              ADD COLUMN provider_message_id text,
              ADD COLUMN provider_accepted_at timestamptz,
              ADD COLUMN dispatch_started_at timestamptz,
              ADD COLUMN quota_usage_date date,
              ADD COLUMN finalize_not_before timestamptz
            """
        )
    )
    await conn.execute(
        text("ALTER TABLE email_send_locks DROP CONSTRAINT email_send_locks_status_check")
    )
    await conn.execute(
        text(
            """
            ALTER TABLE email_send_locks
              ADD CONSTRAINT email_send_locks_status_check
              CHECK (status IN (
                'locked', 'sent', 'failed', 'released',
                'dispatching', 'accepted_pending', 'uncertain'
              ))
            """
        )
    )


async def _count_ids(conn, table: str, ids: list[str]) -> int:
    if not ids:
        return 0
    params = {f"id_{index}": value for index, value in enumerate(ids)}
    holders = ", ".join(f":id_{index}" for index in range(len(ids)))
    row = await conn.execute(
        text(f"SELECT count(*) FROM {table} WHERE id IN ({holders})"),
        params,
    )
    return int(row.scalar_one())


@pytest.mark.asyncio
async def test_dev_recovery_state_machine_rolls_back():
    dev_url = _require_dev_url()
    engine = create_async_engine(_async_url(dev_url))
    service = TenantMessagingService()
    residue = {}
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            try:
                created_columns = await _apply_recovery_ddl(conn)
                residue["ddl_mode"] = created_columns
                instance_id = service._instance_id()
                existing_locks = (
                    await conn.execute(
                        text(
                            """
                            SELECT esl.id, esl.status
                            FROM email_send_locks esl
                            JOIN tenants t ON t.id = esl.tenant_id
                            WHERE t.instance_id = :instance_id
                            """
                        ),
                        {"instance_id": instance_id},
                    )
                ).mappings().all()
                residue["existing_locks"] = {
                    str(row["id"]): row["status"] for row in existing_locks
                }
                plan = (
                    await conn.execute(
                        text(
                            """
                            SELECT sp.id AS plan_id, sp.tenant_id, sp.domain_id, sp.sent_count
                            FROM sending_plans sp
                            JOIN tenants t ON t.id = sp.tenant_id
                            WHERE t.instance_id = :instance_id
                              AND sp.domain_id IS NOT NULL
                              AND EXISTS (
                                SELECT 1 FROM sequence_steps ss WHERE ss.plan_id = sp.id
                              )
                            ORDER BY (
                              SELECT count(*) FROM sequence_steps ss WHERE ss.plan_id = sp.id
                            ) DESC
                            LIMIT 1
                            """
                        ),
                        {"instance_id": instance_id},
                    )
                ).mappings().first()
                if plan is None:
                    pytest.fail("开发库没有可借的发送计划")
                step = (
                    await conn.execute(
                        text(
                            """
                            SELECT id, step_number
                            FROM sequence_steps
                            WHERE plan_id = :plan_id
                            ORDER BY step_number
                            LIMIT 1
                            """
                        ),
                        {"plan_id": plan["plan_id"]},
                    )
                ).mappings().first()
                company = (
                    await conn.execute(
                        text(
                            """
                            SELECT id
                            FROM tenant_companies
                            WHERE tenant_id = :tenant_id
                            LIMIT 1
                            """
                        ),
                        {"tenant_id": plan["tenant_id"]},
                    )
                ).first()
                contacts = (
                    await conn.execute(
                        text(
                            """
                            SELECT tc.id
                            FROM tenant_contacts tc
                            WHERE tc.tenant_id = :tenant_id
                              AND NOT EXISTS (
                                SELECT 1 FROM sequence_enrollments se
                                WHERE se.plan_id = :plan_id
                                  AND se.tenant_contact_id = tc.id
                              )
                              AND NOT EXISTS (
                                SELECT 1 FROM sending_plan_recipients spr
                                WHERE spr.plan_id = :plan_id
                                  AND spr.tenant_contact_id = tc.id
                              )
                            LIMIT 25
                            """
                        ),
                        {"tenant_id": plan["tenant_id"], "plan_id": plan["plan_id"]},
                    )
                ).scalars().all()
                if step is None or company is None or len(contacts) < 25:
                    pytest.fail(
                        "开发库外键不足："
                        f"step={step is not None} company={company is not None} "
                        f"contacts={len(contacts)}"
                    )
                usage_date = ACCEPTED_AT.date()
                domain_id = plan["domain_id"]
                plan_tenant = plan["tenant_id"]
                plan_sent_original = plan["sent_count"]
                residue["plan_id"] = plan["plan_id"]
                residue["plan_sent_original"] = plan_sent_original
                residue["domain_id"] = domain_id
                residue["usage_date"] = usage_date
                usage = (
                    await conn.execute(
                        text(
                            """
                            SELECT reserved_count
                            FROM domain_daily_usage
                            WHERE domain_id = :domain_id
                              AND usage_date = :usage_date
                            """
                        ),
                        {"domain_id": domain_id, "usage_date": usage_date},
                    )
                ).first()
                usage_inserted_id = None
                if usage is None:
                    usage_inserted_id = str(uuid4())
                    await conn.execute(
                        text(
                            """
                            INSERT INTO domain_daily_usage (
                              id, tenant_id, domain_id, usage_date, daily_limit, reserved_count
                            ) VALUES (
                              :id, :tenant_id, :domain_id, :usage_date, 100, 4
                            )
                            """
                        ),
                        {
                            "id": usage_inserted_id,
                            "tenant_id": plan_tenant,
                            "domain_id": domain_id,
                            "usage_date": usage_date,
                        },
                    )
                    reserved_before = 4
                    reserved_original = None
                else:
                    reserved_original = usage[0]
                    await conn.execute(
                        text(
                            """
                            UPDATE domain_daily_usage
                            SET reserved_count = reserved_count + 4
                            WHERE domain_id = :domain_id
                              AND usage_date = :usage_date
                            """
                        ),
                        {"domain_id": domain_id, "usage_date": usage_date},
                    )
                    reserved_before = reserved_original + 4
                residue["usage_inserted_id"] = usage_inserted_id
                residue["reserved_original"] = reserved_original

                email_created_at = datetime(2026, 8, 15, tzinfo=UTC)
                stale_at = RECOVERY_AT - timedelta(minutes=31)
                inserted_recipient_ids: list[str] = []
                inserted_enrollment_ids: list[str] = []
                inserted_lock_ids: list[str] = []
                inserted_email_ids: list[str] = []
                chains = []
                for contact_id in contacts:
                    recipient_id = str(uuid4())
                    enrollment_id = str(uuid4())
                    await conn.execute(
                        text(
                            """
                            INSERT INTO sending_plan_recipients (
                              id, tenant_id, plan_id, tenant_company_id,
                              tenant_contact_id, source_type
                            ) VALUES (
                              :id, :tenant_id, :plan_id, :company_id, :contact_id, 'manual'
                            )
                            """
                        ),
                        {
                            "id": recipient_id,
                            "tenant_id": plan_tenant,
                            "plan_id": plan["plan_id"],
                            "company_id": company[0],
                            "contact_id": contact_id,
                        },
                    )
                    await conn.execute(
                        text(
                            """
                            INSERT INTO sequence_enrollments (
                              id, tenant_id, plan_id, plan_recipient_id, tenant_contact_id
                            ) VALUES (
                              :id, :tenant_id, :plan_id, :recipient_id, :contact_id
                            )
                            """
                        ),
                        {
                            "id": enrollment_id,
                            "tenant_id": plan_tenant,
                            "plan_id": plan["plan_id"],
                            "recipient_id": recipient_id,
                            "contact_id": contact_id,
                        },
                    )
                    inserted_recipient_ids.append(recipient_id)
                    inserted_enrollment_ids.append(enrollment_id)
                    chains.append(
                        {
                            "enrollment_id": enrollment_id,
                            "tenant_id": plan_tenant,
                            "step_id": step["id"],
                            "email_plan_id": plan["plan_id"],
                            "step_number": step["step_number"],
                            "contact_id": contact_id,
                        }
                    )
                unsent, legacy, dispatching, uncertain = chains[:4]
                older = chains[4:24]
                newest = chains[24]

                async def insert_lock(row, **fields):
                    row["id"] = str(uuid4())
                    inserted_lock_ids.append(row["id"])
                    await conn.execute(
                        text(
                            """
                            INSERT INTO email_send_locks (
                              id, tenant_id, enrollment_id, step_id, status, locked_at,
                              email_id, provider_message_id, provider_accepted_at,
                              dispatch_started_at, quota_usage_date
                            ) VALUES (
                              :id, :tenant_id, :enrollment_id, :step_id, :status, :locked_at,
                              :email_id, :message_id, :accepted_at, :started_at, :usage_date
                            )
                            """
                        ),
                        {
                            "id": row["id"],
                            "tenant_id": row["tenant_id"],
                            "enrollment_id": row["enrollment_id"],
                            "step_id": row["step_id"],
                            "status": fields["status"],
                            "locked_at": fields.get("locked_at", stale_at),
                            "email_id": fields.get("email_id"),
                            "message_id": fields.get("message_id"),
                            "accepted_at": fields.get("accepted_at"),
                            "started_at": fields.get("started_at"),
                            "usage_date": fields.get("usage_date"),
                        },
                    )

                await insert_lock(
                    unsent,
                    status="locked",
                    locked_at=stale_at,
                    usage_date=usage_date,
                )
                await insert_lock(legacy, status="locked", locked_at=stale_at)
                dispatching["email_id"] = str(uuid4())
                await insert_lock(
                    dispatching,
                    status="dispatching",
                    locked_at=stale_at,
                    email_id=dispatching["email_id"],
                    started_at=stale_at,
                    usage_date=usage_date,
                )
                await insert_lock(uncertain, status="uncertain", locked_at=stale_at)
                for index, row in enumerate(older):
                    row["email_id"] = str(uuid4())
                    await insert_lock(
                        row,
                        status="accepted_pending",
                        email_id=row["email_id"],
                        message_id=f"pending-{index:02d}-example",
                        accepted_at=ACCEPTED_AT + timedelta(seconds=index),
                        started_at=stale_at,
                    )
                newest["email_id"] = str(uuid4())
                newest["created_at"] = email_created_at
                inserted_email_ids.append(newest["email_id"])
                await conn.execute(
                    text(
                        """
                        INSERT INTO emails (
                          id, created_at, tenant_id, plan_id, step_id, step_number,
                          enrollment_id, tenant_contact_id, from_email, to_email,
                          subject, body_html, status
                        ) VALUES (
                          :id, :created_at, :tenant_id, :plan_id, :step_id, :step_number,
                          :enrollment_id, :contact_id, 'sender@example.com',
                          'buyer@example.com', 'recovery', '<p>recovery</p>', 'queued'
                        )
                        """
                    ),
                    {
                        "id": newest["email_id"],
                        "created_at": email_created_at,
                        "tenant_id": newest["tenant_id"],
                        "plan_id": newest["email_plan_id"],
                        "step_id": newest["step_id"],
                        "step_number": newest["step_number"],
                        "enrollment_id": newest["enrollment_id"],
                        "contact_id": newest["contact_id"],
                    },
                )
                await insert_lock(
                    newest,
                    status="accepted_pending",
                    email_id=newest["email_id"],
                    message_id=SYNTHETIC_ID,
                    accepted_at=ACCEPTED_AT + timedelta(seconds=20),
                    started_at=stale_at,
                )
                residue["recipient_ids"] = inserted_recipient_ids
                residue["enrollment_ids"] = inserted_enrollment_ids
                residue["lock_ids"] = inserted_lock_ids
                residue["email_ids"] = inserted_email_ids

                released = await service.release_unsent_locks(
                    conn, as_of=RECOVERY_AT, stale_minutes=30
                )
                assert released["recovered_count"] == 1
                assert released["enrollment_ids"] == [str(unsent["enrollment_id"])]
                again = await service.release_unsent_locks(
                    conn, as_of=RECOVERY_AT, stale_minutes=30
                )
                assert again["recovered_count"] == 0
                statuses = {}
                for row_id in (
                    legacy["id"],
                    dispatching["id"],
                    uncertain["id"],
                    newest["id"],
                ):
                    status = (
                        await conn.execute(
                            text("SELECT status FROM email_send_locks WHERE id = :id"),
                            {"id": row_id},
                        )
                    ).scalar_one()
                    statuses[str(row_id)] = status
                assert statuses[str(legacy["id"])] == "locked"
                assert statuses[str(dispatching["id"])] == "dispatching"
                assert statuses[str(uncertain["id"])] == "uncertain"
                assert statuses[str(newest["id"])] == "accepted_pending"
                reserved_after = (
                    await conn.execute(
                        text(
                            """
                            SELECT reserved_count
                            FROM domain_daily_usage
                            WHERE domain_id = :domain_id
                              AND usage_date = :usage_date
                            """
                        ),
                        {"domain_id": domain_id, "usage_date": usage_date},
                    )
                ).scalar_one()
                assert reserved_after == reserved_before - 1

                plan_before = (
                    await conn.execute(
                        text("SELECT sent_count FROM sending_plans WHERE id = :plan_id"),
                        {"plan_id": newest["email_plan_id"]},
                    )
                ).scalar_one()
                next_step = (
                    await conn.execute(
                        text(
                            """
                            SELECT delay_days
                            FROM sequence_steps
                            WHERE plan_id = :plan_id
                              AND step_number = :step_number
                            """
                        ),
                        {
                            "plan_id": newest["email_plan_id"],
                            "step_number": newest["step_number"] + 1,
                        },
                    )
                ).first()

                first_page = await service.list_accepted_pending(
                    conn,
                    limit=20,
                    as_of=RECOVERY_AT,
                    lease_until=RECOVERY_AT + timedelta(seconds=15),
                )
                assert len(first_page) == 20
                assert str(newest["email_id"]) not in {row["email_id"] for row in first_page}
                for row in first_page:
                    await service.defer_accepted_pending(
                        conn,
                        email_id=row["email_id"],
                        tenant_id=row["tenant_id"],
                        enrollment_id=row["enrollment_id"],
                        step_id=row["step_id"],
                        not_before=RECOVERY_AT + timedelta(seconds=60),
                    )
                second_page = await service.list_accepted_pending(
                    conn,
                    limit=20,
                    as_of=RECOVERY_AT,
                    lease_until=RECOVERY_AT + timedelta(seconds=15),
                )
                assert [row["email_id"] for row in second_page] == [str(newest["email_id"])]
                assert second_page[0]["provider_accepted_at"] == ACCEPTED_AT + timedelta(seconds=20)

                sent = await service.mark_email_sent(
                    conn,
                    email_id=str(newest["email_id"]),
                    payload={"engagelab_message_id": SYNTHETIC_ID, "sent_at": RECOVERY_AT},
                )
                assert sent.get("duplicate") is not True
                assert sent["status"] == "sent"
                duplicate = await service.mark_email_sent(
                    conn,
                    email_id=str(newest["email_id"]),
                    payload={"engagelab_message_id": SYNTHETIC_ID, "sent_at": RECOVERY_AT},
                )
                assert duplicate["duplicate"] is True

                email_row = (
                    await conn.execute(
                        text(
                            """
                            SELECT sent_at, status, length(engagelab_message_id) AS id_length
                            FROM emails
                            WHERE id = :email_id
                              AND created_at = :created_at
                              AND tenant_id = :tenant_id
                            """
                        ),
                        {
                            "email_id": newest["email_id"],
                            "created_at": newest["created_at"],
                            "tenant_id": newest["tenant_id"],
                        },
                    )
                ).mappings().one()
                enrollment_after = (
                    await conn.execute(
                        text(
                            """
                            SELECT current_step, last_step_sent_at, next_step_due_at,
                                   updated_at, completed_at
                            FROM sequence_enrollments
                            WHERE id = :enrollment_id
                              AND tenant_id = :tenant_id
                            """
                        ),
                        {
                            "enrollment_id": newest["enrollment_id"],
                            "tenant_id": newest["tenant_id"],
                        },
                    )
                ).mappings().one()
                plan_after = (
                    await conn.execute(
                        text("SELECT sent_count FROM sending_plans WHERE id = :plan_id"),
                        {"plan_id": newest["email_plan_id"]},
                    )
                ).scalar_one()
                send_at = ACCEPTED_AT + timedelta(seconds=20)
                assert email_row["sent_at"] == send_at
                assert email_row["id_length"] == 107
                assert email_row["status"] == "sent"
                assert enrollment_after["last_step_sent_at"] == send_at
                assert enrollment_after["updated_at"] > send_at
                if next_step is None:
                    assert enrollment_after["completed_at"] == send_at
                    assert enrollment_after["next_step_due_at"] is None
                else:
                    assert enrollment_after["current_step"] == newest["step_number"] + 1
                    assert enrollment_after["next_step_due_at"] == send_at + timedelta(
                        days=next_step[0]
                    )
                assert plan_after == plan_before + 1
                grouped = EmailReconciliationService()._group_by_send_date_cst(
                    [{"sent_at": email_row["sent_at"], "engagelab_message_id": "length-only"}]
                )
                assert list(grouped) == ["2026-10-26"]

                await service.record_provider_acceptance(
                    conn,
                    email_id=str(dispatching["email_id"]),
                    tenant_id=str(dispatching["tenant_id"]),
                    enrollment_id=str(dispatching["enrollment_id"]),
                    step_id=str(dispatching["step_id"]),
                    provider_message_id="receipt-example",
                    accepted_at=ACCEPTED_AT,
                )
                await service.record_provider_acceptance(
                    conn,
                    email_id=str(dispatching["email_id"]),
                    tenant_id=str(dispatching["tenant_id"]),
                    enrollment_id=str(dispatching["enrollment_id"]),
                    step_id=str(dispatching["step_id"]),
                    provider_message_id="receipt-example",
                    accepted_at=RECOVERY_AT,
                )
                receipt_at = (
                    await conn.execute(
                        text(
                            """
                            SELECT provider_accepted_at
                            FROM email_send_locks
                            WHERE id = :id
                            """
                        ),
                        {"id": dispatching["id"]},
                    )
                ).scalar_one()
                assert receipt_at == ACCEPTED_AT
            finally:
                await transaction.rollback()

            residue["message_column"] = await _column_exists(conn, "finalize_not_before")
            residue["constraint"] = (
                await conn.execute(
                    text(
                        """
                        SELECT pg_get_constraintdef(oid)
                        FROM pg_constraint
                        WHERE conname = 'email_send_locks_status_check'
                        """
                    )
                )
            ).scalar_one()
            message_type = (
                await conn.execute(
                    text(
                        """
                        SELECT data_type, character_maximum_length
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'emails'
                          AND column_name = 'engagelab_message_id'
                        """
                    )
                )
            ).first()
            residue["message_type"] = (message_type[0], message_type[1])
            residue["synthetic"] = (
                await conn.execute(
                    text(
                        """
                        SELECT count(*)
                        FROM emails
                        WHERE engagelab_message_id = :message_id
                        """
                    ),
                    {"message_id": SYNTHETIC_ID},
                )
            ).scalar_one()
            residue["locks_left"] = await _count_ids(
                conn, "email_send_locks", residue["lock_ids"]
            )
            residue["enrollments_left"] = await _count_ids(
                conn, "sequence_enrollments", residue["enrollment_ids"]
            )
            residue["recipients_left"] = await _count_ids(
                conn, "sending_plan_recipients", residue["recipient_ids"]
            )
            residue["emails_left"] = await _count_ids(conn, "emails", residue["email_ids"])
            if residue["usage_inserted_id"] is None:
                residue["reserved_after"] = (
                    await conn.execute(
                        text(
                            """
                            SELECT reserved_count
                            FROM domain_daily_usage
                            WHERE domain_id = :domain_id
                              AND usage_date = :usage_date
                            """
                        ),
                        {
                            "domain_id": residue["domain_id"],
                            "usage_date": residue["usage_date"],
                        },
                    )
                ).scalar_one()
            else:
                residue["usage_left"] = await _count_ids(
                    conn, "domain_daily_usage", [residue["usage_inserted_id"]]
                )
            residue["plan_sent_after"] = (
                await conn.execute(
                    text("SELECT sent_count FROM sending_plans WHERE id = :plan_id"),
                    {"plan_id": residue["plan_id"]},
                )
            ).scalar_one()
            restored = (
                await conn.execute(
                    text(
                        """
                        SELECT esl.id, esl.status
                        FROM email_send_locks esl
                        JOIN tenants t ON t.id = esl.tenant_id
                        WHERE t.instance_id = :instance_id
                        """
                    ),
                    {"instance_id": service._instance_id()},
                )
            ).mappings().all()
            residue["locks_now"] = {str(row["id"]): row["status"] for row in restored}
    finally:
        await engine.dispose()

    if residue["ddl_mode"] == "existing":
        assert residue["message_column"] is True
    else:
        assert residue["message_column"] is False
    if residue["ddl_mode"] == "full":
        assert "accepted_pending" not in residue["constraint"]
        assert "dispatching" not in residue["constraint"]
        assert residue["message_type"] == ("character varying", 100)
    assert residue["synthetic"] == 0
    assert residue["locks_left"] == 0
    assert residue["enrollments_left"] == 0
    assert residue["recipients_left"] == 0
    assert residue["emails_left"] == 0
    if residue["usage_inserted_id"] is None:
        assert residue["reserved_after"] == residue["reserved_original"]
    else:
        assert residue["usage_left"] == 0
    assert residue["plan_sent_after"] == residue["plan_sent_original"]
    assert residue["locks_now"] == residue["existing_locks"]
