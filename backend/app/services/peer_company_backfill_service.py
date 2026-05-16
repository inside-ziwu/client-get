"""同行公司批量回填服务。

遍历 lixiaoyun_raw_companies 按 id ASC 顺序清洗，
每 batch_size 条为一个事务，记录 last_processed_id 支持断点续传。

设计决策参考: openspec/changes/peer-cleaning-v2/design.md D3.2
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.services.peer_company_cleaning_service import PeerCompanyCleaningService


@dataclass
class PeerCompanyBackfillStats:
    raw_total: int = 0
    candidate_raw_count: int = 0
    generated_peer_count: int = 0
    source_relation_count: int = 0
    keyword_relation_count: int = 0
    skipped_missing_identity: int = 0
    website_identity_count: int = 0
    source_id_identity_count: int = 0
    conflict_candidate_count: int = 0
    english_name_count: int = 0
    peer_total_after: int = 0
    contact_count: int = 0

    def to_dict(self) -> dict:
        peer_denominator = self.peer_total_after or self.generated_peer_count
        raw = asdict(self)
        raw["dedup_rate"] = (
            1 - (peer_denominator / self.raw_total) if self.raw_total else 0
        )
        raw["english_name_coverage"] = (
            self.english_name_count / peer_denominator if peer_denominator else 0
        )
        return raw


class PeerCompanyBackfillService:
    def __init__(self) -> None:
        self.cleaning = PeerCompanyCleaningService()

    async def run_batch(
        self,
        conn: AsyncConnection,
        *,
        last_processed_id: int = 0,
        batch_size: int = 500,
        dry_run: bool = True,
    ) -> tuple[dict, int]:
        """处理一个批次的 raw 数据。

        返回 (stats_dict, new_last_processed_id)。
        调用方负责 commit 和循环调用。
        """
        stats = PeerCompanyBackfillStats()
        identity_keys: set[tuple[str, str]] = set()
        english_identity_keys: set[tuple[str, str]] = set()
        current_last_id = last_processed_id

        result = await conn.execute(
            text(
                """
                SELECT
                    id,
                    source_id,
                    name,
                    english_name,
                    domain,
                    esdate,
                    legalperson,
                    uncid,
                    reg_capital,
                    employee_scale,
                    reg_address,
                    keyword_master_id::text AS keyword_master_id,
                    raw_payload
                FROM lixiaoyun_raw_companies
                WHERE id > :last_id
                ORDER BY id
                LIMIT :limit
                """
            ),
            {"last_id": last_processed_id, "limit": batch_size},
        )
        rows = result.mappings().all()

        for db_row in rows:
            row = dict(db_row)
            current_last_id = int(row["id"])
            stats.raw_total += 1
            identity = self.cleaning.derive_identity(row)
            if identity is None:
                stats.skipped_missing_identity += 1
                continue

            stats.candidate_raw_count += 1
            if identity.identity_type == "website_host":
                stats.website_identity_count += 1
            else:
                stats.source_id_identity_count += 1
            identity_key = (identity.identity_type, identity.identity_value)
            identity_keys.add(identity_key)
            if row.get("english_name"):
                english_identity_keys.add(identity_key)

            if dry_run:
                continue

            await self.cleaning.clean_raw_company(
                conn,
                raw_company_id=int(row["id"]),
                row=row,
                upsert_contacts=True,
            )

        stats.generated_peer_count = len(identity_keys)
        if not dry_run:
            stats.source_relation_count = await self._count_table(conn, "peer_company_sources")
            stats.keyword_relation_count = await self._count_table(conn, "peer_company_keywords")
            stats.conflict_candidate_count = await self._count_conflicts(conn)
            stats.peer_total_after = await self._count_table(conn, "peer_companies")
            stats.english_name_count = await self._count_peers_with_english_name(conn)
            stats.contact_count = await self._count_table(conn, "peer_company_contacts")
        else:
            stats.english_name_count = len(english_identity_keys)

        return stats.to_dict(), current_last_id

    async def run(
        self,
        conn: AsyncConnection,
        *,
        dry_run: bool = True,
        batch_size: int = 500,
    ) -> dict:
        """兼容旧接口：一次性跑完所有批次（适用于 dry_run 预估）。"""
        all_stats = PeerCompanyBackfillStats()
        last_id = 0
        identity_keys: set[tuple[str, str]] = set()
        english_identity_keys: set[tuple[str, str]] = set()

        while True:
            result = await conn.execute(
                text(
                    """
                    SELECT
                        id,
                        source_id,
                        name,
                        english_name,
                        domain,
                        esdate,
                        legalperson,
                        uncid,
                        reg_capital,
                        employee_scale,
                        reg_address,
                        keyword_master_id::text AS keyword_master_id,
                        raw_payload
                    FROM lixiaoyun_raw_companies
                    WHERE id > :last_id
                    ORDER BY id
                    LIMIT :limit
                    """
                ),
                {"last_id": last_id, "limit": batch_size},
            )
            rows = result.mappings().all()
            if not rows:
                break

            for db_row in rows:
                row = dict(db_row)
                last_id = int(row["id"])
                all_stats.raw_total += 1
                identity = self.cleaning.derive_identity(row)
                if identity is None:
                    all_stats.skipped_missing_identity += 1
                    continue

                all_stats.candidate_raw_count += 1
                if identity.identity_type == "website_host":
                    all_stats.website_identity_count += 1
                else:
                    all_stats.source_id_identity_count += 1
                identity_key = (identity.identity_type, identity.identity_value)
                identity_keys.add(identity_key)
                if row.get("english_name"):
                    english_identity_keys.add(identity_key)

                if dry_run:
                    continue

                await self.cleaning.clean_raw_company(
                    conn,
                    raw_company_id=int(row["id"]),
                    row=row,
                    upsert_contacts=True,
                )

        all_stats.generated_peer_count = len(identity_keys)
        if not dry_run:
            all_stats.source_relation_count = await self._count_table(conn, "peer_company_sources")
            all_stats.keyword_relation_count = await self._count_table(conn, "peer_company_keywords")
            all_stats.conflict_candidate_count = await self._count_conflicts(conn)
            all_stats.peer_total_after = await self._count_table(conn, "peer_companies")
            all_stats.english_name_count = await self._count_peers_with_english_name(conn)
            all_stats.contact_count = await self._count_table(conn, "peer_company_contacts")
        else:
            all_stats.english_name_count = len(english_identity_keys)
        return all_stats.to_dict()

    async def _count_table(self, conn: AsyncConnection, table: str) -> int:
        allowed = {
            "peer_companies", "peer_company_sources",
            "peer_company_keywords", "peer_company_contacts",
        }
        if table not in allowed:
            raise ValueError(f"unexpected table: {table}")
        result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        return int(result.scalar_one() or 0)

    async def _count_conflicts(self, conn: AsyncConnection) -> int:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM peer_companies WHERE conflict_count > 0")
        )
        return int(result.scalar_one() or 0)

    async def _count_peers_with_english_name(self, conn: AsyncConnection) -> int:
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM peer_companies
                WHERE english_name IS NOT NULL AND trim(english_name) <> ''
                """
            )
        )
        return int(result.scalar_one() or 0)
