# Email Send Interval 3s Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将发送计划每封邮件之间的固定发送间隔从 1 秒调整为 3 秒。

**Architecture:** 沿用现有 `send_strategy.interval_seconds` 单一来源，不新增配置项或抽象。同步更新 service 默认值、worker fallback、Alembic 迁移、行为规格和测试。

**Tech Stack:** Python, FastAPI service layer, SQLAlchemy/Alembic, pytest.

## Global Constraints

- 简洁优先，不引入新的配置开关。
- 不覆盖调用方显式传入的合法 `send_strategy`。
- 不执行线上迁移、镜像构建、镜像推送或 Sealos 更新。

---

### Task 1: Backend interval behavior

**Files:**
- Modify: `backend/tests/test_email_send_interval.py`
- Modify: `backend/app/workers/sending.py`
- Modify: `backend/app/services/tenant_messaging_service.py`

**Interfaces:**
- Consumes: 现有 `SendingWorker._delay_seconds(send_strategy: dict | None) -> float`
- Produces: 缺失或无效发送策略 fallback 为 3 秒；新建发送计划默认 `send_strategy` 为 `{"interval_seconds":[3,3]}`。

- [x] **Step 1: Write the failing tests**

Update `backend/tests/test_email_send_interval.py` so the three interval tests expect 3 seconds:

```python
def test_worker_delay_uses_fixed_three_second_interval():
    worker = SendingWorker(random_between=lambda low, high: low)

    assert worker._delay_seconds({"interval_seconds": [3, 3]}) == 3


def test_worker_delay_falls_back_to_three_seconds_for_missing_or_invalid_interval():
    worker = SendingWorker(random_between=lambda low, high: low)

    assert worker._delay_seconds(None) == 3
    assert worker._delay_seconds({"interval_seconds": ["bad"]}) == 3


@pytest.mark.asyncio
async def test_create_sending_plan_defaults_to_three_second_interval():
    svc = TenantMessagingService()
    conn = AsyncMock()

    with patch.object(
        svc,
        "get_sending_plan",
        new_callable=AsyncMock,
        return_value={"id": "plan-001"},
    ), patch.object(svc, "audit") as mock_audit:
        mock_audit.write = AsyncMock()

        await svc.create_sending_plan(
            conn,
            tenant_id="tenant-001",
            user_id="user-001",
            payload={
                "name": "计划",
                "recipient_source": "group",
                "recipient_config": {},
            },
        )

    params = conn.execute.await_args.args[1]
    assert json.loads(params["send_strategy"]) == {"interval_seconds": [3, 3]}
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_email_send_interval.py -q
```

Expected: FAIL because current implementation still returns and saves 1 second.

- [x] **Step 3: Write minimal implementation**

Change `backend/app/workers/sending.py` fallback interval from `[1, 1]` to `[3, 3]`.
Change `backend/app/services/tenant_messaging_service.py` create-plan default from `{"interval_seconds": [1, 1]}` to `{"interval_seconds": [3, 3]}`.

- [x] **Step 4: Run test to verify it passes**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_email_send_interval.py -q
```

Expected: PASS.

### Task 2: Database migration and behavior spec

**Files:**
- Create: `backend/alembic/versions/20260708_0001_set_email_send_interval_3s.py`
- Modify: `backend/03_database/schema.sql`
- Modify: `docs/specs/email-send-interval/spec.md`

**Interfaces:**
- Consumes: Existing Alembic head `20260625_0100`.
- Produces: New Alembic head that sets default/backfill to `[3,3]`; static schema and main spec aligned to 3 seconds.

- [x] **Step 1: Add migration**

Create `backend/alembic/versions/20260708_0001_set_email_send_interval_3s.py`:

```python
"""发送计划默认发送间隔改为 3 秒。

revision: 20260708_0001
down_revision: 20260625_0100
"""

from alembic import op

revision = "20260708_0001"
down_revision = "20260625_0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sending_plans
          ALTER COLUMN send_strategy SET DEFAULT '{"interval_seconds":[3,3]}'::jsonb;
        """
    )
    conn.exec_driver_sql(
        """
        UPDATE sending_plans
        SET send_strategy = jsonb_set(
              COALESCE(send_strategy, '{}'::jsonb),
              '{interval_seconds}',
              '[3,3]'::jsonb,
              true
            )
        WHERE send_strategy IS NULL
           OR send_strategy->'interval_seconds' IS DISTINCT FROM '[3,3]'::jsonb;
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        ALTER TABLE sending_plans
          ALTER COLUMN send_strategy SET DEFAULT '{"interval_seconds":[1,1]}'::jsonb;
        """
    )
    # 不自动恢复既有计划数据：旧区间可能来自用户显式配置或历史默认，无法可靠区分。
```

- [x] **Step 2: Update main spec**

Edit `docs/specs/email-send-interval/spec.md` so all 1-second requirement text, scenarios, and expected values become 3 seconds and `[3, 3]` / `{"interval_seconds":[3,3]}`.

- [x] **Step 3: Update static schema reference**

Edit `backend/03_database/schema.sql` so `sending_plans.send_strategy` defaults to `{"interval_seconds":[3,3]}`.

- [x] **Step 4: Run focused tests**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_email_send_interval.py -q
```

Expected: PASS.

- [x] **Step 5: Verify references are aligned**

Run:

```bash
rg -n "\\[1, 1\\]|\\[1,1\\]|one-second|one second|1 秒|1秒" backend/app backend/tests docs/specs/email-send-interval backend/alembic/versions
```

Expected: Current behavior files do not mention 1 second. Historical migration, downgrade logic, and provenance text may still mention the previous 1-second value.
