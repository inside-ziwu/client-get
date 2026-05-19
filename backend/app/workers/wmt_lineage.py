"""wmt 血缘回写：为 waimaotong_clean_companies 回写 keyword_master_ids。

可被以下场景调用:
  - repair_wmt_lineage.py（一次性补全）
  - 未来采集管道对接（D8 钩子入口）
"""

import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)

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
          AND lxc.keyword_master_ids != '{}'
          AND wc2.id = ANY(:target_ids)
        GROUP BY wc2.id
    ) sub
    WHERE wc.id = sub.wmt_clean_id
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
          AND wc2.id = ANY(:target_ids)
        GROUP BY wc2.id
    ) sub
    WHERE wc.id = sub.wmt_clean_id
""")


async def backfill_keyword_master_ids(conn, *, wmt_clean_ids: list[int] | None = None) -> dict:
    """为指定的 wmt_clean 公司回写 keyword_master_ids。

    若 wmt_clean_ids 为 None，则对所有 keyword_master_ids='{}' 的记录回写。
    """
    if wmt_clean_ids is None:
        ids_result = await conn.execute(
            text("SELECT ARRAY_AGG(id) FROM waimaotong_clean_companies WHERE keyword_master_ids = '{}'")
        )
        wmt_clean_ids = ids_result.scalar_one() or []

    if not wmt_clean_ids:
        return {"clean_path": 0, "raw_fallback": 0}

    r1 = await conn.execute(_SQL_BACKFILL_CLEAN_PATH, {"target_ids": wmt_clean_ids})
    clean_count = r1.rowcount

    r2 = await conn.execute(_SQL_BACKFILL_RAW_FALLBACK, {"target_ids": wmt_clean_ids})
    fallback_count = r2.rowcount

    logger.info("backfill_keyword_master_ids: clean_path=%d, raw_fallback=%d", clean_count, fallback_count)
    return {"clean_path": clean_count, "raw_fallback": fallback_count}
