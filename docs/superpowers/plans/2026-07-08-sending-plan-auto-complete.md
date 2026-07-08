# Sending Plan Auto Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当 `running` 发送计划下不存在任何 `active` 或 `paused` enrollment 时，自动将该计划推进为 `completed`，并回填数据库中已经满足该条件的历史计划。

**Architecture:** 新增一个计划完成聚合 helper。所有会把 enrollment 推进到终局状态的运行时路径，在更新 enrollment 后调用该 helper。新增 Alembic 回填迁移，用同一 SQL 条件完成历史 `running` 计划。

**Tech Stack:** Python, FastAPI service layer, SQLAlchemy text SQL, Alembic, pytest.

## Global Constraints

- 计划完成只看 `sequence_enrollments.status` 聚合结果。
- 任意 `active` enrollment 存在时，计划不得完成。
- 任意 `paused` enrollment 存在时，计划不得完成。
- 非 `active` / `paused` enrollment 不阻塞计划完成。
- 计划必须至少存在 1 条 enrollment 才能自动完成。
- 自动完成只作用于 `sending_plans.status = 'running'`。
- 不改变条件型步骤的现有状态机；仍是 `active` 的 enrollment 必须继续阻塞计划完成。
- 不自动执行生产迁移、镜像构建、镜像推送或 Sealos 更新。

---

## Task 1: Shared completion helper

**Files:**
- Create: `backend/app/services/sending_plan_completion.py`
- Create: `backend/tests/test_sending_plan_auto_complete.py`

**Interfaces:**
- Produces: `complete_running_plan_if_finished(conn: AsyncConnection, *, plan_id: str) -> bool`
- Consumes: SQLAlchemy `AsyncConnection.execute`

- [x] **Step 1: Write failing helper tests**

Create tests that assert `complete_running_plan_if_finished`:

- updates only `sending_plans.status = 'running'`
- requires at least one enrollment via `EXISTS`
- requires no `sequence_enrollments.status IN ('active', 'paused')` via `NOT EXISTS`
- sets `status = 'completed'`
- sets `completed_at = COALESCE(sp.completed_at, now())`
- updates `updated_at`
- returns `True` when `RETURNING sp.id` yields a row
- returns `False` when no row is updated

- [x] **Step 2: Run helper test and confirm red**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py -q
```

Expected: fails because `app.services.sending_plan_completion` does not exist.

- [x] **Step 3: Implement helper**

Create `backend/app/services/sending_plan_completion.py`:

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def complete_running_plan_if_finished(conn: AsyncConnection, *, plan_id: str) -> bool:
    result = await conn.execute(
        text(
            """
            UPDATE sending_plans sp
            SET status = 'completed',
                completed_at = COALESCE(sp.completed_at, now()),
                updated_at = now()
            WHERE sp.id = :plan_id
              AND sp.status = 'running'
              AND EXISTS (
                SELECT 1
                FROM sequence_enrollments se
                WHERE se.plan_id = sp.id
              )
              AND NOT EXISTS (
                SELECT 1
                FROM sequence_enrollments se
                WHERE se.plan_id = sp.id
                  AND se.status IN ('active', 'paused')
              )
            RETURNING sp.id
            """
        ),
        {"plan_id": plan_id},
    )
    return result.mappings().first() is not None
```

- [x] **Step 4: Run helper test and confirm green**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py -q
```

Expected: PASS.

---

## Task 2: Runtime checks in messaging service

**Files:**
- Modify: `backend/tests/test_sending_plan_auto_complete.py`
- Modify: `backend/app/services/tenant_messaging_service.py`

**Interfaces:**
- Consumes: `complete_running_plan_if_finished(conn, plan_id=...) -> bool`
- Produces: Last-step success checks plan completion.
- Produces: Permanent failure and retry-exhausted failure check plan completion.

- [x] **Step 1: Add failing tests**

Add tests proving:

- `mark_email_sent` calls `complete_running_plan_if_finished` after the current email is the last sequence step and the enrollment is set to `completed`.
- `mark_email_sent` does not call the helper when there is a next sequence step.
- `mark_email_failed` calls the helper after permanent failure sets the enrollment to `failed`.
- `mark_email_failed` calls the helper after retry exhaustion sets the enrollment to `failed`.
- `mark_email_failed` does not call the helper when a retry is scheduled and enrollment remains active.

- [x] **Step 2: Run tests and confirm red**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py -q
```

Expected: fails because `tenant_messaging_service` does not import or call the helper.

- [x] **Step 3: Import helper**

In `backend/app/services/tenant_messaging_service.py`, import:

```python
from app.services.sending_plan_completion import complete_running_plan_if_finished
```

- [x] **Step 4: Call helper after last-step success**

In `TenantMessagingService.mark_email_sent`, call:

```python
await complete_running_plan_if_finished(conn, plan_id=email["plan_id"])
```

Only call it in the `next_row is None` branch, after the enrollment has been updated to `completed` and after the plan `sent_count` update has run.

- [x] **Step 5: Call helper after terminal failures**

In `TenantMessagingService.mark_email_failed`, call the helper:

- after the permanent-failure branch updates the enrollment to `failed`
- after retry exhaustion updates the enrollment to `failed`

Do not call it when a retry is scheduled.

- [x] **Step 6: Run focused tests**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py tests/test_sending_worker.py -q
```

Expected: PASS.

---

## Task 3: Runtime checks in webhook and reconciliation paths

**Files:**
- Modify: `backend/tests/test_sending_plan_auto_complete.py`
- Modify: `backend/app/services/webhook_service.py`
- Modify: `backend/app/services/email_reconciliation_service.py`

**Interfaces:**
- Consumes: `complete_running_plan_if_finished(conn, plan_id=...) -> bool`
- Produces: Webhook terminal events check plan completion.
- Produces: Reconciliation bounce events check plan completion.

- [x] **Step 1: Add failing tests**

Add tests proving:

- EngageLab webhook events `replied`、`bounced`、`unsubscribed` call `complete_running_plan_if_finished` after enrollment terminal status update.
- Non-terminal webhook events such as `delivered` do not call the helper.
- Reconciliation `_apply_bounced` calls the helper after enrollment becomes `bounced`.

- [x] **Step 2: Run tests and confirm red**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py -q
```

Expected: fails because these service paths do not import or call the helper.

- [x] **Step 3: Include `plan_id` in email rows**

In `backend/app/services/webhook_service.py`, include `plan_id` in the email lookup:

```sql
SELECT id, created_at, tenant_id, plan_id, enrollment_id, ...
```

In `backend/app/services/email_reconciliation_service.py`, include `e.plan_id` in the reconciliation email query.

- [x] **Step 4: Import and call helper**

Import `complete_running_plan_if_finished` in both service files.

Call it only after a terminal enrollment update and only when `email["plan_id"]` is present.

- [x] **Step 5: Run focused tests**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py tests/test_webhook_service_engagelab_provider_event_id.py -q
```

Expected: PASS.

---

## Task 4: Historical data backfill migration

**Files:**
- Create: `backend/alembic/versions/20260708_0002_complete_finished_sending_plans.py`
- Modify: `backend/tests/test_sending_plan_auto_complete.py`

**Interfaces:**
- Produces: One-time data migration that completes eligible historical `running` plans.

- [x] **Step 1: Add failing migration guard test**

Add a test that reads `alembic/versions/20260708_0002_complete_finished_sending_plans.py` and asserts the migration SQL includes:

- `UPDATE sending_plans sp`
- `SET status = 'completed'`
- `completed_at = COALESCE(sp.completed_at, now())`
- `sp.status = 'running'`
- `EXISTS`
- `NOT EXISTS`
- `se.status IN ('active', 'paused')`

Also assert the migration only updates `sending_plans`; it must not update `sequence_enrollments`.

- [x] **Step 2: Run migration guard test and confirm red**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py::test_backfill_migration_completes_finished_running_plans -q
```

Expected: fails because migration file does not exist.

- [x] **Step 3: Create migration**

Create `backend/alembic/versions/20260708_0002_complete_finished_sending_plans.py`.

Use current Alembic head as `down_revision`; if `20260708_0001` is still the head, use:

```python
revision = "20260708_0002"
down_revision = "20260708_0001"
```

Upgrade SQL:

```sql
UPDATE sending_plans sp
SET status = 'completed',
    completed_at = COALESCE(sp.completed_at, now()),
    updated_at = now()
WHERE sp.status = 'running'
  AND EXISTS (
    SELECT 1
    FROM sequence_enrollments se
    WHERE se.plan_id = sp.id
  )
  AND NOT EXISTS (
    SELECT 1
    FROM sequence_enrollments se
    WHERE se.plan_id = sp.id
      AND se.status IN ('active', 'paused')
  );
```

Downgrade should be a no-op because the data correction is not safely reversible.

- [x] **Step 4: Run migration guard test**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py::test_backfill_migration_completes_finished_running_plans -q
```

Expected: PASS.

---

## Task 5: Final verification

**Files:**
- Verify all files changed in Tasks 1-4.

**Interfaces:**
- Consumes: Tasks 1-4 completed.
- Produces: Verified implementation ready for review.

- [x] **Step 1: Run focused test suite**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_sending_plan_auto_complete.py tests/test_sending_worker.py tests/test_webhook_service_engagelab_provider_event_id.py -q
```

Expected: PASS.

- [x] **Step 2: Verify Alembic chain**

Run:

```bash
cd backend && .venv/bin/python -m alembic heads
```

Expected: the new migration is on the intended head chain; no unintended extra head is introduced.

- [x] **Step 3: Report completion**

Summarize:

- helper behavior
- runtime call sites
- migration backfill condition
- tests run and result

Check off all completed boxes in this file after implementation and verification succeed.
