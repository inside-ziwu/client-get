"""
CleanupService: 消费 cleanup_queue，执行清洗管道（raw → clean_companies → tenant_companies）。

工作模式：
- 无状态服务（stateless），不持有 engine — 由 CleanupWorker 管理 engine 和 loop。
- 处理：UPSERT clean_companies → UPSERT tenant_companies → status='done'
- 失败：status='failed'/'pending'，attempts++，last_error=...
- 重置：每 5 分钟把 attempts<MAX_ATTEMPTS AND status='failed' 的行重置回 pending

D-008 规则：
- 励销云(lixiaoyun)不入 clean，直接 mark done。
"""
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100
_MAX_ATTEMPTS = 3


class CleanupService:
    """无状态 CleanupService — 所有方法接受 conn: AsyncConnection。"""

    async def process_one_batch(self, conn: AsyncConnection, batch_size: int = _BATCH_SIZE) -> int:
        return await self._process_batch(conn, batch_size=batch_size)

    async def recover_stuck(self, conn: AsyncConnection, stuck_minutes: int = 10) -> int:
        """恢复超时的 processing 条目回到 pending（用于 worker 重启恢复）。"""
        result = await conn.execute(
            text(
                """
                UPDATE cleanup_queue
                SET status = 'pending'
                WHERE status = 'processing'
                  AND enqueued_at < now() - make_interval(mins => :mins)
                RETURNING id
                """
            ),
            {"mins": stuck_minutes},
        )
        recovered = result.rowcount
        if recovered:
            logger.info("CleanupService: 恢复 %d 条超时 processing 条目", recovered)
        return recovered

    async def _process_batch(self, conn: AsyncConnection, batch_size: int = _BATCH_SIZE) -> int:
        rows = await self._claim_batch(conn, batch_size=batch_size)
        if not rows:
            return 0
        for row in rows:
            await self._process_one(conn, row)
        return len(rows)

    async def _claim_batch(self, conn: AsyncConnection, batch_size: int = _BATCH_SIZE) -> list:
        result = await conn.execute(
            text(
                """
                UPDATE cleanup_queue
                SET status = 'processing'
                WHERE id IN (
                    SELECT id FROM cleanup_queue
                    WHERE status = 'pending'
                    ORDER BY id
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, raw_table, raw_row_id, task_id, attempts
                """
            ),
            {"limit": batch_size},
        )
        return result.mappings().all()

    async def _process_one(self, conn: AsyncConnection, row) -> None:
        queue_id = row["id"]
        raw_table = row["raw_table"]
        raw_row_id = row["raw_row_id"]
        try:
            if raw_table == "lixiaoyun_raw_companies":
                pass  # 励销云不进 clean，直接标 done
            elif raw_table in ("waimaotong_raw_companies", "tendata_raw_companies"):
                await self._clean_and_link(conn, raw_table=raw_table, raw_row_id=raw_row_id)
            else:
                logger.warning("CleanupService: unknown raw_table %s, skipping", raw_table)

            await conn.execute(
                text("UPDATE cleanup_queue SET status='done', processed_at=now() WHERE id=:id"),
                {"id": queue_id},
            )
        except Exception as exc:
            logger.warning("CleanupService: failed to process queue row %s: %s", queue_id, exc)
            await conn.execute(
                text(
                    """
                    UPDATE cleanup_queue
                    SET status = CASE WHEN attempts + 1 >= :max_attempts THEN 'failed' ELSE 'pending' END,
                        attempts = attempts + 1,
                        last_error = :last_error
                    WHERE id = :id
                    """
                ),
                {"id": queue_id, "max_attempts": _MAX_ATTEMPTS, "last_error": str(exc)[:500]},
            )

    async def _clean_and_link(
        self, conn: AsyncConnection, *, raw_table: str, raw_row_id: str
    ) -> None:
        raw = await self._load_raw_row(conn, raw_table=raw_table, raw_row_id=raw_row_id)
        if raw is None:
            logger.warning("CleanupService: raw row %s/%s not found", raw_table, raw_row_id)
            return

        name = raw.get("name") or ""
        country_iso3 = raw.get("country_iso3") or ""
        domain = raw.get("website") or raw.get("domain") or None
        keyword_master_id = raw.get("keyword_master_id")

        if not name or not country_iso3:
            await self._mark_raw_cleanup_issue(
                conn,
                raw_table=raw_table,
                raw_row_id=raw_row_id,
                reason="missing_identity",
                detail={"missing_name": not bool(name), "missing_country_iso3": not bool(country_iso3)},
            )
            logger.warning(
                "CleanupService: missing name or country_iso3 for %s/%s, skipping clean",
                raw_table, raw_row_id,
            )
            return

        clean_id = await self._upsert_clean_company(
            conn,
            name=name,
            country_iso3=country_iso3,
            domain=domain,
            source_table=raw_table,
            raw=raw,
        )

        await self._upsert_clean_company_source(
            conn,
            clean_id=clean_id,
            raw_table=raw_table,
            raw=raw,
        )
        await self._materialize_clean_contacts_for_raw_source(
            conn,
            raw_table=raw_table,
            raw_row_id=raw["id"],
            raw=raw,
        )
        if keyword_master_id:
            await self._upsert_clean_company_keyword(
                conn,
                clean_id=clean_id,
                keyword_master_id=str(keyword_master_id),
            )
            await self._materialize_tenant_companies_for_keyword(
                conn,
                clean_id=clean_id,
                keyword_master_id=str(keyword_master_id),
            )
        elif raw_table == "tendata_raw_companies":
            await self._mark_raw_cleanup_issue(
                conn,
                raw_table=raw_table,
                raw_row_id=raw_row_id,
                reason="missing_keyword_master_id",
                detail={"clean_company_id": int(clean_id)},
            )

    async def _load_raw_row(
        self, conn: AsyncConnection, *, raw_table: str, raw_row_id: str
    ) -> dict | None:
        raw_row_pk = int(raw_row_id)
        if raw_table == "waimaotong_raw_companies":
            result = await conn.execute(
                text(
                    """
                    SELECT id, keyword_master_id, source_id, collection_type, name, country_iso3,
                           domain, industry AS industry_desc, products AS product_tags,
                           trade_amount_3y_usd, trade_count, contacts_count, raw_payload
                    FROM waimaotong_raw_companies WHERE id = :id
                    """
                ),
                {"id": raw_row_pk},
            )
        elif raw_table == "tendata_raw_companies":
            result = await conn.execute(
                text(
                    """
                    SELECT id, keyword_master_id, source_id, collection_type, name, country_iso3,
                           website, industry_desc, employee_num, trade_amount_3y_usd,
                           trade_count, contacts_count, pcb_suppliers, product_tags, aliases,
                           raw_payload, created_at
                    FROM tendata_raw_companies WHERE id = :id
                    """
                ),
                {"id": raw_row_pk},
            )
        else:
            return None

        row = result.mappings().first()
        if row is None:
            return None
        d = dict(row)
        if isinstance(d.get("raw_payload"), str):
            try:
                d["raw_payload"] = json.loads(d["raw_payload"])
            except Exception:
                d["raw_payload"] = {}
        return d

    async def _upsert_clean_company(
        self,
        conn: AsyncConnection,
        *,
        name: str,
        country_iso3: str,
        domain: str | None,
        source_table: str,
        raw: dict,
    ) -> str:
        import re as _re
        # Strip protocol from domain for storage
        domain_clean = None
        if domain:
            domain_clean = _re.sub(r"^https?://", "", domain).rstrip("/") or None

        # 从 raw 提取评分字段（腾道/外贸通结构化字段优先）
        employee_num = raw.get("employee_num")
        trade_amount_3y_usd = raw.get("trade_amount_3y_usd")
        trade_count_val = raw.get("trade_count")
        contacts_count = raw.get("contacts_count")
        pcb_suppliers = raw.get("pcb_suppliers") or []
        product_tags = raw.get("product_tags") or []
        aliases = raw.get("aliases") or []
        source_created_at = raw.get("created_at")

        result = await conn.execute(
            text(
                """
                INSERT INTO clean_companies
                  (name_normalized, name, country_iso3, website, industry_desc, product_tags,
                   employee_num, trade_amount_3y_usd, trade_count, contacts_count, pcb_suppliers,
                   aliases, latest_tendata_summary_at, updated_at)
                VALUES
                  (normalize_company_name(:name), :name, :country_iso3,
                   :domain, :industry_desc, :product_tags,
                   :employee_num, :trade_amount_3y_usd, :trade_count,
                   COALESCE(:contacts_count, 0), :pcb_suppliers,
                   :aliases, :source_created_at, now())
                ON CONFLICT (name_normalized, country_iso3) DO UPDATE
                SET
                  name                  = COALESCE(EXCLUDED.name,     clean_companies.name),
                  website               = COALESCE(EXCLUDED.website,  clean_companies.website),
                  industry_desc         = CASE
                    WHEN EXCLUDED.latest_tendata_summary_at >= COALESCE(clean_companies.latest_tendata_summary_at, '-infinity'::timestamptz)
                    THEN COALESCE(EXCLUDED.industry_desc, clean_companies.industry_desc)
                    ELSE clean_companies.industry_desc
                  END,
                  product_tags          = ARRAY(
                    SELECT DISTINCT unnest(clean_companies.product_tags || EXCLUDED.product_tags)
                  ),
                  employee_num          = CASE
                    WHEN EXCLUDED.latest_tendata_summary_at >= COALESCE(clean_companies.latest_tendata_summary_at, '-infinity'::timestamptz)
                    THEN COALESCE(EXCLUDED.employee_num, clean_companies.employee_num)
                    ELSE clean_companies.employee_num
                  END,
                  trade_amount_3y_usd   = CASE
                    WHEN EXCLUDED.latest_tendata_summary_at >= COALESCE(clean_companies.latest_tendata_summary_at, '-infinity'::timestamptz)
                    THEN COALESCE(EXCLUDED.trade_amount_3y_usd, clean_companies.trade_amount_3y_usd)
                    ELSE clean_companies.trade_amount_3y_usd
                  END,
                  trade_count           = CASE
                    WHEN EXCLUDED.latest_tendata_summary_at >= COALESCE(clean_companies.latest_tendata_summary_at, '-infinity'::timestamptz)
                    THEN COALESCE(EXCLUDED.trade_count, clean_companies.trade_count)
                    ELSE clean_companies.trade_count
                  END,
                  contacts_count        = CASE
                    WHEN EXCLUDED.latest_tendata_summary_at >= COALESCE(clean_companies.latest_tendata_summary_at, '-infinity'::timestamptz)
                    THEN COALESCE(EXCLUDED.contacts_count, clean_companies.contacts_count)
                    ELSE clean_companies.contacts_count
                  END,
                  pcb_suppliers         = ARRAY(
                    SELECT DISTINCT unnest(clean_companies.pcb_suppliers || EXCLUDED.pcb_suppliers)
                  ),
                  aliases               = ARRAY(
                    SELECT DISTINCT unnest(clean_companies.aliases || EXCLUDED.aliases)
                  ),
                  latest_tendata_summary_at = GREATEST(
                    COALESCE(clean_companies.latest_tendata_summary_at, '-infinity'::timestamptz),
                    COALESCE(EXCLUDED.latest_tendata_summary_at, '-infinity'::timestamptz)
                  ),
                  updated_at            = now()
                RETURNING id
                """
            ),
            {
                "name": name,
                "country_iso3": country_iso3.strip(),
                "domain": domain_clean,
                "industry_desc": raw.get("industry_desc") or raw.get("industry"),
                "product_tags": product_tags,
                "employee_num": employee_num,
                "trade_amount_3y_usd": trade_amount_3y_usd,
                "trade_count": trade_count_val,
                "contacts_count": contacts_count,
                "pcb_suppliers": pcb_suppliers,
                "aliases": aliases,
                "source_created_at": source_created_at,
            },
        )
        row = result.mappings().first()
        return str(row["id"])

    async def _materialize_clean_contacts_for_raw_source(
        self,
        conn: AsyncConnection,
        *,
        raw_table: str,
        raw_row_id: int,
        raw: dict,
    ) -> None:
        source_type = "waimaotong" if raw_table == "waimaotong_raw_companies" else "tendata"
        clean_id = await self._clean_company_id_for_source(
            conn,
            source_type=source_type,
            raw_row_id=int(raw_row_id),
        )
        if clean_id is None:
            return
        await self._upsert_clean_contacts_from_payload(conn, clean_id=clean_id, raw=raw)
        if source_type == "tendata":
            await self._materialize_tendata_raw_contacts_for_source(
                conn,
                clean_id=clean_id,
                raw_company_id=int(raw_row_id),
            )

    async def _clean_company_id_for_source(
        self,
        conn: AsyncConnection,
        *,
        source_type: str,
        raw_row_id: int,
    ) -> int | None:
        result = await conn.execute(
            text(
                """
                SELECT clean_company_id
                FROM clean_company_sources
                WHERE source_type = :source_type
                  AND source_company_id = :raw_row_id
                """
            ),
            {"source_type": source_type, "raw_row_id": raw_row_id},
        )
        value = result.scalar_one_or_none()
        return int(value) if value is not None else None

    async def _upsert_clean_contacts_from_payload(
        self,
        conn: AsyncConnection,
        *,
        clean_id: int,
        raw: dict,
    ) -> int:
        contacts = raw.get("contacts")
        if contacts is None and isinstance(raw.get("raw_payload"), dict):
            contacts = raw["raw_payload"].get("contacts")
        if not isinstance(contacts, list):
            return 0

        changed = 0
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            email = self._clean_text(contact.get("email"))
            if not email:
                continue
            await conn.execute(
                text(
                    """
                    INSERT INTO clean_contacts
                      (clean_company_id, name, position, email, phone)
                    VALUES
                      (:clean_company_id, :name, :position, :email, :phone)
                    ON CONFLICT (clean_company_id, email) WHERE email IS NOT NULL DO UPDATE
                    SET name = COALESCE(EXCLUDED.name, clean_contacts.name),
                        position = COALESCE(EXCLUDED.position, clean_contacts.position),
                        phone = COALESCE(EXCLUDED.phone, clean_contacts.phone),
                        updated_at = now()
                    """
                ),
                {
                    "clean_company_id": int(clean_id),
                    "name": self._clean_text(contact.get("name")),
                    "position": self._clean_text(contact.get("position") or contact.get("title")),
                    "email": email,
                    "phone": self._clean_text(contact.get("phone") or contact.get("mobile")),
                },
            )
            changed += 1
        return changed

    async def _materialize_tendata_raw_contacts_for_source(
        self,
        conn: AsyncConnection,
        *,
        clean_id: int,
        raw_company_id: int,
    ) -> int:
        result = await conn.execute(
            text(
                """
                WITH ranked_contacts AS (
                  SELECT
                    CAST(:clean_id AS bigint) AS clean_company_id,
                    trc.name,
                    trc.position,
                    trc.email,
                    trc.phone,
                    row_number() OVER (
                      PARTITION BY lower(trc.email::text)
                      ORDER BY
                        (
                          CASE WHEN trc.name IS NOT NULL AND btrim(trc.name) <> '' THEN 1 ELSE 0 END
                          + CASE WHEN trc.position IS NOT NULL AND btrim(trc.position) <> '' THEN 1 ELSE 0 END
                          + CASE WHEN trc.phone IS NOT NULL AND btrim(trc.phone) <> '' THEN 1 ELSE 0 END
                        ) DESC,
                        trc.created_at DESC NULLS LAST,
                        trc.id DESC
                    ) AS rank
                  FROM tendata_raw_contacts trc
                  WHERE trc.raw_company_id = :raw_company_id
                    AND trc.email IS NOT NULL
                ),
                deduped_contacts AS (
                  SELECT clean_company_id, name, position, email, phone
                  FROM ranked_contacts
                  WHERE rank = 1
                )
                INSERT INTO clean_contacts
                  (clean_company_id, name, position, email, phone)
                SELECT clean_company_id, name, position, email, phone
                FROM deduped_contacts
                ON CONFLICT (clean_company_id, email) WHERE email IS NOT NULL DO UPDATE
                SET name = COALESCE(EXCLUDED.name, clean_contacts.name),
                    position = COALESCE(EXCLUDED.position, clean_contacts.position),
                    phone = COALESCE(EXCLUDED.phone, clean_contacts.phone),
                    updated_at = now()
                RETURNING id
                """
            ),
            {"clean_id": int(clean_id), "raw_company_id": int(raw_company_id)},
        )
        return len(result.mappings().all())

    async def backfill_tendata_raw_contacts(
        self,
        conn: AsyncConnection,
        *,
        dry_run: bool = True,
        raw_company_id: int | None = None,
    ) -> dict:
        stats_result = await conn.execute(
            text(
                """
                    WITH candidates AS (
                      SELECT
                        ccs.clean_company_id,
                        trc.id AS raw_contact_id,
                        trc.name,
                        trc.position,
                        trc.email,
                        trc.phone,
                        trc.created_at,
                        row_number() OVER (
                          PARTITION BY ccs.clean_company_id, lower(trc.email::text)
                          ORDER BY
                            (
                              CASE WHEN trc.name IS NOT NULL AND btrim(trc.name) <> '' THEN 1 ELSE 0 END
                              + CASE WHEN trc.position IS NOT NULL AND btrim(trc.position) <> '' THEN 1 ELSE 0 END
                              + CASE WHEN trc.phone IS NOT NULL AND btrim(trc.phone) <> '' THEN 1 ELSE 0 END
                            ) DESC,
                            trc.created_at DESC NULLS LAST,
                            trc.id DESC
                        ) AS rank
                      FROM clean_company_sources ccs
                      JOIN tendata_raw_contacts trc
                        ON ccs.source_type = 'tendata'
                       AND ccs.source_company_id = trc.raw_company_id
                      WHERE trc.email IS NOT NULL
                        AND (
                          CAST(:raw_company_id AS bigint) IS NULL
                          OR trc.raw_company_id = CAST(:raw_company_id AS bigint)
                        )
                    )
                    SELECT
                      count(DISTINCT clean_company_id)::int AS clean_company_rows,
                      count(*)::int AS candidate_contact_rows,
                      count(*) FILTER (WHERE rank = 1)::int AS deduped_contact_rows
                    FROM candidates
                    """
            ),
            {"raw_company_id": int(raw_company_id) if raw_company_id is not None else None},
        )
        stats = stats_result.mappings().one()
        summary = {
            "dry_run": dry_run,
            "clean_company_rows": stats["clean_company_rows"] or 0,
            "candidate_contact_rows": stats["candidate_contact_rows"] or 0,
            "deduped_contact_rows": stats["deduped_contact_rows"] or 0,
            "inserted_or_updated_rows": 0,
        }
        if dry_run:
            return summary

        result = await conn.execute(
            text(
                """
                WITH candidates AS (
                  SELECT
                    ccs.clean_company_id,
                    trc.id AS raw_contact_id,
                    trc.name,
                    trc.position,
                    trc.email,
                    trc.phone,
                    trc.created_at,
                    row_number() OVER (
                      PARTITION BY ccs.clean_company_id, lower(trc.email::text)
                      ORDER BY
                        (
                          CASE WHEN trc.name IS NOT NULL AND btrim(trc.name) <> '' THEN 1 ELSE 0 END
                          + CASE WHEN trc.position IS NOT NULL AND btrim(trc.position) <> '' THEN 1 ELSE 0 END
                          + CASE WHEN trc.phone IS NOT NULL AND btrim(trc.phone) <> '' THEN 1 ELSE 0 END
                        ) DESC,
                        trc.created_at DESC NULLS LAST,
                        trc.id DESC
                    ) AS rank
                  FROM clean_company_sources ccs
                  JOIN tendata_raw_contacts trc
                    ON ccs.source_type = 'tendata'
                   AND ccs.source_company_id = trc.raw_company_id
                  WHERE trc.email IS NOT NULL
                    AND (
                      CAST(:raw_company_id AS bigint) IS NULL
                      OR trc.raw_company_id = CAST(:raw_company_id AS bigint)
                    )
                ),
                deduped_contacts AS (
                  SELECT clean_company_id, name, position, email, phone
                  FROM candidates
                  WHERE rank = 1
                )
                INSERT INTO clean_contacts
                  (clean_company_id, name, position, email, phone)
                SELECT clean_company_id, name, position, email, phone
                FROM deduped_contacts
                ON CONFLICT (clean_company_id, email) WHERE email IS NOT NULL DO UPDATE
                SET name = COALESCE(EXCLUDED.name, clean_contacts.name),
                    position = COALESCE(EXCLUDED.position, clean_contacts.position),
                    phone = COALESCE(EXCLUDED.phone, clean_contacts.phone),
                    updated_at = now()
                RETURNING id
                """
            ),
            {"raw_company_id": int(raw_company_id) if raw_company_id is not None else None},
        )
        summary["inserted_or_updated_rows"] = len(result.mappings().all())
        return summary

    def _clean_text(self, value) -> str | None:
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value or None

    async def _upsert_clean_company_source(
        self,
        conn: AsyncConnection,
        *,
        clean_id: str,
        raw_table: str,
        raw: dict,
    ) -> None:
        source_type = "waimaotong" if raw_table == "waimaotong_raw_companies" else "tendata"
        source_key = "|".join(
            str(part)
            for part in (raw.get("source_id"), raw.get("collection_type"))
            if part is not None
        )
        await conn.execute(
            text(
                """
                INSERT INTO clean_company_sources
                  (clean_company_id, source_type, source_company_id, source_key)
                VALUES
                  (:clean_id, :source_type, :source_company_id, :source_key)
                ON CONFLICT (source_type, source_company_id) DO UPDATE
                SET clean_company_id = EXCLUDED.clean_company_id,
                    source_key = COALESCE(EXCLUDED.source_key, clean_company_sources.source_key)
                """
            ),
            {
                "clean_id": int(clean_id),
                "source_type": source_type,
                "source_company_id": int(raw["id"]),
                "source_key": source_key or None,
            },
        )

    async def _upsert_clean_company_keyword(
        self,
        conn: AsyncConnection,
        *,
        clean_id: str,
        keyword_master_id: str,
    ) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO clean_company_keywords (clean_company_id, keyword_master_id)
                VALUES (:clean_id, :keyword_master_id)
                ON CONFLICT (clean_company_id, keyword_master_id) DO NOTHING
                """
            ),
            {"clean_id": int(clean_id), "keyword_master_id": keyword_master_id},
        )

    async def _materialize_tenant_companies_for_keyword(
        self, conn: AsyncConnection, *, clean_id: str, keyword_master_id: str
    ) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO tenant_companies
                  (tenant_id, clean_company_id, business_status, data_status, visibility_status)
                SELECT
                  tk.tenant_id,
                  :clean_id,
                  'new',
                  CASE
                    WHEN NOT EXISTS (
                      SELECT 1 FROM clean_contacts cc WHERE cc.clean_company_id = :clean_id
                    ) THEN 'missing_contacts'
                    WHEN (
                      SELECT count(*) FROM clean_companies c
                      WHERE c.id = :clean_id
                        AND (
                          c.website IS NOT NULL
                          OR c.industry_desc IS NOT NULL
                          OR cardinality(c.product_tags) > 0
                          OR cardinality(c.pcb_suppliers) > 0
                        )
                    ) = 0 THEN 'insufficient_data'
                    ELSE 'ready'
                  END,
                  'visible'
                FROM tenant_keyword tk
                WHERE tk.keyword_master_id = :keyword_master_id
                  AND tk.status = 'active'
                ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
                SET visibility_status = 'visible',
                    data_status = EXCLUDED.data_status,
                    updated_at = now()
                """
            ),
            {"clean_id": int(clean_id), "keyword_master_id": keyword_master_id},
        )

    async def _mark_raw_cleanup_issue(
        self,
        conn: AsyncConnection,
        *,
        raw_table: str,
        raw_row_id: str,
        reason: str,
        detail: dict,
    ) -> None:
        if raw_table != "tendata_raw_companies":
            return
        await conn.execute(
            text(
                """
                UPDATE tendata_raw_companies
                SET enrichment_error = CAST(:error AS jsonb)
                WHERE id = :id
                """
            ),
            {
                "id": int(raw_row_id),
                "error": json.dumps({"stage": "cleanup", "reason": reason, **detail}, ensure_ascii=False),
            },
        )

    async def _reset_retryable_failures(self, conn: AsyncConnection) -> int:
        result = await conn.execute(
            text(
                """
                UPDATE cleanup_queue
                SET status = 'pending'
                WHERE status = 'failed' AND attempts < :max_attempts
                RETURNING id
                """
            ),
            {"max_attempts": _MAX_ATTEMPTS},
        )
        count = len(result.fetchall())
        if count:
            logger.info("CleanupService: reset %d failed rows to pending", count)
        return count
