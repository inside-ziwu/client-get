"""分区维护：提前多月预建，DEFAULT 冲突只跳过该月不阻塞启动。"""

import asyncio
import re
from contextlib import asynccontextmanager
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.db import partitions
from app.db.partitions import ensure_partitions, run_partition_maintenance_loop


class _FakeEngine:
    def __init__(self, conflict: set[str] | None = None):
        self.conflict = conflict or set()
        self.created: list[str] = []

    @asynccontextmanager
    async def begin(self):
        engine = self

        class _Conn:
            async def execute(self, stmt):
                name = re.search(r"EXISTS (\w+)", str(stmt)).group(1)
                if name in engine.conflict:
                    raise IntegrityError(str(stmt), None, Exception("default violated"))
                engine.created.append(name)

        yield _Conn()


async def test_creates_current_plus_three_months_across_year_boundary():
    engine = _FakeEngine()
    await ensure_partitions(engine, today=date(2026, 11, 15))

    months = ["2026_11", "2026_12", "2027_01", "2027_02"]
    assert engine.created == [f"audit_logs_p_{m}" for m in months] + [
        f"emails_p_{m}" for m in months
    ]


async def test_default_partition_conflict_skips_only_that_month():
    engine = _FakeEngine(conflict={"emails_p_2026_10"})
    await ensure_partitions(engine, today=date(2026, 10, 5))

    assert "emails_p_2026_10" not in engine.created
    assert {"emails_p_2026_11", "emails_p_2027_01", "audit_logs_p_2026_10"} <= set(engine.created)


async def test_maintenance_loop_reruns_and_survives_failures(monkeypatch):
    calls = 0
    stop = asyncio.Event()

    async def fake_ensure(_engine):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("db down")
        if calls == 2:
            stop.set()

    monkeypatch.setattr(partitions, "ensure_partitions", fake_ensure)
    await asyncio.wait_for(
        run_partition_maintenance_loop(object(), stop_event=stop, interval_seconds=0),
        timeout=1,
    )
    assert calls == 2
