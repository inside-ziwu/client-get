"""同行公司清洗服务。

将 lixiaoyun_raw_companies 的原始数据按 identity 去重，
写入 peer_companies / peer_company_contacts 等清洗层表。

设计决策参考: openspec/changes/peer-cleaning-v2/design.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


IDENTITY_RULE_VERSION = "peer-cleaning-v1"

# 11 个 display 字段名，用于 _build_display_set_clause
_DISPLAY_TEXT_FIELDS = [
    "name", "english_name", "domain", "website_host",
    "source_id", "legalperson", "uncid",
    "reg_capital", "employee_scale", "reg_address",
]
_DISPLAY_DATE_FIELDS = ["esdate"]


@dataclass(frozen=True)
class PeerIdentity:
    identity_type: str
    identity_value: str
    identity_source: str
    identity_confidence: float


def normalize_website_host(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    candidate = raw if "://" in raw else f"//{raw}"
    parsed = urlparse(candidate)
    host = parsed.hostname or ""
    host = host.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _build_display_set_clause(table_alias: str, param_prefix: str = "") -> str:
    """生成 11 个 display 字段的「最新非空覆盖」SQL SET 片段。

    D1 策略: COALESCE(NULLIF(new, ''), existing) — 新值非空则覆盖，新值为空则保留。
    D7: 统一由此 helper 生成，避免 _upsert_peer_company 与 _update_existing_peer_display 不一致。
    """
    parts: list[str] = []
    for field in _DISPLAY_TEXT_FIELDS:
        param = f":{param_prefix}{field}" if param_prefix else f":{field}"
        parts.append(
            f"{field} = COALESCE(NULLIF({param}, ''), {table_alias}.{field})"
        )
    for field in _DISPLAY_DATE_FIELDS:
        param = f":{param_prefix}{field}" if param_prefix else f":{field}"
        parts.append(
            f"{field} = COALESCE({param}, {table_alias}.{field})"
        )
    return ",\n                    ".join(parts)


class PeerCompanyCleaningService:
    def derive_identity(self, row: dict) -> PeerIdentity | None:
        host = normalize_website_host(row.get("domain") or row.get("website"))
        if host:
            return PeerIdentity(
                identity_type="website_host",
                identity_value=host,
                identity_source="website_host",
                identity_confidence=1.0,
            )

        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            return PeerIdentity(
                identity_type="source_id",
                identity_value=source_id,
                identity_source="lixiaoyun_source_id",
                identity_confidence=0.8,
            )
        return None

    async def clean_raw_company(
        self,
        conn: AsyncConnection,
        *,
        raw_company_id: int,
        row: dict,
        allow_existing_source_peer: bool = True,
        upsert_contacts: bool = True,
    ) -> str | None:
        existing_peer_id: str | None = None
        if allow_existing_source_peer:
            existing_result = await conn.execute(
                text(
                    """
                    SELECT peer_company_id::text AS peer_company_id
                    FROM peer_company_sources
                    WHERE raw_company_id = :raw_company_id
                    """
                ),
                {"raw_company_id": raw_company_id},
            )
            existing = existing_result.mappings().first()
            if existing:
                existing_peer_id = existing["peer_company_id"]

        identity = self.derive_identity(row)

        # D2: source_id 双向复用 — 任何带 source_id 的 raw（不仅限 identity_type=source_id）
        # 都先查 peer_company_sources 是否已有同 source_id 的 peer，有则复用
        if existing_peer_id is None:
            source_id = str(row.get("source_id") or "").strip()
            if source_id:
                source_peer_result = await conn.execute(
                    text(
                        """
                        SELECT peer_company_id::text AS peer_company_id
                        FROM peer_company_sources
                        WHERE source_id = :sid
                        LIMIT 1
                        """
                    ),
                    {"sid": source_id},
                )
                source_peer = source_peer_result.mappings().first()
                if source_peer:
                    existing_peer_id = source_peer["peer_company_id"]

        if existing_peer_id:
            peer_id = existing_peer_id
            await self._update_existing_peer_display(conn, peer_id=peer_id, row=row)
        elif identity is None:
            return None
        else:
            peer_id = await self._upsert_peer_company(conn, identity=identity, row=row)

        await self._upsert_peer_keywords(
            conn,
            peer_id=peer_id,
            keyword_master_id=row.get("keyword_master_id"),
        )
        await self._upsert_peer_source(
            conn,
            peer_id=peer_id,
            raw_company_id=raw_company_id,
            source_id=row.get("source_id"),
        )
        if upsert_contacts:
            contacts = self._extract_contacts(row)
            for contact in contacts:
                await self._upsert_peer_contact(
                    conn,
                    peer_company_id=peer_id,
                    raw_company_id=raw_company_id,
                    contact=contact,
                )
        await self.refresh_peer_contact_count(conn, peer_id=peer_id)
        return peer_id

    async def _upsert_peer_company(
        self,
        conn: AsyncConnection,
        *,
        identity: PeerIdentity,
        row: dict,
    ) -> str:
        display_set = _build_display_set_clause("peer_companies")
        website_host = normalize_website_host(row.get("domain") or row.get("website"))
        result = await conn.execute(
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
                        WHEN peer_companies.uncid IS NOT NULL
                         AND EXCLUDED.uncid IS NOT NULL
                         AND peer_companies.uncid <> EXCLUDED.uncid THEN 1
                        WHEN peer_companies.legalperson IS NOT NULL
                         AND EXCLUDED.legalperson IS NOT NULL
                         AND peer_companies.legalperson <> EXCLUDED.legalperson THEN 1
                        WHEN peer_companies.name IS NOT NULL
                         AND EXCLUDED.name IS NOT NULL
                         AND peer_companies.name <> EXCLUDED.name THEN 1
                        ELSE 0
                    END,
                    last_seen_at = now()
                RETURNING id::text AS id
                """
            ),
            {
                **self._display_params(row),
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
                "website_host": website_host,
            },
        )
        return str(result.mappings().one()["id"])

    async def _update_existing_peer_display(
        self,
        conn: AsyncConnection,
        *,
        peer_id: str,
        row: dict,
    ) -> None:
        display_set = _build_display_set_clause("peer_companies")
        website_host = normalize_website_host(row.get("domain") or row.get("website"))
        await conn.execute(
            text(
                f"""
                UPDATE peer_companies
                SET {display_set},
                    last_seen_at = now()
                WHERE id = :peer_id
                """
            ),
            {**self._display_params(row), "website_host": website_host, "peer_id": peer_id},
        )

    async def _upsert_peer_keywords(
        self,
        conn: AsyncConnection,
        *,
        peer_id: str,
        keyword_master_id: str | None,
    ) -> None:
        if not keyword_master_id:
            return
        await conn.execute(
            text(
                """
                INSERT INTO peer_company_keywords (peer_company_id, keyword_master_id)
                VALUES (CAST(:peer_id AS uuid), CAST(:keyword_master_id AS uuid))
                ON CONFLICT (peer_company_id, keyword_master_id) DO NOTHING
                """
            ),
            {"peer_id": peer_id, "keyword_master_id": str(keyword_master_id)},
        )

    async def _upsert_peer_source(
        self,
        conn: AsyncConnection,
        *,
        peer_id: str,
        raw_company_id: int,
        source_id: str | None,
    ) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO peer_company_sources (peer_company_id, raw_company_id, source_id)
                VALUES (CAST(:peer_id AS uuid), :raw_company_id, :source_id)
                ON CONFLICT (raw_company_id) DO NOTHING
                """
            ),
            {"peer_id": peer_id, "raw_company_id": raw_company_id, "source_id": source_id},
        )

    async def _upsert_peer_contact(
        self,
        conn: AsyncConnection,
        *,
        peer_company_id: str,
        raw_company_id: int,
        contact: dict,
    ) -> None:
        """D3: 两步 upsert 联系人到 peer_company_contacts。

        三级去重: email → source_contact_id → name+phone
        D11: email 做 lower(trim()) 规范化
        """
        name = (contact.get("name") or "").strip() or None
        email_raw = (contact.get("email") or "").strip()
        email = email_raw.lower() if email_raw else None  # D11: 规范化
        position = (contact.get("position") or contact.get("title") or "").strip() or None
        phone = (contact.get("phone") or "").strip() or None
        mobile = (contact.get("mobile") or "").strip() or None
        source_contact_id = (
            contact.get("source_contact_id") or contact.get("id") or ""
        ).strip() or None

        # 跳过：无 name 且无 email 的联系人
        if not name and not email:
            return

        params = {
            "peer_company_id": peer_company_id,
            "email": email,
            "name": name,
            "position": position,
            "phone": phone,
            "mobile": mobile,
            "source_contact_id": str(source_contact_id) if source_contact_id else None,
            "raw_company_id": raw_company_id,
        }

        # 第一步：按 source_contact_id 查已有行，如果新数据有 email 则补上
        if source_contact_id:
            existing_result = await conn.execute(
                text(
                    """
                    SELECT id, email
                    FROM peer_company_contacts
                    WHERE peer_company_id = CAST(:peer_company_id AS uuid)
                      AND source_contact_id = :source_contact_id
                    """
                ),
                {"peer_company_id": peer_company_id, "source_contact_id": str(source_contact_id)},
            )
            existing = existing_result.mappings().first()
            if existing and email and not (existing["email"] or "").strip():
                # 升级：补上 email，同时更新其他字段
                await conn.execute(
                    text(
                        """
                        UPDATE peer_company_contacts
                        SET email = :email,
                            name = COALESCE(NULLIF(:name, ''), peer_company_contacts.name),
                            position = COALESCE(NULLIF(:position, ''), peer_company_contacts.position),
                            phone = COALESCE(NULLIF(:phone, ''), peer_company_contacts.phone),
                            mobile = COALESCE(NULLIF(:mobile, ''), peer_company_contacts.mobile),
                            raw_company_id = :raw_company_id,
                            updated_at = now()
                        WHERE id = :existing_id
                        """
                    ),
                    {**params, "existing_id": existing["id"]},
                )
                return

        # 第二步：INSERT ON CONFLICT — 三级条件唯一索引自动处理去重
        await conn.execute(
            text(
                """
                INSERT INTO peer_company_contacts
                  (peer_company_id, email, name, position, phone, mobile,
                   source_contact_id, raw_company_id)
                VALUES
                  (CAST(:peer_company_id AS uuid), :email, :name, :position, :phone, :mobile,
                   :source_contact_id, :raw_company_id)
                ON CONFLICT DO UPDATE
                SET name = COALESCE(NULLIF(EXCLUDED.name, ''), peer_company_contacts.name),
                    position = COALESCE(NULLIF(EXCLUDED.position, ''), peer_company_contacts.position),
                    phone = COALESCE(NULLIF(EXCLUDED.phone, ''), peer_company_contacts.phone),
                    mobile = COALESCE(NULLIF(EXCLUDED.mobile, ''), peer_company_contacts.mobile),
                    raw_company_id = EXCLUDED.raw_company_id,
                    updated_at = now()
                """
            ),
            params,
        )

    async def refresh_peer_contact_count(self, conn: AsyncConnection, *, peer_id: str) -> None:
        """D3: 直接从 peer_company_contacts 计数，替代原有的跨表 CTE。"""
        await conn.execute(
            text(
                """
                UPDATE peer_companies
                SET contact_count = (
                    SELECT COUNT(*)
                    FROM peer_company_contacts
                    WHERE peer_company_id = CAST(:peer_id AS uuid)
                )
                WHERE id = CAST(:peer_id AS uuid)
                """
            ),
            {"peer_id": peer_id},
        )

    def _display_params(self, row: dict) -> dict:
        return {
            "name": row.get("name"),
            "english_name": row.get("company_name_en") or row.get("english_name"),
            "domain": row.get("domain") or row.get("website"),
            "source_id": row.get("source_id"),
            "esdate": row.get("esdate") or None,
            "legalperson": row.get("legalperson"),
            "uncid": row.get("uncid"),
            "reg_capital": row.get("reg_capital"),
            "employee_scale": row.get("employee_scale"),
            "reg_address": row.get("reg_address"),
        }

    def _extract_contacts(self, row: dict) -> list[dict]:
        raw_payload = row.get("raw_payload") or row.get("raw_data") or {}
        contacts = raw_payload.get("lx_contacts") if isinstance(raw_payload, dict) else None
        return [c for c in contacts if isinstance(c, dict)] if isinstance(contacts, list) else []
