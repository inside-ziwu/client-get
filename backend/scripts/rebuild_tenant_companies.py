"""全清重建 tenant_companies：基于 wmt 血缘按租户关键词重建。

策略（D11）：
  1. 快照 tenant_companies 全表
  2. DELETE FROM tenant_companies（子表 ON DELETE CASCADE 自动级联）
  3. 按每个 active tenant_keyword 查询 waimaotong_clean_companies
  4. INSERT tenant_companies，ON CONFLICT DO NOTHING 幂等

用法:
  python scripts/rebuild_tenant_companies.py --dry-run
  python scripts/rebuild_tenant_companies.py --write

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

_SQL_TENANT_KEYWORDS = text("""
    SELECT
        tk.tenant_id,
        t.slug AS tenant_slug,
        tk.keyword_master_id,
        km.keyword
    FROM tenant_keyword tk
    JOIN tenants t ON t.id = tk.tenant_id
    JOIN keyword_master km ON km.id = tk.keyword_master_id
    WHERE tk.status = 'active'
    ORDER BY t.slug, km.keyword
""")

_SQL_COUNT_CURRENT = text("""
    SELECT
        tc.tenant_id,
        t.slug AS tenant_slug,
        count(*) AS total,
        count(*) FILTER (WHERE tc.visibility_status = 'visible') AS visible
    FROM tenant_companies tc
    JOIN tenants t ON t.id = tc.tenant_id
    GROUP BY tc.tenant_id, t.slug
    ORDER BY t.slug
""")

_SQL_INSERT_FOR_KEYWORD = text("""
    INSERT INTO tenant_companies
      (tenant_id, clean_company_id, business_status, data_status, visibility_status)
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
      END,
      'visible'
    FROM waimaotong_clean_companies wc
    WHERE wc.keyword_master_ids @> ARRAY[:keyword_master_id]::uuid[]
    ON CONFLICT (tenant_id, clean_company_id) DO NOTHING
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="全清重建 tenant_companies")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="只统计不写数据")
    mode.add_argument("--write", action="store_true", help="先快照再全清重建")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)

    with engine.begin() as conn:
        # 当前状态
        current = conn.execute(_SQL_COUNT_CURRENT).mappings().all()
        print("[当前状态] tenant_companies:")
        for r in current:
            print(f"  {r['tenant_slug']}: total={r['total']}, visible={r['visible']}")

        # active 关键词
        keywords = conn.execute(_SQL_TENANT_KEYWORDS).mappings().all()
        print(f"\n[active 关键词] {len(keywords)} 条")

        # 预估每个租户的重建数量
        tenant_kw_map: dict[str, list[str]] = {}
        for kw in keywords:
            slug = kw["tenant_slug"]
            tenant_kw_map.setdefault(slug, []).append(kw["keyword"])

        for slug, kws in tenant_kw_map.items():
            print(f"  {slug}: {len(kws)} 关键词 ({', '.join(kws[:5])}{'...' if len(kws) > 5 else ''})")

        # 预估匹配的 wmt 公司数
        for kw in keywords:
            count = conn.execute(
                text("SELECT count(*) FROM waimaotong_clean_companies WHERE keyword_master_ids @> ARRAY[:km_id]::uuid[]"),
                {"km_id": kw["keyword_master_id"]},
            ).scalar_one()
            print(f"  {kw['tenant_slug']}/{kw['keyword']}: {count} 条 wmt 公司")

        if args.dry_run:
            print("\n[dry-run] 未写入任何数据")
            return

        # 快照
        conn.execute(text("DROP TABLE IF EXISTS _tenant_companies_snapshot"))
        conn.execute(text("""
            CREATE TABLE _tenant_companies_snapshot AS
            SELECT * FROM tenant_companies
        """))
        snapshot_count = conn.execute(text("SELECT count(*) FROM _tenant_companies_snapshot")).scalar_one()
        print(f"\n[快照] 已保存 {snapshot_count} 条到 _tenant_companies_snapshot")

        # 全清
        conn.execute(text("DELETE FROM tenant_companies"))
        print("[全清] tenant_companies 已清空（子表已级联删除）")

        # 重建
        total_inserted = 0
        for kw in keywords:
            result = conn.execute(
                _SQL_INSERT_FOR_KEYWORD,
                {"tenant_id": str(kw["tenant_id"]), "keyword_master_id": kw["keyword_master_id"]},
            )
            total_inserted += result.rowcount
            print(f"  {kw['tenant_slug']}/{kw['keyword']}: 写入 {result.rowcount} 条")

        # 验证
        after = conn.execute(_SQL_COUNT_CURRENT).mappings().all()
        print(f"\n[重建完成] 共写入 {total_inserted} 条")
        for r in after:
            print(f"  {r['tenant_slug']}: total={r['total']}, visible={r['visible']}")

        wmt_total = conn.execute(text("""
            SELECT count(*) FROM waimaotong_clean_companies WHERE keyword_master_ids != '{}'
        """)).scalar_one()
        print(f"\n[校验] wmt_clean 有血缘总数: {wmt_total}")


if __name__ == "__main__":
    main()
