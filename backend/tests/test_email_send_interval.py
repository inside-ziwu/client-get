import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.tenant_messaging_service import TenantMessagingService
from app.workers.sending import SendingWorker


def test_worker_delay_uses_fixed_one_second_interval():
    worker = SendingWorker(random_between=lambda low, high: low)

    assert worker._delay_seconds({"interval_seconds": [1, 1]}) == 1


def test_worker_delay_falls_back_to_one_second_for_missing_or_invalid_interval():
    worker = SendingWorker(random_between=lambda low, high: low)

    assert worker._delay_seconds(None) == 1
    assert worker._delay_seconds({"interval_seconds": ["bad"]}) == 1


@pytest.mark.asyncio
async def test_create_sending_plan_defaults_to_one_second_interval():
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
    assert json.loads(params["send_strategy"]) == {"interval_seconds": [1, 1]}
