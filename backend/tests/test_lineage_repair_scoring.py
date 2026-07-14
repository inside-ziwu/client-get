"""修复 worker 的评分待办与事务边界测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers import wmt_lineage_repair


class _AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class TestScoringBacklog:
    def test_backlog_targets_current_active_template_version(self):
        sql = str(wmt_lineage_repair._SQL_SCORING_BACKLOG)

        assert "scoring_templates" in sql
        assert "st.is_active = true" in sql
        assert "scoring_template_versions" in sql
        assert "company_scores" in sql
        assert "cs.id IS NULL" in sql
        assert "t.instance_id = :instance_id" in sql
        assert "LIMIT :limit" in sql

    @pytest.mark.asyncio
    async def test_each_score_uses_independent_transaction_and_failure_is_retained(self):
        read_conn = AsyncMock()
        backlog_result = MagicMock()
        backlog_result.mappings.return_value.all.return_value = [
            {"id": 11, "tenant_id": "tenant-a"},
            {"id": 12, "tenant_id": "tenant-a"},
        ]
        read_conn.execute.return_value = backlog_result

        score_conn_1 = MagicMock()
        score_conn_1.begin_nested.return_value = _AsyncContext(None)
        score_conn_2 = MagicMock()
        score_conn_2.begin_nested.return_value = _AsyncContext(None)

        metrics_conn = AsyncMock()
        metrics_conn.scalar.side_effect = [1, 3]

        engine = MagicMock()
        engine.connect.side_effect = [_AsyncContext(read_conn), _AsyncContext(metrics_conn)]
        engine.begin.side_effect = [_AsyncContext(score_conn_1), _AsyncContext(score_conn_2)]

        scorer = AsyncMock()
        scorer.score_tenant_company.side_effect = [RuntimeError("评分失败"), {"grade": "A"}]

        with patch(
            "app.services.scoring_engine_service.ScoringEngineService",
            return_value=scorer,
        ):
            stats = await wmt_lineage_repair._score_backlog(
                engine,
                instance_id="instance-a",
                limit=2,
            )

        assert engine.begin.call_count == 2
        score_conn_1.begin_nested.assert_called_once()
        score_conn_2.begin_nested.assert_called_once()
        assert stats == {
            "score_attempted": 2,
            "score_succeeded": 1,
            "score_failed": 1,
            "score_failure_ids": [11],
            "score_remaining": 1,
            "score_no_template": 3,
        }


class TestRepairTransactionBoundary:
    @pytest.mark.asyncio
    async def test_fan_out_commits_before_scoring_starts(self):
        repair_conn = AsyncMock()
        repair_stats = {"skipped": False, "fan_out": 2, "deleted_stale": 0, "active_relations": 2}
        engine = MagicMock()
        engine.begin.return_value = _AsyncContext(repair_conn)

        events = []

        async def run_repair(conn):
            assert conn is repair_conn
            events.append("repair")
            return repair_stats

        class TrackingContext(_AsyncContext):
            async def __aexit__(self, exc_type, exc, traceback):
                events.append("commit")
                return False

        engine.begin.return_value = TrackingContext(repair_conn)

        async def run_scoring(*args, **kwargs):
            events.append("score")
            return {
                "score_attempted": 2,
                "score_succeeded": 2,
                "score_failed": 0,
                "score_failure_ids": [],
            }

        with (
            patch.object(wmt_lineage_repair, "run_wmt_lineage_repair_on_connection", run_repair),
            patch.object(wmt_lineage_repair, "_score_backlog", run_scoring),
        ):
            stats = await wmt_lineage_repair.run_wmt_lineage_repair_once(engine)

        assert events == ["repair", "commit", "score"]
        assert stats["score_succeeded"] == 2
