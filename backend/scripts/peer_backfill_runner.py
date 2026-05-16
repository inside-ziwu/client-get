"""同行公司 backfill runner。

用法:
  # dry run（只统计，不写数据）
  python scripts/peer_backfill_runner.py --dry-run

  # 正式 backfill（每 500 条一个事务）
  python scripts/peer_backfill_runner.py

环境变量:
  SYNC_DATABASE_URL — 同步数据库连接字符串（psycopg 驱动）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 让 app 模块可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="同行公司 backfill runner")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写数据")
    parser.add_argument("--batch-size", type=int, default=500, help="每批处理条数")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)

    if args.dry_run:
        _run_dry(engine, batch_size=args.batch_size)
    else:
        _run_backfill(engine, batch_size=args.batch_size)


def _run_dry(engine, *, batch_size: int) -> None:
    """dry run: 用同步连接遍历所有 raw，统计去重率（不写任何数据）。"""
    from app.services.peer_company_cleaning_service import PeerCompanyCleaningService

    svc = PeerCompanyCleaningService()
    last_id = 0
    raw_total = 0
    skipped = 0
    identity_keys: set[tuple[str, str]] = set()
    english_keys: set[tuple[str, str]] = set()
    website_count = 0
    source_id_count = 0

    print("[dry-run] 开始扫描 lixiaoyun_raw_companies ...")
    t0 = time.time()

    with engine.connect() as conn:
        while True:
            rows = conn.execute(
                text(
                    """
                    SELECT id, source_id, name, english_name, domain,
                           esdate, legalperson, uncid, reg_capital,
                           employee_scale, reg_address,
                           keyword_master_id::text AS keyword_master_id,
                           raw_payload
                    FROM lixiaoyun_raw_companies
                    WHERE id > :last_id
                    ORDER BY id
                    LIMIT :limit
                    """
                ),
                {"last_id": last_id, "limit": batch_size},
            ).mappings().all()

            if not rows:
                break

            for r in rows:
                row = dict(r)
                last_id = int(row["id"])
                raw_total += 1

                identity = svc.derive_identity(row)
                if identity is None:
                    skipped += 1
                    continue

                if identity.identity_type == "website_host":
                    website_count += 1
                else:
                    source_id_count += 1

                key = (identity.identity_type, identity.identity_value)
                identity_keys.add(key)
                if row.get("english_name"):
                    english_keys.add(key)

            if raw_total % 2000 == 0:
                print(f"  ... 已扫描 {raw_total} 条")

    elapsed = time.time() - t0
    peer_count = len(identity_keys)
    dedup_rate = 1 - (peer_count / raw_total) if raw_total else 0
    en_coverage = len(english_keys) / peer_count if peer_count else 0

    print()
    print("=" * 50)
    print("  DRY RUN 结果")
    print("=" * 50)
    print(f"  Raw 总数:           {raw_total}")
    print(f"  可清洗:             {raw_total - skipped}")
    print(f"  跳过（无 identity）: {skipped}")
    print(f"  预估 Peer 数:       {peer_count}")
    print(f"  去重率:             {dedup_rate:.1%}")
    print(f"  website_host 命中:  {website_count}")
    print(f"  source_id 回退:     {source_id_count}")
    print(f"  有英文名的 Peer:    {len(english_keys)} ({en_coverage:.1%})")
    print(f"  耗时:               {elapsed:.1f}s")
    print("=" * 50)


def _run_backfill(engine, *, batch_size: int) -> None:
    """正式 backfill: 同步单进程，每 batch_size 条一个事务。"""
    from app.services.peer_company_cleaning_service import PeerCompanyCleaningService

    svc = PeerCompanyCleaningService()
    last_id = 0
    batch_num = 0
    total_raw = 0
    total_cleaned = 0
    total_skipped = 0

    print(f"[backfill] 开始，batch_size={batch_size}")
    t0 = time.time()

    while True:
        batch_num += 1
        batch_cleaned = 0
        batch_skipped = 0

        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, source_id, name, english_name, domain,
                           esdate, legalperson, uncid, reg_capital,
                           employee_scale, reg_address,
                           keyword_master_id::text AS keyword_master_id,
                           raw_payload
                    FROM lixiaoyun_raw_companies
                    WHERE id > :last_id
                    ORDER BY id
                    LIMIT :limit
                    """
                ),
                {"last_id": last_id, "limit": batch_size},
            ).mappings().all()

            if not rows:
                break

            for r in rows:
                row = dict(r)
                raw_id = int(row["id"])
                last_id = raw_id
                total_raw += 1

                identity = svc.derive_identity(row)
                if identity is None:
                    batch_skipped += 1
                    total_skipped += 1
                    continue

                # 同步版清洗：直接用同步连接执行各步骤
                _sync_clean_raw(conn, svc, raw_company_id=raw_id, row=row, identity=identity)
                batch_cleaned += 1
                total_cleaned += 1

        elapsed = time.time() - t0
        print(
            f"  批次 {batch_num}: last_id={last_id}, "
            f"cleaned={batch_cleaned}, skipped={batch_skipped}, "
            f"累计={total_raw}, 耗时={elapsed:.1f}s"
        )

    elapsed = time.time() - t0
    print()
    print("=" * 50)
    print("  BACKFILL 完成")
    print("=" * 50)
    print(f"  总 Raw:    {total_raw}")
    print(f"  已清洗:    {total_cleaned}")
    print(f"  跳过:      {total_skipped}")
    print(f"  总批次:    {batch_num - 1}")
    print(f"  最后 ID:   {last_id}")
    print(f"  耗时:      {elapsed:.1f}s")
    print("=" * 50)

    # 最终统计
    with engine.connect() as conn:
        for tbl in ["peer_companies", "peer_company_contacts", "peer_company_keywords", "peer_company_sources"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar_one()
            print(f"  {tbl}: {count}")


def _sync_clean_raw(conn, svc, *, raw_company_id: int, row: dict, identity) -> None:
    """同步版 clean_raw_company — 用同步 conn 执行所有 SQL。"""
    from app.services.peer_company_cleaning_service import (
        normalize_website_host, _build_display_set_clause,
    )

    existing_peer_id = None

    # 查 raw_company_id 是否已有映射
    existing = conn.execute(
        text("SELECT peer_company_id::text FROM peer_company_sources WHERE raw_company_id = :rid"),
        {"rid": raw_company_id},
    ).mappings().first()
    if existing:
        existing_peer_id = existing["peer_company_id"]

    # D2: source_id 双向复用
    if existing_peer_id is None:
        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            sp = conn.execute(
                text("SELECT peer_company_id::text FROM peer_company_sources WHERE source_id = :sid LIMIT 1"),
                {"sid": source_id},
            ).mappings().first()
            if sp:
                existing_peer_id = sp["peer_company_id"]

    display_set = _build_display_set_clause("peer_companies")
    website_host = normalize_website_host(row.get("domain") or row.get("website"))
    params = {**svc._display_params(row), "website_host": website_host}

    if existing_peer_id:
        peer_id = existing_peer_id
        conn.execute(
            text(f"UPDATE peer_companies SET {display_set}, last_seen_at = now() WHERE id = :peer_id"),
            {**params, "peer_id": peer_id},
        )
    else:
        from app.services.peer_company_cleaning_service import IDENTITY_RULE_VERSION
        result = conn.execute(
            text(
                f"""
                INSERT INTO peer_companies
                  (identity_type, identity_value, identity_source, identity_confidence,
                   identity_rule_version, merge_reason, name, english_name, domain,
                   website_host, source_id, esdate, legalperson, uncid, reg_capital,
                   employee_scale, reg_address, first_seen_at, last_seen_at)
                VALUES
                  (:identity_type, :identity_value, :identity_source, :identity_confidence,
                   :identity_rule_version, :merge_reason, :name, :english_name, :domain,
                   :website_host, :source_id, :esdate, :legalperson, :uncid, :reg_capital,
                   :employee_scale, :reg_address, now(), now())
                ON CONFLICT (identity_type, identity_value) DO UPDATE
                SET {display_set},
                    conflict_count = peer_companies.conflict_count + CASE
                        WHEN peer_companies.uncid IS NOT NULL AND EXCLUDED.uncid IS NOT NULL
                         AND peer_companies.uncid <> EXCLUDED.uncid THEN 1
                        WHEN peer_companies.legalperson IS NOT NULL AND EXCLUDED.legalperson IS NOT NULL
                         AND peer_companies.legalperson <> EXCLUDED.legalperson THEN 1
                        WHEN peer_companies.name IS NOT NULL AND EXCLUDED.name IS NOT NULL
                         AND peer_companies.name <> EXCLUDED.name THEN 1
                        ELSE 0 END,
                    last_seen_at = now()
                RETURNING id::text AS id
                """
            ),
            {
                **params,
                "identity_type": identity.identity_type,
                "identity_value": identity.identity_value,
                "identity_source": identity.identity_source,
                "identity_confidence": identity.identity_confidence,
                "identity_rule_version": IDENTITY_RULE_VERSION,
                "merge_reason": (
                    "website host normalized"
                    if identity.identity_type == "website_host"
                    else "fallback to Lixiaoyun source_id"
                ),
            },
        )
        peer_id = str(result.mappings().one()["id"])

    # keywords
    km_id = row.get("keyword_master_id")
    if km_id:
        conn.execute(
            text(
                "INSERT INTO peer_company_keywords (peer_company_id, keyword_master_id) "
                "VALUES (CAST(:pid AS uuid), CAST(:kid AS uuid)) ON CONFLICT DO NOTHING"
            ),
            {"pid": peer_id, "kid": str(km_id)},
        )

    # source mapping
    conn.execute(
        text(
            "INSERT INTO peer_company_sources (peer_company_id, raw_company_id, source_id) "
            "VALUES (CAST(:pid AS uuid), :rid, :sid) ON CONFLICT (raw_company_id) DO NOTHING"
        ),
        {"pid": peer_id, "rid": raw_company_id, "sid": row.get("source_id")},
    )

    # contacts
    contacts = svc._extract_contacts(row)
    for c in contacts:
        name = (c.get("name") or "").strip() or None
        email_raw = (c.get("email") or "").strip()
        email = email_raw.lower() if email_raw else None
        position = (c.get("position") or c.get("title") or "").strip() or None
        phone = (c.get("phone") or "").strip() or None
        mobile = (c.get("mobile") or "").strip() or None
        sc_id = (c.get("source_contact_id") or c.get("id") or "").strip() or None

        if not name and not email:
            continue

        cp = {
            "peer_company_id": peer_id, "email": email, "name": name,
            "position": position, "phone": phone, "mobile": mobile,
            "source_contact_id": str(sc_id) if sc_id else None,
            "raw_company_id": raw_company_id,
        }

        # 两步 upsert
        if sc_id:
            ex = conn.execute(
                text(
                    "SELECT id, email FROM peer_company_contacts "
                    "WHERE peer_company_id = CAST(:peer_company_id AS uuid) AND source_contact_id = :source_contact_id"
                ),
                {"peer_company_id": peer_id, "source_contact_id": str(sc_id)},
            ).mappings().first()
            if ex and email and not (ex["email"] or "").strip():
                conn.execute(
                    text(
                        "UPDATE peer_company_contacts SET email = :email, "
                        "name = COALESCE(NULLIF(:name, ''), peer_company_contacts.name), "
                        "position = COALESCE(NULLIF(:position, ''), peer_company_contacts.position), "
                        "phone = COALESCE(NULLIF(:phone, ''), peer_company_contacts.phone), "
                        "mobile = COALESCE(NULLIF(:mobile, ''), peer_company_contacts.mobile), "
                        "raw_company_id = :raw_company_id, updated_at = now() WHERE id = :existing_id"
                    ),
                    {**cp, "existing_id": ex["id"]},
                )
                continue

        conn.execute(
            text(
                "INSERT INTO peer_company_contacts "
                "(peer_company_id, email, name, position, phone, mobile, source_contact_id, raw_company_id) "
                "VALUES (CAST(:peer_company_id AS uuid), :email, :name, :position, :phone, :mobile, :source_contact_id, :raw_company_id) "
                "ON CONFLICT DO UPDATE SET "
                "name = COALESCE(NULLIF(EXCLUDED.name, ''), peer_company_contacts.name), "
                "position = COALESCE(NULLIF(EXCLUDED.position, ''), peer_company_contacts.position), "
                "phone = COALESCE(NULLIF(EXCLUDED.phone, ''), peer_company_contacts.phone), "
                "mobile = COALESCE(NULLIF(EXCLUDED.mobile, ''), peer_company_contacts.mobile), "
                "raw_company_id = EXCLUDED.raw_company_id, updated_at = now()"
            ),
            cp,
        )

    # refresh contact_count
    conn.execute(
        text(
            "UPDATE peer_companies SET contact_count = "
            "(SELECT COUNT(*) FROM peer_company_contacts WHERE peer_company_id = CAST(:pid AS uuid)) "
            "WHERE id = CAST(:pid AS uuid)"
        ),
        {"pid": peer_id},
    )


if __name__ == "__main__":
    main()
