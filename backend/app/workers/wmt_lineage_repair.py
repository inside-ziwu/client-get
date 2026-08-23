"""WMT 客户池关系修复与租户评分补齐。

外部流程可能重建 ``waimaotong_clean_companies``，因此本 worker 定期：
1. 向当前实例的活跃 PCB 租户分发客户公池（排除手工私有行）。
2. 删除当前实例中指向已不存在公司的关系。
3. 在关系事务提交后，分别用租户的活跃模板补齐评分。
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from time import monotonic
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.utils.industry import PCB_INDUSTRY_ALIASES as _PCB_INDUSTRY_ALIASES

logger = logging.getLogger(__name__)

_ADVISORY_LOCK_KEY = 2_026_052_101
_SCORING_BATCH_SIZE = 500


_SQL_FAN_OUT_FULL_POOL = text("""
    INSERT INTO tenant_companies
      (tenant_id, clean_company_id, business_status, data_status)
    SELECT
      t.id,
      wc.id,
      'new',
      CASE
        WHEN COALESCE(wc.contacts_count, 0) = 0 THEN 'missing_contacts'
        WHEN wc.domain IS NULL AND wc.industry IS NULL AND wc.product_tags IS NULL
          THEN 'insufficient_data'
        ELSE 'ready'
      END
    FROM tenants t
    JOIN waimaotong_clean_companies wc
      ON (wc.source_id IS NULL OR wc.source_id NOT LIKE 'manual-%')
    WHERE t.status = 'active'
      AND lower(trim(t.industry)) = ANY(:industry_aliases)
      AND t.instance_id = :instance_id
    ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
    SET data_status = EXCLUDED.data_status,
        updated_at = CASE
          WHEN tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
          THEN now()
          ELSE tenant_companies.updated_at
        END
    WHERE tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
""")

_SQL_DELETE_STALE_RELATIONS = text("""
    DELETE FROM tenant_companies tc
    USING tenants t
    WHERE t.id = tc.tenant_id
      AND t.instance_id = :instance_id
      AND NOT EXISTS (
        SELECT 1
        FROM waimaotong_clean_companies wc
        WHERE wc.id = tc.clean_company_id
      )
""")

_SQL_ACTIVE_RELATION_COUNT = text("""
    SELECT count(*)
    FROM tenant_companies tc
    JOIN tenants t ON t.id = tc.tenant_id
    JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
    WHERE t.instance_id = :instance_id
      AND t.status = 'active'
      AND lower(trim(t.industry)) = ANY(:industry_aliases)
""")

_SQL_SCORING_BACKLOG = text("""
    SELECT tc.id, tc.tenant_id
    FROM tenant_companies tc
    JOIN tenants t ON t.id = tc.tenant_id
    JOIN scoring_templates st
      ON st.tenant_id = tc.tenant_id
     AND st.is_active = true
    JOIN LATERAL (
      SELECT stv.id
      FROM scoring_template_versions stv
      WHERE stv.template_id = st.id
        AND stv.tenant_id = tc.tenant_id
      ORDER BY stv.version DESC
      LIMIT 1
    ) current_version ON true
    LEFT JOIN company_scores cs
      ON cs.tenant_company_id = tc.id
     AND cs.template_version_id = current_version.id
     AND cs.is_retry = false
    WHERE t.instance_id = :instance_id
      AND t.status = 'active'
      AND lower(trim(t.industry)) = ANY(:industry_aliases)
      AND cs.id IS NULL
    ORDER BY tc.id
    LIMIT :limit
""")

_SQL_SCORING_REMAINING_COUNT = text("""
    SELECT count(*)
    FROM (
      SELECT tc.id
      FROM tenant_companies tc
      JOIN tenants t ON t.id = tc.tenant_id
      JOIN scoring_templates st
        ON st.tenant_id = tc.tenant_id
       AND st.is_active = true
      JOIN LATERAL (
        SELECT stv.id
        FROM scoring_template_versions stv
        WHERE stv.template_id = st.id
          AND stv.tenant_id = tc.tenant_id
        ORDER BY stv.version DESC
        LIMIT 1
      ) current_version ON true
      LEFT JOIN company_scores cs
        ON cs.tenant_company_id = tc.id
       AND cs.template_version_id = current_version.id
       AND cs.is_retry = false
      WHERE t.instance_id = :instance_id
        AND t.status = 'active'
        AND lower(trim(t.industry)) = ANY(:industry_aliases)
        AND cs.id IS NULL
    ) backlog
""")

_SQL_NO_TEMPLATE_COUNT = text("""
    SELECT count(*)
    FROM tenant_companies tc
    JOIN tenants t ON t.id = tc.tenant_id
    WHERE t.instance_id = :instance_id
      AND t.status = 'active'
      AND lower(trim(t.industry)) = ANY(:industry_aliases)
      AND NOT EXISTS (
        SELECT 1
        FROM scoring_templates st
        WHERE st.tenant_id = tc.tenant_id
          AND st.is_active = true
          AND EXISTS (
            SELECT 1
            FROM scoring_template_versions stv
            WHERE stv.template_id = st.id
              AND stv.tenant_id = tc.tenant_id
          )
      )
""")


async def _score_backlog(
    engine: AsyncEngine,
    *,
    instance_id: str,
    limit: int = _SCORING_BATCH_SIZE,
) -> dict:
    """按当前模板版本补评；每家公司使用独立事务。"""
    params = {
        "instance_id": instance_id,
        "industry_aliases": _PCB_INDUSTRY_ALIASES,
        "limit": limit,
    }
    async with engine.connect() as conn:
        result = await conn.execute(_SQL_SCORING_BACKLOG, params)
        backlog = result.mappings().all()

    from app.services.scoring_engine_service import ScoringEngineService

    scorer = ScoringEngineService()
    succeeded = 0
    failure_ids: list[int] = []
    for row in backlog:
        tc_id = int(row["id"])
        try:
            async with engine.begin() as conn:
                async with conn.begin_nested():
                    score = await scorer.score_tenant_company(
                        conn,
                        tenant_id=str(row["tenant_id"]),
                        tenant_company_id=tc_id,
                    )
                    if score is None:
                        raise RuntimeError("租户无可用评分模板或公司关系已消失")
            succeeded += 1
        except Exception:
            failure_ids.append(tc_id)
            logger.exception("wmt_lineage_repair: tenant_company_id=%s 补评失败", tc_id)

    metric_params = {
        "instance_id": instance_id,
        "industry_aliases": _PCB_INDUSTRY_ALIASES,
    }
    async with engine.connect() as conn:
        remaining = int(await conn.scalar(_SQL_SCORING_REMAINING_COUNT, metric_params) or 0)
        no_template = int(await conn.scalar(_SQL_NO_TEMPLATE_COUNT, metric_params) or 0)

    return {
        "score_attempted": len(backlog),
        "score_succeeded": succeeded,
        "score_failed": len(failure_ids),
        "score_failure_ids": failure_ids,
        "score_remaining": remaining,
        "score_no_template": no_template,
    }


async def run_wmt_lineage_repair_once(engine: AsyncEngine) -> dict:
    """执行单轮关系修复，提交后再独立执行补评。"""
    run_id = uuid4().hex[:12]
    started_at = monotonic()
    async with engine.begin() as conn:
        stats = await run_wmt_lineage_repair_on_connection(conn)

    if stats["skipped"]:
        logger.info(
            "wmt_lineage_repair run_id=%s phase=skipped duration_ms=%d stats=%s",
            run_id,
            int((monotonic() - started_at) * 1000),
            stats,
        )
        return stats

    scoring_stats = await _score_backlog(
        engine,
        instance_id=get_settings().instance_id,
    )
    stats.update(scoring_stats)
    logger.info(
        "wmt_lineage_repair run_id=%s phase=complete duration_ms=%d stats=%s",
        run_id,
        int((monotonic() - started_at) * 1000),
        stats,
    )
    return stats


async def run_wmt_lineage_repair_on_connection(conn) -> dict:
    """在已有事务中修复关系；不在此事务内执行评分。"""
    instance_id = get_settings().instance_id
    locked = await conn.scalar(
        text(
            "SELECT pg_try_advisory_xact_lock("
            "CAST(:key AS bigint) + pg_catalog.hashtext(:instance_id))"
        ),
        {"key": _ADVISORY_LOCK_KEY, "instance_id": instance_id},
    )
    if not locked:
        logger.info("wmt_lineage_repair: 其他 worker 正在修复当前实例，跳过本轮")
        return {"skipped": True, "reason": "lock_busy"}

    params = {
        "industry_aliases": _PCB_INDUSTRY_ALIASES,
        "instance_id": instance_id,
    }
    fan_out = await conn.execute(_SQL_FAN_OUT_FULL_POOL, params)
    deleted_stale = await conn.execute(
        _SQL_DELETE_STALE_RELATIONS,
        {"instance_id": instance_id},
    )
    active_relations = int(await conn.scalar(_SQL_ACTIVE_RELATION_COUNT, params) or 0)

    return {
        "skipped": False,
        "fan_out": fan_out.rowcount,
        "deleted_stale": deleted_stale.rowcount,
        "active_relations": active_relations,
    }


async def run_wmt_lineage_repair_loop(
    engine: AsyncEngine,
    *,
    interval_seconds: int,
    stop_event: asyncio.Event,
) -> None:
    """后台循环。启动后立即跑一轮，之后按间隔自愈。"""
    interval = max(interval_seconds, 30)
    while not stop_event.is_set():
        try:
            await run_wmt_lineage_repair_once(engine)
        except Exception:
            logger.exception("wmt_lineage_repair: repair iteration failed")

        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
