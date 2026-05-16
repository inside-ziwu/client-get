"""FanOutWorker — 关键词 fan-out：将已有 clean_companies 推送到新订阅租户的视图中。

UC-11 场景：
    当租户新增关键词订阅时，该关键词可能已被其他租户采集过。
    fan-out worker 负责将 keyword_master 关联的现有 clean_companies
    复制（INSERT）到新租户的 tenant_companies 表，实现"反推"效果。

幂等保证：
    tenant_companies 表有 UNIQUE(tenant_id, clean_company_id) 约束，
    所有插入均使用 ON CONFLICT DO NOTHING，可安全重复执行。

使用方式：
    # 单次触发（通常由 API 在租户绑定关键词后异步调用）
    worker = FanOutWorker()
    result = await worker.run_for_tenant_keyword(engine, tenant_id=..., keyword_master_id=...)
"""

import logging

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
        """为某租户的某个关键词执行一次 fan-out 写入。

        流程：
        1. 通过 clean_company_keywords 找到该平台关键词已命中的 clean_companies
        2. 确认目标租户仍订阅该 tenant_keyword
        3. INSERT INTO tenant_companies ON CONFLICT DO NOTHING

        Args:
            engine: AsyncEngine 实例
            tenant_id: 目标租户 UUID（str）
            keyword_master_id: keyword_master UUID（str）

        Returns:
            {"inserted": N, "skipped": M, "tenant_id": ..., "keyword_master_id": ...}
        """
        async with engine.begin() as conn:
            return await run_fan_out_for_tenant_keyword(conn, tenant_id, keyword_master_id)


async def run_fan_out_for_tenant_keyword(
    conn,
    tenant_id: str,
    keyword_master_id: str,
) -> dict:
    """核心 fan-out 逻辑（接受 AsyncConnection，方便单元测试直接调用）。

    Args:
        conn: AsyncConnection
        tenant_id: 目标租户 UUID（str）
        keyword_master_id: 已归一化关键词在 keyword_master 中的 UUID

    Returns:
        {"inserted": N, "tenant_id": ..., "keyword_master_id": ...}
    """
    # 步骤 1：查出该 keyword_master 对应的展示信息
    kn_result = await conn.execute(
        text(
            """
            SELECT keyword_normalized, keyword
            FROM keyword_master
            WHERE id = :kmid
            LIMIT 1
            """
        ),
        {"kmid": keyword_master_id},
    )
    km_row = kn_result.mappings().first()
    if km_row is None:
        logger.warning("fan_out: keyword_master_id=%s 不存在，跳过", keyword_master_id)
        return {"inserted": 0, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}

    keyword = km_row["keyword"]

    subscription = await conn.execute(
        text(
            """
            SELECT 1
            FROM tenant_keyword
            WHERE tenant_id = :tenant_id
              AND keyword_master_id = :keyword_master_id
              AND status = 'active'
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
    )
    if subscription.first() is None:
        logger.info(
            "fan_out: keyword=%s tenant_id=%s 未订阅或已删除，跳过",
            keyword,
            tenant_id,
        )
        return {"inserted": 0, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}

    result = await conn.execute(
        text(
            """
            INSERT INTO tenant_companies
              (tenant_id, clean_company_id, business_status, data_status, visibility_status)
            SELECT
              :tenant_id,
              cck.clean_company_id,
              'new',
              CASE
                WHEN NOT EXISTS (
                  SELECT 1
                  FROM clean_contacts contacts
                  WHERE contacts.clean_company_id = cck.clean_company_id
                ) THEN 'missing_contacts'
                WHEN (
                  cc.website IS NULL
                  AND cc.industry_desc IS NULL
                  AND cardinality(cc.product_tags) = 0
                  AND cardinality(cc.pcb_suppliers) = 0
                ) THEN 'insufficient_data'
                ELSE 'ready'
              END,
              'visible'
            FROM clean_company_keywords cck
            JOIN clean_companies cc ON cc.id = cck.clean_company_id
            WHERE cck.keyword_master_id = :keyword_master_id
            ORDER BY cck.clean_company_id
            LIMIT 5000
            ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
            SET visibility_status = 'visible',
                data_status = EXCLUDED.data_status,
                updated_at = now()
            WHERE tenant_companies.visibility_status <> 'visible'
            RETURNING id
            """
        ),
        {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
    )
    inserted = len(result.mappings().all())

    logger.info(
        "fan_out: keyword=%s tenant_id=%s 写入 tenant_companies=%d 条",
        keyword,
        tenant_id,
        inserted,
    )
    return {"inserted": inserted, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}


async def hide_tenant_companies_for_cancelled_keyword(
    conn,
    *,
    tenant_id: str,
    keyword_master_id: str,
) -> dict:
    """Hide tenant companies whose last active keyword coverage was removed."""
    affected = await conn.execute(
        text(
            """
            SELECT tc.id AS tenant_company_id, tc.clean_company_id
            FROM tenant_companies tc
            JOIN clean_company_keywords cancelled
              ON cancelled.clean_company_id = tc.clean_company_id
             AND cancelled.keyword_master_id = :keyword_master_id
            WHERE tc.tenant_id = :tenant_id
              AND tc.visibility_status = 'visible'
              AND NOT EXISTS (
                SELECT 1
                FROM clean_company_keywords cck
                JOIN tenant_keyword tk
                  ON tk.keyword_master_id = cck.keyword_master_id
                 AND tk.tenant_id = :tenant_id
                 AND tk.status = 'active'
                WHERE cck.clean_company_id = tc.clean_company_id
              )
            ORDER BY tc.id
            """
        ),
        {"tenant_id": tenant_id, "keyword_master_id": keyword_master_id},
    )
    tenant_company_ids = [row["tenant_company_id"] for row in affected.mappings().all()]
    if not tenant_company_ids:
        return {"hidden": 0, "tenant_id": tenant_id, "keyword_master_id": keyword_master_id}

    await conn.execute(
        text(
            """
            DELETE FROM group_members
            WHERE tenant_id = :tenant_id
              AND tenant_company_id = ANY(:tenant_company_ids)
            """
        ),
        {"tenant_id": tenant_id, "tenant_company_ids": tenant_company_ids},
    )
    await conn.execute(
        text(
            """
            DELETE FROM scoring_jobs
            WHERE tenant_id = :tenant_id
              AND tenant_company_id = ANY(:tenant_company_ids)
              AND status IN ('pending','leased')
            """
        ),
        {"tenant_id": tenant_id, "tenant_company_ids": tenant_company_ids},
    )
    await conn.execute(
        text(
            """
            DELETE FROM company_scores
            WHERE tenant_id = :tenant_id
              AND tenant_company_id = ANY(:tenant_company_ids)
            """
        ),
        {"tenant_id": tenant_id, "tenant_company_ids": tenant_company_ids},
    )
    await conn.execute(
        text(
            """
            UPDATE tenant_companies
            SET visibility_status = 'hidden',
                model_score = NULL,
                score = NULL,
                note = NULL,
                tags = '{}',
                business_status = 'new',
                updated_at = now()
            WHERE tenant_id = :tenant_id
              AND id = ANY(:tenant_company_ids)
            """
        ),
        {"tenant_id": tenant_id, "tenant_company_ids": tenant_company_ids},
    )
    return {
        "hidden": len(tenant_company_ids),
        "tenant_id": tenant_id,
        "keyword_master_id": keyword_master_id,
    }
