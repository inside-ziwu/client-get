"""wmt 血缘补全：为 waimaotong_clean_companies 回写 keyword_master_ids。

血缘链路:
  wmt_clean.sys_company_id → wmt_raw.sys_company_id → wmt_raw.source_competitor
  → lower(trim()) 匹配 → lx_clean.entname_eng → lx_clean.keyword_master_ids
  → 或 fallback → lx_raw.entname_eng → lx_raw.keyword_master_id

用法:
  # dry-run（只统计，不写数据）
  python scripts/repair_wmt_lineage.py --dry-run

  # 正式写入（先快照再回写）
  python scripts/repair_wmt_lineage.py --write

环境变量:
  SYNC_DATABASE_URL — 同步数据库连接字符串
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.core.config import get_settings

# clean 主路径：wmt_raw.source_competitor 精确匹配 lx_clean.entname_eng
_SQL_CLEAN_PATH = text("""
    WITH lineage AS (
        SELECT
            wc.id AS wmt_clean_id,
            wc.company_name,
            wr.id AS wmt_raw_id,
            wr.source_competitor,
            wr.source_keyword,
            lxc.id AS lx_clean_id,
            lxc.entname_eng,
            lxc.keyword_master_ids AS km_ids
        FROM waimaotong_clean_companies wc
        JOIN waimaotong_raw_companies wr
            ON wr.sys_company_id = wc.sys_company_id
        JOIN lixiaoyun_api_clean_companies lxc
            ON lower(trim(lxc.entname_eng)) = lower(trim(wr.source_competitor))
        WHERE wc.sys_company_id IS NOT NULL
          AND wr.source_competitor IS NOT NULL
          AND wr.source_competitor != ''
          AND lxc.keyword_master_ids != '{}'
    )
    SELECT
        wmt_clean_id,
        company_name,
        array_agg(DISTINCT unnested_km) AS keyword_master_ids
    FROM lineage, unnest(km_ids) AS unnested_km
    GROUP BY wmt_clean_id, company_name
""")

# raw fallback：lx_clean 未命中，匹配 lx_raw (lixiaoyun_api_companies)
_SQL_RAW_FALLBACK = text("""
    WITH already_resolved AS (
        SELECT id FROM waimaotong_clean_companies
        WHERE keyword_master_ids != '{}'
    ),
    fallback AS (
        SELECT
            wc.id AS wmt_clean_id,
            wc.company_name,
            wr.id AS wmt_raw_id,
            wr.source_competitor,
            lxr.keyword_master_id AS km_id
        FROM waimaotong_clean_companies wc
        JOIN waimaotong_raw_companies wr
            ON wr.sys_company_id = wc.sys_company_id
        JOIN lixiaoyun_api_companies lxr
            ON lower(trim(lxr.entname_eng)) = lower(trim(wr.source_competitor))
        WHERE wc.id NOT IN (SELECT id FROM already_resolved)
          AND wc.sys_company_id IS NOT NULL
          AND wr.source_competitor IS NOT NULL
          AND wr.source_competitor != ''
          AND lxr.keyword_master_id IS NOT NULL
    )
    SELECT
        wmt_clean_id,
        company_name,
        array_agg(DISTINCT km_id) AS keyword_master_ids
    FROM fallback
    GROUP BY wmt_clean_id, company_name
""")

# unresolved 诊断
_SQL_UNRESOLVED = text("""
    SELECT
        wc.id AS wmt_clean_id,
        wc.company_name,
        wr.id AS wmt_raw_id,
        wr.source_competitor,
        wr.source_keyword,
        CASE
            WHEN wr.sys_company_id IS NULL THEN 'wmt_raw 无 sys_company_id'
            WHEN wr.source_competitor IS NULL OR wr.source_competitor = '' THEN 'wmt_raw 无 source_competitor'
            ELSE 'lx_clean 和 lx_raw 均无匹配'
        END AS reason
    FROM waimaotong_clean_companies wc
    LEFT JOIN waimaotong_raw_companies wr
        ON wr.sys_company_id = wc.sys_company_id
    WHERE wc.keyword_master_ids = '{}'
    ORDER BY wc.id
""")

_SQL_SNAPSHOT = text("""
    CREATE TABLE IF NOT EXISTS _wmt_lineage_snapshot AS
    SELECT id, keyword_master_ids, now() AS snapshot_at
    FROM waimaotong_clean_companies
    WHERE keyword_master_ids != '{}'
""")

_SQL_UPDATE = text("""
    UPDATE waimaotong_clean_companies
    SET keyword_master_ids = :km_ids
    WHERE id = :wmt_clean_id
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="wmt 血缘补全：回写 keyword_master_ids")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="只统计不写数据")
    mode.add_argument("--write", action="store_true", help="先快照再写入")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)

    with engine.begin() as conn:
        # clean 主路径
        clean_rows = conn.execute(_SQL_CLEAN_PATH).mappings().all()
        print(f"[clean 主路径] 命中 {len(clean_rows)} 条 wmt_clean 公司")

        if not args.dry_run:
            for r in clean_rows:
                conn.execute(_SQL_UPDATE, {"wmt_clean_id": r["wmt_clean_id"], "km_ids": list(r["keyword_master_ids"])})
            print(f"  → 已写入 {len(clean_rows)} 条 keyword_master_ids")

        # raw fallback
        fallback_rows = conn.execute(_SQL_RAW_FALLBACK).mappings().all()
        print(f"[raw fallback] 命中 {len(fallback_rows)} 条 wmt_clean 公司")

        if not args.dry_run:
            for r in fallback_rows:
                conn.execute(_SQL_UPDATE, {"wmt_clean_id": r["wmt_clean_id"], "km_ids": list(r["keyword_master_ids"])})
            print(f"  → 已写入 {len(fallback_rows)} 条 keyword_master_ids")

        # unresolved 诊断
        unresolved = conn.execute(_SQL_UNRESOLVED).mappings().all()
        print(f"[unresolved] {len(unresolved)} 条 wmt_clean 公司无法归因")
        for u in unresolved:
            print(f"  wmt_id={u['wmt_clean_id']} name={u['company_name']} "
                  f"raw_id={u.get('wmt_raw_id')} competitor={u.get('source_competitor')} "
                  f"reason={u['reason']}")

        # 汇总
        total_wmt = conn.execute(text("SELECT count(*) FROM waimaotong_clean_companies")).scalar_one()
        resolved = len(clean_rows) + len(fallback_rows)
        print(f"\n[汇总] wmt_clean 总数: {total_wmt}, "
              f"clean 主路径: {len(clean_rows)}, "
              f"raw fallback: {len(fallback_rows)}, "
              f"已归因: {resolved}, "
              f"unresolved: {len(unresolved)}")

        if args.dry_run:
            print("\n[dry-run] 未写入任何数据")
            conn.rollback()


if __name__ == "__main__":
    main()
