"""WMT 血缘与 tenant 可见关系自愈。

外部流程可能重建 waimaotong_clean_companies，导致 tenant_companies
仍指向过期的 WMT bigint id。本 worker 幂等执行四类自愈动作：
1. 规范并回填关键词血缘（clean path → raw fallback）
2. 关键词 fan-out（tenant_keyword 订阅匹配）
3. 行业 fan-out（批次标签 → PCB 租户）
4. 清理 stale 关系
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services.collection_source import KEYWORD_TAG_JSONB

logger = logging.getLogger(__name__)

_ADVISORY_LOCK_KEY = 2_026_052_101

# 批次标签 → 行业 的硬编码规则；第二行业出现时再数据化。
# 新租户行业写法若不在别名表内会漏推，新增行业别名需同步登记此处。
_PCB_INDUSTRY_ALIASES = ["pcb", "电路板"]


_SQL_NORMALIZE_KEYWORD_MASTER_IDS = text("""
    UPDATE waimaotong_clean_companies
    SET keyword_master_ids = '{}'::uuid[]
    WHERE keyword_master_ids IS NULL
""")

_SQL_BACKFILL_CLEAN_PATH = text("""
    UPDATE waimaotong_clean_companies wc
    SET keyword_master_ids = sub.km_ids
    FROM (
        SELECT
            wc2.id AS wmt_clean_id,
            array_agg(DISTINCT unnested_km) AS km_ids
        FROM waimaotong_clean_companies wc2
        JOIN waimaotong_raw_companies wr
            ON wr.sys_company_id = wc2.sys_company_id
        JOIN lixiaoyun_api_clean_companies lxc
            ON lower(trim(lxc.entname_eng)) = lower(trim(wr.source_competitor))
        , unnest(lxc.keyword_master_ids) AS unnested_km
        WHERE wc2.sys_company_id IS NOT NULL
          AND wr.source_competitor IS NOT NULL
          AND wr.source_competitor != ''
          AND lxc.keyword_master_ids IS NOT NULL
          AND lxc.keyword_master_ids != '{}'
        GROUP BY wc2.id
    ) sub
    WHERE wc.id = sub.wmt_clean_id
      AND wc.keyword_master_ids IS DISTINCT FROM sub.km_ids
""")

_SQL_BACKFILL_RAW_FALLBACK = text("""
    UPDATE waimaotong_clean_companies wc
    SET keyword_master_ids = sub.km_ids
    FROM (
        SELECT
            wc2.id AS wmt_clean_id,
            array_agg(DISTINCT lxr.keyword_master_id) AS km_ids
        FROM waimaotong_clean_companies wc2
        JOIN waimaotong_raw_companies wr
            ON wr.sys_company_id = wc2.sys_company_id
        JOIN lixiaoyun_api_companies lxr
            ON lower(trim(lxr.entname_eng)) = lower(trim(wr.source_competitor))
        WHERE wc2.keyword_master_ids = '{}'
          AND wc2.sys_company_id IS NOT NULL
          AND wr.source_competitor IS NOT NULL
          AND wr.source_competitor != ''
          AND lxr.keyword_master_id IS NOT NULL
        GROUP BY wc2.id
    ) sub
    WHERE wc.id = sub.wmt_clean_id
      AND wc.keyword_master_ids IS DISTINCT FROM sub.km_ids
""")

_SQL_FAN_OUT_ACTIVE_KEYWORDS = text("""
    INSERT INTO tenant_companies
      (tenant_id, clean_company_id, business_status, data_status)
    SELECT DISTINCT
      tk.tenant_id,
      wc.id,
      'new',
      CASE
        WHEN COALESCE(wc.contacts_count, 0) = 0 THEN 'missing_contacts'
        WHEN (
          wc.domain IS NULL
          AND wc.industry IS NULL
          AND wc.product_tags IS NULL
        ) THEN 'insufficient_data'
        ELSE 'ready'
      END
    FROM tenant_keyword tk
    JOIN waimaotong_clean_companies wc
      ON wc.keyword_master_ids @> ARRAY[tk.keyword_master_id]::uuid[]
    WHERE tk.status = 'active'
    ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
    SET data_status = EXCLUDED.data_status,
        updated_at = CASE
            WHEN tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
            THEN now()
            ELSE tenant_companies.updated_at
        END
    WHERE tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
    RETURNING id
""")

_SQL_FAN_OUT_INDUSTRY = text(f"""
    INSERT INTO tenant_companies
      (tenant_id, clean_company_id, business_status, data_status)
    SELECT DISTINCT
      t.id,
      wc.id,
      'new',
      CASE
        WHEN COALESCE(wc.contacts_count, 0) = 0 THEN 'missing_contacts'
        WHEN (
          wc.domain IS NULL
          AND wc.industry IS NULL
          AND wc.product_tags IS NULL
        ) THEN 'insufficient_data'
        ELSE 'ready'
      END
    FROM tenants t
    JOIN waimaotong_clean_companies wc
      ON wc.data_source_tags @> {KEYWORD_TAG_JSONB}
    WHERE t.status = 'active'
      AND lower(trim(t.industry)) = ANY(:industry_aliases)
    ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
    SET data_status = EXCLUDED.data_status,
        updated_at = now()
    WHERE tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
    RETURNING id
""")

_SQL_DELETE_STALE_RELATIONS = text("""
    DELETE FROM tenant_companies tc
    WHERE NOT EXISTS (
        SELECT 1
        FROM waimaotong_clean_companies wc
        WHERE wc.id = tc.clean_company_id
    )
    RETURNING id
""")

_SQL_UNRESOLVED_COUNT = text("""
    SELECT count(*)
    FROM waimaotong_clean_companies
    WHERE keyword_master_ids = '{}'
""")

_SQL_ACTIVE_JOIN_COUNT = text("""
    SELECT count(*)
    FROM tenant_companies tc
    JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
""")


async def run_wmt_lineage_repair_once(engine: AsyncEngine) -> dict:
    """执行单轮 WMT lineage repair。

    返回统计信息；如果其他实例已经持有 advisory lock，则跳过本轮。
    """
    async with engine.begin() as conn:
        return await run_wmt_lineage_repair_on_connection(conn)


async def run_wmt_lineage_repair_on_connection(conn) -> dict:
    """在已有事务/连接内执行 repair，主要供测试和脚本复用。"""
    locked = await conn.scalar(
        text("SELECT pg_try_advisory_xact_lock(:key)"),
        {"key": _ADVISORY_LOCK_KEY},
    )
    if not locked:
        logger.info("wmt_lineage_repair: another instance holds the lock, skipping")
        return {"skipped": True, "reason": "lock_busy"}

    normalized = await conn.execute(_SQL_NORMALIZE_KEYWORD_MASTER_IDS)
    clean_path = await conn.execute(_SQL_BACKFILL_CLEAN_PATH)
    raw_fallback = await conn.execute(_SQL_BACKFILL_RAW_FALLBACK)
    fan_out = await conn.execute(_SQL_FAN_OUT_ACTIVE_KEYWORDS)
    industry_fan_out = await conn.execute(
        _SQL_FAN_OUT_INDUSTRY,
        {"industry_aliases": _PCB_INDUSTRY_ALIASES},
    )
    deleted_stale = await conn.execute(_SQL_DELETE_STALE_RELATIONS)
    unresolved = int(await conn.scalar(_SQL_UNRESOLVED_COUNT) or 0)
    active_join = int(await conn.scalar(_SQL_ACTIVE_JOIN_COUNT) or 0)

    stats = {
        "skipped": False,
        "normalized_keyword_master_ids": normalized.rowcount,
        "clean_path": clean_path.rowcount,
        "raw_fallback": raw_fallback.rowcount,
        "fan_out": len(fan_out.mappings().all()),
        "industry_fan_out": len(industry_fan_out.mappings().all()),
        "deleted_stale": len(deleted_stale.mappings().all()),
        "unresolved": unresolved,
        "active_join": active_join,
    }
    logger.info("wmt_lineage_repair: %s", stats)
    return stats


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
