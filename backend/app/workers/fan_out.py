"""FanOutWorker — 关键词 fan-out：将 wmt 血缘匹配的公司推送到租户视图中。

当租户新增关键词订阅时，fan-out 负责将 keyword_master_ids 包含该关键词的
waimaotong_clean_companies 写入 tenant_companies，实现"反推"效果。

幂等保证：
    tenant_companies 表有 UNIQUE(tenant_id, clean_company_id) 约束，
    所有插入均使用 ON CONFLICT ... DO UPDATE，可安全重复执行。

使用方式：
    worker = FanOutWorker()
    result = await worker.run_for_tenant_keyword(engine, tenant_id=..., keyword_master_id=...)
"""

import logging

from app.services.scoring_engine_service import ScoringEngineService

_scoring_engine = ScoringEngineService()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class FanOutWorker:
    """无状态 fan-out worker，为指定 (tenant_id, keyword_master_id) 执行反推写入。"""

    async def run_for_tenant_keyword(
        self,
        engine: AsyncEngine,
        *,
        tenant_id: str,
        keyword_master_id: str,
    ) -> dict:
        async with engine.begin() as conn:
            return await run_fan_out_for_tenant_keyword(conn, tenant_id, keyword_master_id)


async def run_fan_out_for_tenant_keyword(
    conn,
    tenant_id: str,
    keyword_master_id: str,
) -> dict:
    """核心 fan-out：将 wmt 血缘匹配的公司写入 tenant_companies。"""
    km_row = (
        await conn.execute(
            text("SELECT keyword FROM keyword_master WHERE id = :kmid LIMIT 1"),
            {"kmid": keyword_master_id},
        )
    ).mappings().first()
    if km_row is None:
        logger.warning("fan_out: keyword_master_id=%s 不存在，跳过", keyword_master_id)
        return {"inserted": 0, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}

    keyword = km_row["keyword"]

    subscription = (
        await conn.execute(
            text("""
                SELECT 1 FROM tenant_keyword
                WHERE tenant_id = :tenant_id
                  AND keyword_master_id = :keyword_master_id
                  AND status = 'active'
                LIMIT 1
            """),
            {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
        )
    ).first()
    if subscription is None:
        logger.info("fan_out: keyword=%s tenant_id=%s 未订阅或已删除，跳过", keyword, tenant_id)
        return {"inserted": 0, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}

    result = await conn.execute(
        text("""
            INSERT INTO tenant_companies
              (tenant_id, clean_company_id, business_status, data_status)
            SELECT
              :tenant_id,
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
            FROM waimaotong_clean_companies wc
            WHERE wc.keyword_master_ids @> ARRAY[:keyword_master_id]::uuid[]
            ORDER BY wc.id
            ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
            SET data_status = EXCLUDED.data_status,
                updated_at = now()
            WHERE tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
            RETURNING id
        """),
        {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
    )
    new_rows = result.mappings().all()
    inserted = len(new_rows)

    for row in new_rows:
        try:
            await _scoring_engine.score_tenant_company(conn, tenant_id=tenant_id, tenant_company_id=row["id"])
        except Exception:
            logger.warning("fan_out: 评分失败 tc_id=%s", row["id"], exc_info=True)

    logger.info("fan_out: keyword=%s tenant_id=%s 写入 tenant_companies=%d 条", keyword, tenant_id, inserted)
    return {"inserted": inserted, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}
