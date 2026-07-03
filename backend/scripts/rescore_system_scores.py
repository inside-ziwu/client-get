#!/usr/bin/env python3
"""全量重算 waimaotong_clean_companies 的系统评分(system_score / system_grade)。

背景:has_china_pcb_supplier 条件接入采集类型口径后
(openspec change score-pcb-supplier-by-collection-type),
存量分数仍是旧口径(该维度一律 default 10 分),需要全量重算对齐。

用法:
  默认 dry-run,只统计等级迁移分布,不写库:
    python -m scripts.rescore_system_scores
  真正执行(分批 UPDATE,每批一个事务,可安全重跑):
    RESCORE_CONFIRM=yes python -m scripts.rescore_system_scores --execute

数据库连接:DATABASE_URL 或 CLIENTGET_DEV_DATABASE_URL(与 init_instance 一致)。
模板口径:当前实例(CLIENTGET_INSTANCE_ID,默认 default)的激活平台模板,
与 score_clean_company / wmt_lineage_repair 补评完全一致。
"""

import argparse
import os
import sys
from collections import Counter

from sqlalchemy import create_engine, text

from app.services.scoring_engine_service import evaluate_company

BATCH_SIZE = 1000

COMPANY_FIELDS_SQL = """
    SELECT id, employee_size, trade_amount_3y_usd, trade_count,
           contacts_count, data_source_tags, source_tags,
           company_type_analysis, industry,
           system_grade AS old_grade, system_score AS old_score
    FROM waimaotong_clean_companies
    ORDER BY id
"""


def _build_sync_database_url() -> str:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raw = os.environ.get("CLIENTGET_DEV_DATABASE_URL", "").strip()
    if not raw:
        print("错误:DATABASE_URL 或 CLIENTGET_DEV_DATABASE_URL 未设置", file=sys.stderr)
        sys.exit(1)
    clean = raw.split("://", 1)[-1]
    return f"postgresql+psycopg://{clean}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="真正写库(默认 dry-run)")
    args = parser.parse_args()

    if args.execute and os.environ.get("RESCORE_CONFIRM") != "yes":
        print("错误:--execute 需要同时设置环境变量 RESCORE_CONFIRM=yes(二重确认)", file=sys.stderr)
        sys.exit(1)

    instance_id = os.environ.get("CLIENTGET_INSTANCE_ID", "default")
    engine = create_engine(_build_sync_database_url(), future=True)

    with engine.connect() as conn:
        tmpl = conn.execute(
            text(
                """
                SELECT name, version, dimensions, grade_thresholds
                FROM platform_scoring_templates
                WHERE is_active = true AND instance_id = :instance_id
                ORDER BY updated_at DESC LIMIT 1
                """
            ),
            {"instance_id": instance_id},
        ).mappings().first()
        if tmpl is None:
            print(f"错误:实例 {instance_id} 无激活平台评分模板", file=sys.stderr)
            sys.exit(1)
        print(f"模板:{tmpl['name']} v{tmpl['version']}(instance={instance_id})")

        rows = conn.execute(text(COMPANY_FIELDS_SQL)).mappings().all()
        print(f"待重算公司数:{len(rows)}")

    updates: list[tuple[int, int, str]] = []  # (id, score, grade)
    transitions: Counter = Counter()
    changed = 0
    for row in rows:
        data = dict(row)
        result = evaluate_company(tmpl["dimensions"], tmpl["grade_thresholds"], data)
        new_score, new_grade = result["total_score"], result["grade"]
        if new_score != data["old_score"] or new_grade != data["old_grade"]:
            changed += 1
        transitions[f"{data['old_grade'] or 'NULL'} → {new_grade}"] += 1
        updates.append((int(data["id"]), int(new_score), new_grade))

    print(f"分数或等级变化:{changed} / {len(updates)}")
    print("等级迁移分布(旧 → 新):")
    for k, v in sorted(transitions.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    if not args.execute:
        print("\n[dry-run] 未写库。确认无误后用 RESCORE_CONFIRM=yes ... --execute 执行。")
        return

    written = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        values_sql = ",".join(f"({cid},{score},'{grade}')" for cid, score, grade in batch)
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    UPDATE waimaotong_clean_companies AS c
                    SET system_score = v.score, system_grade = v.grade
                    FROM (VALUES {values_sql}) AS v(id, score, grade)
                    WHERE c.id = v.id
                    """
                )
            )
        written += len(batch)
        if written % 20000 < BATCH_SIZE:
            print(f"  已写入 {written} / {len(updates)}")

    print(f"完成:共写入 {written} 家公司的系统评分。")
    engine.dispose()


if __name__ == "__main__":
    main()
