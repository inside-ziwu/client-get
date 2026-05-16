import json
import logging
from datetime import date as date_type, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.internal_idempotency_service import InternalIdempotencyService
from app.utils.country import to_iso3

logger = logging.getLogger(__name__)
_AUTO_CREATE_TENDATA_STAGE2 = False
_BEIJING_TZ = ZoneInfo("Asia/Shanghai")
_DEFAULT_LIXIAOYUN_PAGE_SIZE = 10
_MAX_LIXIAOYUN_PAGE_SIZE = 100
_ENRICHMENT_STAGES = {
    "detail": ("detail_status", "detail_fetched_at"),
    "trade": ("trade_status", "trade_fetched_at"),
    "contacts": ("contacts_status", "contacts_fetched_at"),
}


def _parse_date(value) -> date_type | None:
    """将 'YYYY-MM-DD' 字符串或 datetime.date 对象转为 datetime.date，供 asyncpg DATE 列使用。"""
    if not value:
        return None
    if isinstance(value, date_type):
        return value
    try:
        return date_type.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _to_pg_array(values: list | None) -> list:
    """Normalize values for asyncpg text[] binding."""
    if not values:
        return []
    return [str(v) for v in values if v is not None]


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item is not None]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [value]


def _json(value) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _raw_payload_with_contacts(row: dict) -> dict:
    payload = row.get("raw_payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if "contacts" in row:
        payload = {**payload, "contacts": row.get("contacts") or []}
    return payload


class CollectionService:
    def __init__(self) -> None:
        self.idempotency = InternalIdempotencyService()

    async def _upsert_waimaotong_raw(self, conn: AsyncConnection, task_id: str, row: dict) -> str:
        source_id = row.get("source_id")
        if not source_id:
            return ""

        keyword_master_id = row.get("keyword_master_id")
        if not keyword_master_id:
            keyword_master_id = await self._keyword_master_id_for_task(conn, task_id)
        collection_type = row.get("collection_type") or "direct_search"
        search_payload = (
            row.get("search_payload") or row.get("raw_payload") or row.get("raw_data") or {}
        )
        detail_payload = row.get("detail_payload")
        trade_payload = row.get("trade_payload")
        contacts_status = row.get("contacts_status") or (
            "fetched"
            if "contacts_count" in row and (row.get("contacts_count") or 0) == 0
            else "pending"
        )

        result = await conn.execute(
            text(
                """
                INSERT INTO waimaotong_raw_companies
                  (keyword_master_id, source_id, collection_type, real_id, name, country_iso3,
                   domain, industry, address, phone, employee_size, founded_year, description,
                   products, source_tags, emails, trade_amount_3y_usd, trade_count, contacts_count,
                   has_trade_data, customs_data, search_payload, detail_payload, trade_payload,
                   raw_payload, detail_status, detail_fetched_at, trade_status, trade_fetched_at,
                   contacts_status, contacts_fetched_at, enrichment_error, updated_at)
                VALUES
                  (:keyword_master_id, :source_id, :collection_type, :real_id, :name, :country_iso3,
                   :domain, :industry, :address, :phone, :employee_size, :founded_year, :description,
                   CAST(:products AS text[]), CAST(:source_tags AS text[]), CAST(:emails AS text[]),
                   :trade_amount_3y_usd, :trade_count, :contacts_count, :has_trade_data,
                   CAST(:customs_data AS jsonb), CAST(:search_payload AS jsonb),
                   CAST(:detail_payload AS jsonb), CAST(:trade_payload AS jsonb),
                   CAST(:raw_payload AS jsonb), :detail_status, :detail_fetched_at,
                   :trade_status, :trade_fetched_at, :contacts_status, :contacts_fetched_at,
                   CAST(:enrichment_error AS jsonb), now())
                ON CONFLICT (keyword_master_id, source_id, collection_type) DO UPDATE
                SET search_payload = COALESCE(EXCLUDED.search_payload, waimaotong_raw_companies.search_payload),
                    detail_payload = COALESCE(EXCLUDED.detail_payload, waimaotong_raw_companies.detail_payload),
                    trade_payload = COALESCE(EXCLUDED.trade_payload, waimaotong_raw_companies.trade_payload),
                    raw_payload = COALESCE(EXCLUDED.raw_payload, waimaotong_raw_companies.raw_payload),
                    real_id = COALESCE(EXCLUDED.real_id, waimaotong_raw_companies.real_id),
                    name = COALESCE(EXCLUDED.name, waimaotong_raw_companies.name),
                    country_iso3 = COALESCE(EXCLUDED.country_iso3, waimaotong_raw_companies.country_iso3),
                    domain = COALESCE(EXCLUDED.domain, waimaotong_raw_companies.domain),
                    industry = COALESCE(EXCLUDED.industry, waimaotong_raw_companies.industry),
                    address = COALESCE(EXCLUDED.address, waimaotong_raw_companies.address),
                    phone = COALESCE(EXCLUDED.phone, waimaotong_raw_companies.phone),
                    employee_size = COALESCE(EXCLUDED.employee_size, waimaotong_raw_companies.employee_size),
                    founded_year = COALESCE(EXCLUDED.founded_year, waimaotong_raw_companies.founded_year),
                    description = COALESCE(EXCLUDED.description, waimaotong_raw_companies.description),
                    products = COALESCE(EXCLUDED.products, waimaotong_raw_companies.products),
                    source_tags = COALESCE(EXCLUDED.source_tags, waimaotong_raw_companies.source_tags),
                    emails = COALESCE(EXCLUDED.emails, waimaotong_raw_companies.emails),
                    trade_amount_3y_usd = COALESCE(EXCLUDED.trade_amount_3y_usd, waimaotong_raw_companies.trade_amount_3y_usd),
                    trade_count = COALESCE(EXCLUDED.trade_count, waimaotong_raw_companies.trade_count),
                    contacts_count = COALESCE(EXCLUDED.contacts_count, waimaotong_raw_companies.contacts_count),
                    has_trade_data = COALESCE(EXCLUDED.has_trade_data, waimaotong_raw_companies.has_trade_data),
                    customs_data = COALESCE(EXCLUDED.customs_data, waimaotong_raw_companies.customs_data),
                    detail_status = CASE
                      WHEN EXCLUDED.detail_status <> 'pending' THEN EXCLUDED.detail_status
                      ELSE waimaotong_raw_companies.detail_status
                    END,
                    detail_fetched_at = COALESCE(EXCLUDED.detail_fetched_at, waimaotong_raw_companies.detail_fetched_at),
                    trade_status = CASE
                      WHEN EXCLUDED.trade_status <> 'pending' THEN EXCLUDED.trade_status
                      ELSE waimaotong_raw_companies.trade_status
                    END,
                    trade_fetched_at = COALESCE(EXCLUDED.trade_fetched_at, waimaotong_raw_companies.trade_fetched_at),
                    contacts_status = CASE
                      WHEN EXCLUDED.contacts_status <> 'pending' THEN EXCLUDED.contacts_status
                      ELSE waimaotong_raw_companies.contacts_status
                    END,
                    contacts_fetched_at = COALESCE(EXCLUDED.contacts_fetched_at, waimaotong_raw_companies.contacts_fetched_at),
                    enrichment_error = COALESCE(EXCLUDED.enrichment_error, waimaotong_raw_companies.enrichment_error),
                    updated_at = now()
                RETURNING id
                """
            ),
            {
                "keyword_master_id": keyword_master_id,
                "source_id": source_id,
                "collection_type": collection_type,
                "real_id": row.get("real_id"),
                "name": row.get("name"),
                "country_iso3": to_iso3(row["country_iso3"]) if row.get("country_iso3") else None,
                "domain": row.get("domain") or row.get("website"),
                "industry": row.get("industry"),
                "address": row.get("address"),
                "phone": row.get("phone"),
                "employee_size": row.get("employee_size") or row.get("employee_num"),
                "founded_year": row.get("founded_year"),
                "description": row.get("description") or row.get("overview"),
                "products": _to_pg_array(_as_list(row.get("products"))),
                "source_tags": _to_pg_array(_as_list(row.get("source_tags"))),
                "emails": _to_pg_array(_as_list(row.get("emails"))),
                "trade_amount_3y_usd": row.get("trade_amount_3y_usd"),
                "trade_count": row.get("trade_count"),
                "contacts_count": row.get("contacts_count"),
                "has_trade_data": row.get("has_trade_data"),
                "customs_data": _json(row.get("customs_data"))
                if row.get("customs_data") is not None
                else None,
                "search_payload": _json(search_payload),
                "detail_payload": _json(detail_payload) if detail_payload is not None else None,
                "trade_payload": _json(trade_payload) if trade_payload is not None else None,
                "raw_payload": _json(
                    row.get("raw_payload") or row.get("raw_data") or search_payload
                ),
                "detail_status": row.get("detail_status", "pending"),
                "detail_fetched_at": row.get("detail_fetched_at"),
                "trade_status": row.get("trade_status", "pending"),
                "trade_fetched_at": row.get("trade_fetched_at"),
                "contacts_status": contacts_status,
                "contacts_fetched_at": row.get("contacts_fetched_at")
                or (datetime.now(timezone.utc) if contacts_status == "fetched" else None),
                "enrichment_error": _json(row.get("enrichment_error"))
                if row.get("enrichment_error") is not None
                else None,
            },
        )
        result_row = result.mappings().first()
        return str(result_row["id"])

    async def _upsert_waimaotong_raw_contact(
        self, conn: AsyncConnection, task_id: str, row: dict
    ) -> None:
        raw_company_id = row.get("raw_company_id")
        if not raw_company_id:
            source_company_id = row.get("source_company_id") or row.get("company_source_id")
            if not source_company_id:
                return
            collection_type = row.get("collection_type") or "direct_search"
            keyword_master_id = row.get(
                "keyword_master_id"
            ) or await self._keyword_master_id_for_task(conn, task_id)
            company_row = (
                (
                    await conn.execute(
                        text(
                            """
                        SELECT id
                        FROM waimaotong_raw_companies
                        WHERE source_id = :source_id
                          AND collection_type = :collection_type
                          AND (
                            keyword_master_id IS NOT DISTINCT FROM CAST(:keyword_master_id AS uuid)
                          )
                        ORDER BY id
                        LIMIT 1
                        """
                        ),
                        {
                            "source_id": source_company_id,
                            "collection_type": collection_type,
                            "keyword_master_id": keyword_master_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if not company_row:
                raw_company_id = await self._upsert_waimaotong_raw(
                    conn,
                    task_id,
                    {
                        "keyword_master_id": keyword_master_id,
                        "source_id": source_company_id,
                        "collection_type": collection_type,
                        "name": source_company_id,
                        "raw_payload": {},
                    },
                )
            else:
                raw_company_id = str(company_row["id"])
        if not raw_company_id:
            return

        raw_payload = row.get("raw_payload") or row.get("raw_data") or {}
        position = row.get("position") or row.get("title")
        conflict_target = "(raw_company_id, source_contact_id) WHERE source_contact_id IS NOT NULL"
        if not row.get("source_contact_id") and row.get("email"):
            conflict_target = (
                "(raw_company_id, email) WHERE source_contact_id IS NULL AND email IS NOT NULL"
            )
        on_conflict = f"""
                ON CONFLICT {conflict_target} DO UPDATE
                SET name = COALESCE(EXCLUDED.name, waimaotong_raw_contacts.name),
                    position = COALESCE(EXCLUDED.position, waimaotong_raw_contacts.position),
                    department = COALESCE(EXCLUDED.department, waimaotong_raw_contacts.department),
                    email_status = COALESCE(EXCLUDED.email_status, waimaotong_raw_contacts.email_status),
                    phone = COALESCE(EXCLUDED.phone, waimaotong_raw_contacts.phone),
                    mobile = COALESCE(EXCLUDED.mobile, waimaotong_raw_contacts.mobile),
                    linkedin = COALESCE(EXCLUDED.linkedin, waimaotong_raw_contacts.linkedin),
                    whatsapp = COALESCE(EXCLUDED.whatsapp, waimaotong_raw_contacts.whatsapp),
                    source = COALESCE(EXCLUDED.source, waimaotong_raw_contacts.source),
                    confidence = COALESCE(EXCLUDED.confidence, waimaotong_raw_contacts.confidence),
                    raw_payload = COALESCE(EXCLUDED.raw_payload, waimaotong_raw_contacts.raw_payload)
        """
        if not row.get("source_contact_id") and not row.get("email"):
            on_conflict = ""

        await conn.execute(
            text(
                f"""
                INSERT INTO waimaotong_raw_contacts
                  (raw_company_id, source_contact_id, name, position, department, email,
                   email_status, phone, mobile, linkedin, whatsapp, source, confidence, raw_payload)
                VALUES
                  (:raw_company_id, :source_contact_id, :name, :position, :department, :email,
                   :email_status, :phone, :mobile, :linkedin, :whatsapp, :source, :confidence,
                   CAST(:raw_payload AS jsonb))
                {on_conflict}
                """
            ),
            {
                "raw_company_id": int(raw_company_id),
                "source_contact_id": row.get("source_contact_id"),
                "name": row.get("name"),
                "position": position,
                "department": row.get("department"),
                "email": row.get("email"),
                "email_status": row.get("email_status"),
                "phone": row.get("phone"),
                "mobile": row.get("mobile"),
                "linkedin": row.get("linkedin"),
                "whatsapp": row.get("whatsapp"),
                "source": row.get("source"),
                "confidence": row.get("confidence"),
                "raw_payload": _json(raw_payload),
            },
        )
        await self._mark_enrichment_status(
            conn, "waimaotong_raw_companies", raw_company_id, "contacts", "fetched"
        )

    async def _upsert_tendata_raw(self, conn: AsyncConnection, task_id: str, row: dict) -> str:
        source_id = row.get("source_id") or row.get("tid")
        if not source_id:
            return ""

        keyword_master_id = row.get("keyword_master_id") or await self._keyword_master_id_for_task(
            conn, task_id
        )
        collection_type = row.get("collection_type") or "reverse_lookup"
        contacts_count = row.get("contacts_count", 0)
        contacts_status = row.get("contacts_status") or (
            "fetched" if "contacts" in row or contacts_count == 0 else "pending"
        )
        contacts_fetched_at = row.get("contacts_fetched_at") or (
            datetime.now(timezone.utc) if contacts_status == "fetched" else None
        )
        trade_status = row.get("trade_status") or (
            "fetched"
            if row.get("has_trade_data")
            or row.get("trade_amount_3y_usd") is not None
            or row.get("trade_count") is not None
            else "pending"
        )
        trade_fetched_at = row.get("trade_fetched_at") or (
            datetime.now(timezone.utc) if trade_status == "fetched" else None
        )

        result = await conn.execute(
            text(
                """
                INSERT INTO tendata_raw_companies
                  (keyword_master_id, source_id, collection_type, globiz_id, name, name_local,
                   country_iso3, website, tax_no,
                   industry_desc, employee_num, incorporation_date,
                   trade_amount_3y_usd, trade_count,
                   pcb_suppliers, product_tags, contacts_count, has_trade_data, aliases,
                   raw_payload, detail_status, detail_fetched_at, trade_status, trade_fetched_at,
                   contacts_status, contacts_fetched_at, enrichment_error)
                VALUES
                  (:keyword_master_id, :source_id, :collection_type, :globiz_id, :name, :name_local,
                   :country_iso3, :website, :tax_no,
                   :industry_desc, :employee_num, :incorporation_date,
                   :trade_amount_3y_usd, :trade_count,
                   CAST(:pcb_suppliers AS text[]), CAST(:product_tags AS text[]),
                   :contacts_count, :has_trade_data, CAST(:aliases AS text[]),
                   CAST(:raw_payload AS jsonb), :detail_status, :detail_fetched_at,
                   :trade_status, :trade_fetched_at, :contacts_status, :contacts_fetched_at,
                   CAST(:enrichment_error AS jsonb))
                ON CONFLICT (keyword_master_id, source_id, collection_type) DO UPDATE
                SET raw_payload = COALESCE(EXCLUDED.raw_payload, tendata_raw_companies.raw_payload),
                    globiz_id = COALESCE(EXCLUDED.globiz_id, tendata_raw_companies.globiz_id),
                    name = COALESCE(EXCLUDED.name, tendata_raw_companies.name),
                    name_local = COALESCE(EXCLUDED.name_local, tendata_raw_companies.name_local),
                    country_iso3 = COALESCE(EXCLUDED.country_iso3, tendata_raw_companies.country_iso3),
                    website = COALESCE(EXCLUDED.website, tendata_raw_companies.website),
                    tax_no = COALESCE(EXCLUDED.tax_no, tendata_raw_companies.tax_no),
                    industry_desc = COALESCE(EXCLUDED.industry_desc, tendata_raw_companies.industry_desc),
                    employee_num = COALESCE(EXCLUDED.employee_num, tendata_raw_companies.employee_num),
                    incorporation_date = COALESCE(EXCLUDED.incorporation_date, tendata_raw_companies.incorporation_date),
                    trade_amount_3y_usd = COALESCE(EXCLUDED.trade_amount_3y_usd, tendata_raw_companies.trade_amount_3y_usd),
                    trade_count = COALESCE(EXCLUDED.trade_count, tendata_raw_companies.trade_count),
                    pcb_suppliers = COALESCE(EXCLUDED.pcb_suppliers, tendata_raw_companies.pcb_suppliers),
                    product_tags = COALESCE(EXCLUDED.product_tags, tendata_raw_companies.product_tags),
                    contacts_count = COALESCE(EXCLUDED.contacts_count, tendata_raw_companies.contacts_count),
                    has_trade_data = COALESCE(EXCLUDED.has_trade_data, tendata_raw_companies.has_trade_data),
                    aliases = COALESCE(EXCLUDED.aliases, tendata_raw_companies.aliases),
                    detail_status = CASE
                      WHEN EXCLUDED.detail_status <> 'pending' THEN EXCLUDED.detail_status
                      ELSE tendata_raw_companies.detail_status
                    END,
                    detail_fetched_at = COALESCE(EXCLUDED.detail_fetched_at, tendata_raw_companies.detail_fetched_at),
                    trade_status = CASE
                      WHEN EXCLUDED.trade_status <> 'pending' THEN EXCLUDED.trade_status
                      ELSE tendata_raw_companies.trade_status
                    END,
                    trade_fetched_at = COALESCE(EXCLUDED.trade_fetched_at, tendata_raw_companies.trade_fetched_at),
                    contacts_status = CASE
                      WHEN EXCLUDED.contacts_status <> 'pending' THEN EXCLUDED.contacts_status
                      ELSE tendata_raw_companies.contacts_status
                    END,
                    contacts_fetched_at = COALESCE(EXCLUDED.contacts_fetched_at, tendata_raw_companies.contacts_fetched_at),
                    enrichment_error = COALESCE(EXCLUDED.enrichment_error, tendata_raw_companies.enrichment_error)
                RETURNING id
                """
            ),
            {
                "keyword_master_id": keyword_master_id,
                "source_id": source_id,
                "collection_type": collection_type,
                "globiz_id": row.get("globiz_id"),
                "name": row.get("name"),
                "name_local": row.get("name_local"),
                "country_iso3": to_iso3(row["country_iso3"]) if row.get("country_iso3") else None,
                "website": row.get("website"),
                "tax_no": row.get("tax_no"),
                "industry_desc": row.get("industry_desc"),
                "employee_num": row.get("employee_num"),
                "incorporation_date": row.get("incorporation_date"),
                "trade_amount_3y_usd": row.get("trade_amount_3y_usd"),
                "trade_count": row.get("trade_count"),
                "pcb_suppliers": _to_pg_array(row.get("pcb_suppliers")),
                "product_tags": _to_pg_array(row.get("product_tags")),
                "contacts_count": contacts_count,
                "has_trade_data": bool(row.get("has_trade_data", False)),
                "aliases": _to_pg_array(row.get("aliases")),
                "raw_payload": _json(_raw_payload_with_contacts(row)),
                "detail_status": row.get("detail_status", "pending"),
                "detail_fetched_at": row.get("detail_fetched_at"),
                "trade_status": trade_status,
                "trade_fetched_at": trade_fetched_at,
                "contacts_status": contacts_status,
                "contacts_fetched_at": contacts_fetched_at,
                "enrichment_error": _json(row.get("enrichment_error"))
                if row.get("enrichment_error") is not None
                else None,
            },
        )
        result_row = result.mappings().first()
        return str(result_row["id"])

    async def _upsert_lixiaoyun_raw(self, conn: AsyncConnection, row: dict) -> None:
        if not row.get("source_id"):
            return

        esdate = _parse_date(row.get("esdate"))
        keyword_master_id = row.get("keyword_master_id")
        if not keyword_master_id and row.get("task_id"):
            keyword_master_id = await self._keyword_master_id_for_task(conn, row["task_id"])

        await conn.execute(
            text(
                """
                INSERT INTO lixiaoyun_raw_companies
                  (keyword_master_id, source_id, name, english_name, domain, esdate, legalperson,
                   uncid, reg_capital, employee_scale, reg_address, raw_payload)
                VALUES
                  (:keyword_master_id, :source_id, :name, :english_name, :domain,
                   :esdate,
                   :legalperson,
                   :uncid, :reg_capital, :employee_scale, :reg_address, CAST(:raw_payload AS jsonb))
                ON CONFLICT (keyword_master_id, source_id) DO UPDATE
                SET raw_payload = EXCLUDED.raw_payload,
                    english_name = COALESCE(NULLIF(EXCLUDED.english_name,''), lixiaoyun_raw_companies.english_name),
                    esdate       = COALESCE(EXCLUDED.esdate, lixiaoyun_raw_companies.esdate),
                    domain       = COALESCE(NULLIF(EXCLUDED.domain,''), lixiaoyun_raw_companies.domain),
                    legalperson  = COALESCE(NULLIF(EXCLUDED.legalperson,''), lixiaoyun_raw_companies.legalperson),
                    uncid        = COALESCE(NULLIF(EXCLUDED.uncid,''), lixiaoyun_raw_companies.uncid),
                    reg_capital  = COALESCE(NULLIF(EXCLUDED.reg_capital,''), lixiaoyun_raw_companies.reg_capital),
                    employee_scale = COALESCE(NULLIF(EXCLUDED.employee_scale,''), lixiaoyun_raw_companies.employee_scale),
                    reg_address  = COALESCE(NULLIF(EXCLUDED.reg_address,''), lixiaoyun_raw_companies.reg_address)
                """
            ),
            {
                "keyword_master_id": keyword_master_id,
                "source_id": row.get("source_id"),
                "name": row.get("name"),
                "english_name": row.get("company_name_en") or row.get("english_name"),
                "domain": row.get("domain"),
                "esdate": esdate,
                "legalperson": row.get("legalperson"),
                "uncid": row.get("uncid"),
                "reg_capital": row.get("reg_capital"),
                "employee_scale": row.get("employee_scale"),
                "reg_address": row.get("reg_address"),
                "raw_payload": json.dumps(row.get("raw_payload") or {}),
            },
        )

    async def _upsert_waimaotong_detail(
        self, conn: AsyncConnection, *, raw_company_id: str, row: dict
    ) -> None:
        await conn.execute(
            text(
                """
                UPDATE waimaotong_raw_companies
                SET address = COALESCE(:address, address),
                    employee_size = COALESCE(:employee_size, employee_size),
                    founded_year = COALESCE(:founded_year, founded_year),
                    description = COALESCE(:description, description),
                    products = COALESCE(CAST(:products AS text[]), products),
                    detail_payload = COALESCE(CAST(:detail_payload AS jsonb), detail_payload),
                    detail_status = 'fetched',
                    detail_fetched_at = COALESCE(:detail_fetched_at, now()),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": int(raw_company_id),
                "address": row.get("address"),
                "employee_size": row.get("employee_size"),
                "founded_year": row.get("founded_year"),
                "description": row.get("description") or row.get("overview"),
                "products": _to_pg_array(_as_list(row.get("products"))),
                "detail_payload": _json(row.get("detail_payload") or row.get("raw_payload"))
                if (row.get("detail_payload") is not None or row.get("raw_payload") is not None)
                else None,
                "detail_fetched_at": row.get("detail_fetched_at"),
            },
        )

    async def _upsert_waimaotong_trade(
        self, conn: AsyncConnection, *, raw_company_id: str, row: dict
    ) -> None:
        await conn.execute(
            text(
                """
                UPDATE waimaotong_raw_companies
                SET trade_amount_3y_usd = COALESCE(:trade_amount_3y_usd, trade_amount_3y_usd),
                    trade_count = COALESCE(:trade_count, trade_count),
                    contacts_count = COALESCE(:contacts_count, contacts_count),
                    has_trade_data = COALESCE(:has_trade_data, has_trade_data),
                    customs_data = COALESCE(CAST(:customs_data AS jsonb), customs_data),
                    trade_payload = COALESCE(CAST(:trade_payload AS jsonb), trade_payload),
                    trade_status = 'fetched',
                    trade_fetched_at = COALESCE(:trade_fetched_at, now()),
                    updated_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": int(raw_company_id),
                "trade_amount_3y_usd": row.get("trade_amount_3y_usd"),
                "trade_count": row.get("trade_count"),
                "contacts_count": row.get("contacts_count"),
                "has_trade_data": row.get("has_trade_data"),
                "customs_data": _json(row.get("customs_data"))
                if row.get("customs_data") is not None
                else None,
                "trade_payload": _json(row.get("trade_payload") or row.get("raw_payload"))
                if (row.get("trade_payload") is not None or row.get("raw_payload") is not None)
                else None,
                "trade_fetched_at": row.get("trade_fetched_at"),
            },
        )

    async def mark_waimaotong_enrichment_failed(
        self, conn: AsyncConnection, *, raw_company_id: str, stage: str, error: dict | str
    ) -> None:
        await self._mark_enrichment_status(
            conn,
            "waimaotong_raw_companies",
            raw_company_id,
            stage,
            "failed",
            error=error,
        )

    async def mark_tendata_enrichment_failed(
        self, conn: AsyncConnection, *, raw_company_id: str, stage: str, error: dict | str
    ) -> None:
        await self._mark_enrichment_status(
            conn,
            "tendata_raw_companies",
            raw_company_id,
            stage,
            "failed",
            error=error,
        )

    async def _mark_enrichment_status(
        self,
        conn: AsyncConnection,
        table: str,
        raw_company_id: str,
        stage: str,
        status: str,
        *,
        error: dict | str | None = None,
    ) -> None:
        if stage not in _ENRICHMENT_STAGES:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"未知 enrichment stage: {stage}",
                status_code=422,
            )
        if status not in {"pending", "fetched", "failed", "skipped"}:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"未知 enrichment status: {status}",
                status_code=422,
            )
        status_column, fetched_at_column = _ENRICHMENT_STAGES[stage]
        fetched_sql = (
            f"{fetched_at_column} = COALESCE({fetched_at_column}, now()),"
            if status == "fetched"
            else ""
        )
        error_payload = None
        if error is not None:
            error_payload = (
                {"stage": stage, "error": error}
                if not isinstance(error, dict)
                else {"stage": stage, **error}
            )
        await conn.execute(
            text(
                f"""
                UPDATE {table}
                SET {status_column} = :status,
                    {fetched_sql}
                    enrichment_error = COALESCE(CAST(:enrichment_error AS jsonb), enrichment_error)
                WHERE id = :id
                """
            ),
            {
                "id": int(raw_company_id),
                "status": status,
                "enrichment_error": _json(error_payload) if error_payload is not None else None,
            },
        )

    async def _keyword_master_id_for_task(self, conn: AsyncConnection, task_id: str) -> str | None:
        result = await conn.execute(
            text(
                """
                SELECT cr.keyword_master_id
                FROM collection_tasks ct
                JOIN collection_runs cr ON cr.id = ct.run_id
                WHERE ct.id = :task_id
                  AND cr.keyword_master_id IS NOT NULL
                UNION ALL
                SELECT ck.keyword_master_id
                FROM collection_task_keywords ctk
                JOIN collection_keywords ck ON ck.id = ctk.keyword_id
                WHERE ctk.task_id = :task_id
                  AND ck.keyword_master_id IS NOT NULL
                ORDER BY 1
                LIMIT 1
                """
            ),
            {"task_id": task_id},
        )
        value = result.scalar()
        return str(value) if value else None

    async def _enqueue_cleanup(
        self, conn: AsyncConnection, raw_table: str, raw_row_id: str
    ) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO cleanup_queue (raw_table, raw_row_id, status)
                VALUES (:raw_table, :raw_row_id, 'pending')
                ON CONFLICT (raw_table, raw_row_id) DO NOTHING
                """
            ),
            {"raw_table": raw_table, "raw_row_id": raw_row_id},
        )

    async def _route_and_enqueue(
        self, conn: AsyncConnection, task_id: str, rows: list[dict]
    ) -> dict:
        inserted = 0
        enqueued = 0
        for row in rows:
            target_table = row.get("target_table")
            if target_table == "waimaotong_raw_companies":
                raw_row_id = await self._upsert_waimaotong_raw(conn, task_id, row)
                if raw_row_id:
                    await self._enqueue_cleanup(conn, target_table, int(raw_row_id))
                    inserted += 1
                    enqueued += 1
            elif target_table == "tendata_raw_companies":
                raw_row_id = await self._upsert_tendata_raw(conn, task_id, row)
                if raw_row_id:
                    await self._enqueue_cleanup(conn, target_table, int(raw_row_id))
                    inserted += 1
                    enqueued += 1
            elif target_table == "lixiaoyun_raw_companies":
                if not row.get("source_id"):
                    continue
                await self._upsert_lixiaoyun_raw(conn, {**row, "task_id": task_id})
                inserted += 1
            elif target_table == "waimaotong_raw_contacts":
                await self._upsert_waimaotong_raw_contact(conn, task_id, row)
                inserted += 1
            else:
                logger.warning("unknown target_table: %s", target_table)
        return {"inserted": inserted, "updated": 0, "enqueued": enqueued}

    async def recover_expired_tasks(self, conn: AsyncConnection) -> dict:
        expired_result = await conn.execute(
            text(
                """
                SELECT id, attempt_count, max_attempts
                FROM collection_tasks
                WHERE status = 'running'
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= now()
                FOR UPDATE SKIP LOCKED
                """
            )
        )
        recovered = 0
        failed = 0
        for row in expired_result.mappings().all():
            if row["attempt_count"] >= row["max_attempts"]:
                await conn.execute(
                    text(
                        """
                        UPDATE collection_tasks
                        SET status = 'failed',
                            lease_id = NULL,
                            lease_owner = NULL,
                            lease_expires_at = NULL,
                            error_message = :error_message,
                            completed_at = COALESCE(completed_at, now()),
                            updated_at = now()
                        WHERE id = :task_id
                        """
                    ),
                    {
                        "task_id": row["id"],
                        "error_message": "collection task lease expired after max attempts",
                    },
                )
                failed += 1
                continue

            await conn.execute(
                text(
                    """
                    UPDATE collection_tasks
                    SET status = 'pending',
                        lease_id = NULL,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        error_message = :error_message,
                        updated_at = now()
                    WHERE id = :task_id
                    """
                ),
                {
                    "task_id": row["id"],
                    "error_message": "collection task lease expired and was requeued",
                },
            )
            recovered += 1

        return {
            "expired_count": recovered + failed,
            "requeued_count": recovered,
            "failed_count": failed,
        }

    async def claim_tasks(
        self,
        conn: AsyncConnection,
        *,
        service_instance: str,
        limit: int,
        lease_seconds: int,
    ) -> dict:
        recovery = await self.recover_expired_tasks(conn)
        lease_id = str(new_uuid())
        lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
        result = await conn.execute(
            text(
                """
                WITH candidate AS (
                  SELECT id
                  FROM collection_tasks
                  WHERE status = 'pending'
                    AND COALESCE(scheduled_at, created_at, now()) <= now()
                    AND (
                      (
                        run_id IS NOT NULL
                        AND EXISTS (
                          SELECT 1
                          FROM collection_runs cr
                          WHERE cr.id = collection_tasks.run_id
                            AND cr.status IN ('running', 'daily_limit_reached')
                        )
                      )
                      OR (
                        run_id IS NULL
                        AND NOT EXISTS (
                          SELECT 1
                          FROM collection_task_keywords ctk_any
                          WHERE ctk_any.task_id = collection_tasks.id
                        )
                      )
                      OR (
                        run_id IS NULL
                        AND EXISTS (
                        SELECT 1
                        FROM collection_task_keywords ctk
                        JOIN collection_keywords ck ON ck.id = ctk.keyword_id
                        WHERE ctk.task_id = collection_tasks.id
                          AND ck.status = 'active'
                          AND ck.subscription_status = 'running'
                        )
                      )
                    )
                  ORDER BY priority DESC, COALESCE(scheduled_at, created_at, now()) ASC
                  LIMIT :limit
                  FOR UPDATE SKIP LOCKED
                )
                UPDATE collection_tasks t
                SET status = 'running',
                    lease_id = :lease_id,
                    lease_owner = :lease_owner,
                    lease_expires_at = :lease_expires_at,
                    attempt_count = attempt_count + 1,
                    started_at = COALESCE(started_at, now()),
                    updated_at = now()
                FROM candidate
                WHERE t.id = candidate.id
                RETURNING t.id, t.run_id, t.keyword, t.countries, t.source_types,
                          t.task_type, t.context, t.page_size, t.cursor_snapshot,
                          (
                            SELECT cr.cursor
                            FROM collection_runs cr
                            WHERE cr.id = t.run_id
                          ) AS run_cursor,
                          (
                            SELECT cr.skip_source_ids
                            FROM collection_runs cr
                            WHERE cr.id = t.run_id
                          ) AS run_skip_source_ids
                """
            ),
            {
                "limit": limit,
                "lease_id": lease_id,
                "lease_owner": service_instance,
                "lease_expires_at": lease_expires_at,
            },
        )
        tasks = [
            {
                "id": str(row["id"]),
                "run_id": str(row["run_id"]) if row["run_id"] else None,
                "keyword": row["keyword"],
                "countries": row["countries"],
                "source_types": row["source_types"],
                "task_type": row["task_type"],
                "context": self._context_with_task_defaults(row),
            }
            for row in result.mappings().all()
        ]
        return {"lease_id": lease_id, "tasks": tasks, "recovery": recovery}

    async def heartbeat(
        self,
        conn: AsyncConnection,
        *,
        task_id: str,
        lease_id: str,
        lease_seconds: int,
    ) -> dict:
        lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
        result = await conn.execute(
            text(
                """
                UPDATE collection_tasks
                SET lease_expires_at = :lease_expires_at,
                    updated_at = now()
                WHERE id = :task_id
                  AND status = 'running'
                  AND lease_id = :lease_id
                  AND lease_expires_at > now()
                RETURNING id, lease_expires_at
                """
            ),
            {
                "task_id": task_id,
                "lease_id": lease_id,
                "lease_expires_at": lease_expires_at,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="LEASE_INVALID", message="lease 无效或已过期", status_code=409)
        return {"task_id": str(row["id"]), "lease_expires_at": row["lease_expires_at"].isoformat()}

    async def submit_result(
        self,
        conn: AsyncConnection,
        *,
        task_id: str,
        lease_id: str,
        companies: list[dict],
        contacts: list[dict],
        competitors: list[dict],
        cursor: dict | None = None,
        skip_source_ids: list[str] | None = None,
        request_id: str,
        service_name: str,
    ) -> dict:
        endpoint = f"collection.submit_result.{task_id}"
        existing = await self.idempotency.load(
            conn,
            service_name=service_name,
            request_id=request_id,
            endpoint=endpoint,
        )
        if existing is not None:
            return existing

        task = await self._load_task_for_update(conn, task_id)
        self._assert_task_lease(task, lease_id)

        all_rows = list(companies) + list(contacts) + list(competitors)
        route_summary = await self._route_and_enqueue(conn, task_id=task_id, rows=all_rows)

        tenant_keyword_map = await self._get_tenant_keyword_map(conn, task_id)
        total_rows_count = len(companies) + len(competitors)
        no_more_data = total_rows_count == 0
        await self._update_run_after_success(
            conn,
            task=task,
            task_id=task_id,
            result_count=total_rows_count,
            no_more_data=no_more_data,
            cursor=cursor,
            skip_source_ids=skip_source_ids,
        )

        summary = {
            "companies_count": len(companies),
            "contacts_count": len(contacts),
            "competitors_count": len(competitors),
            "tenant_count": len(tenant_keyword_map),
            "route_summary": route_summary,
            "reason": "no_more_data" if no_more_data else "batch_completed",
        }
        await conn.execute(
            text(
                """
                UPDATE collection_tasks
                SET status = 'completed',
                    result_summary = CAST(:result_summary AS jsonb),
                    completed_at = now(),
                    lease_id = NULL,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    error_message = NULL,
                    updated_at = now()
                WHERE id = :task_id
                """
            ),
            {
                "task_id": task_id,
                "result_summary": json.dumps(summary, ensure_ascii=False),
            },
        )

        # After a competitor_search task completes with new competitors,
        # automatically create a buyer_lookup task so Tendata can reverse-lookup
        # overseas importers for those Chinese manufacturers.
        buyer_task_id: str | None = None
        if _AUTO_CREATE_TENDATA_STAGE2 and task["task_type"] == "competitor_search" and competitors:
            competitor_names = [
                r.get("company_name_en") or ""
                for r in competitors
                if r.get("target_table") == "lixiaoyun_raw_companies" and r.get("company_name_en")
            ]
            if competitor_names:
                buyer_task_id = await self._create_buyer_lookup_task(
                    conn,
                    source_task=task,
                    competitor_names=competitor_names,
                    tenant_keyword_map=tenant_keyword_map,
                )
        summary["buyer_lookup_task_id"] = buyer_task_id

        response = {"task_id": task_id, "summary": summary}
        await self.idempotency.save(
            conn,
            service_name=service_name,
            request_id=request_id,
            endpoint=endpoint,
            response_body=response,
        )
        return response

    async def mark_failed(
        self,
        conn: AsyncConnection,
        *,
        task_id: str,
        lease_id: str,
        error_message: str,
        retryable: bool = True,
        error_code: str | None = None,
    ) -> dict:
        task = await self._load_task_for_update(conn, task_id)
        self._assert_task_lease(task, lease_id)
        full_error = error_message if not error_code else f"[{error_code}] {error_message}"

        if retryable and task["attempt_count"] < task["max_attempts"]:
            await conn.execute(
                text(
                    """
                    UPDATE collection_tasks
                    SET status = 'pending',
                        lease_id = NULL,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        error_message = :error_message,
                        updated_at = now()
                    WHERE id = :task_id
                    """
                ),
                {"task_id": task_id, "error_message": full_error},
            )
            return {
                "task_id": task_id,
                "status": "pending",
                "retryable": True,
                "reason": full_error,
            }

        await conn.execute(
            text(
                """
                UPDATE collection_tasks
                SET status = 'failed',
                    lease_id = NULL,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    error_message = :error_message,
                    completed_at = COALESCE(completed_at, now()),
                    updated_at = now()
                WHERE id = :task_id
                """
            ),
            {"task_id": task_id, "error_message": full_error},
        )
        return {
            "task_id": task_id,
            "status": "failed",
            "retryable": False,
            "reason": full_error,
        }

    async def _create_buyer_lookup_task(
        self,
        conn: AsyncConnection,
        *,
        source_task,
        competitor_names: list[str],
        tenant_keyword_map: dict[str, str],
    ) -> str:
        """Create a buyer_lookup task that feeds competitor names to Tendata."""
        import hashlib

        buyer_task_id = str(new_uuid())
        context = {"competitor_names": competitor_names}

        # Reuse same keyword / countries so we can track lineage
        keyword = source_task["keyword"]
        keyword_normalized = source_task.get("keyword_normalized") or keyword.lower()
        countries = source_task.get("countries") or []
        countries_list = list(countries) if countries else []
        countries_hash = hashlib.sha256(
            ",".join(sorted(countries_list)).encode("utf-8")
        ).hexdigest()

        await conn.execute(
            text(
                """
                INSERT INTO collection_tasks
                  (id, keyword, keyword_normalized, countries, countries_hash,
                   source_types, task_type, context, status, priority, scheduled_at)
                VALUES
                  (:id, :keyword, :keyword_normalized, CAST(:countries AS jsonb), :countries_hash,
                   CAST(:source_types AS jsonb), 'buyer_lookup', CAST(:context AS jsonb),
                   'pending', :priority, now())
                """
            ),
            {
                "id": buyer_task_id,
                "keyword": keyword,
                "keyword_normalized": keyword_normalized,
                "countries": json.dumps(countries_list, ensure_ascii=False),
                "countries_hash": countries_hash,
                "source_types": json.dumps(["tengdao"], ensure_ascii=False),
                "context": json.dumps(context, ensure_ascii=False),
                "priority": 5,  # lower priority than competitor_search
            },
        )

        # Link the same tenant-keyword pairs so results get attributed correctly
        for tenant_id, keyword_id in tenant_keyword_map.items():
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                    VALUES (:id, :task_id, :keyword_id, :tenant_id)
                    ON CONFLICT (task_id, keyword_id) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "task_id": buyer_task_id,
                    "keyword_id": keyword_id,
                    "tenant_id": tenant_id,
                },
            )

        return buyer_task_id

    async def get_tenant_keyword_map(self, conn: AsyncConnection, task_id: str) -> dict[str, str]:
        return await self._get_tenant_keyword_map(conn, task_id)

    async def save_competitors_partial(
        self,
        conn: AsyncConnection,
        *,
        task_id: str,
        competitors: list[dict],
    ) -> None:
        """Phase-1 save: persist basic search results before detail enrichment starts."""
        for competitor in competitors:
            if competitor.get("target_table") == "lixiaoyun_raw_companies":
                await self._upsert_lixiaoyun_raw(conn, {**competitor, "task_id": task_id})
            else:
                tenant_keyword_map = await self._get_tenant_keyword_map(conn, task_id)
                for tenant_id in tenant_keyword_map:
                    await self._upsert_competitor(conn, tenant_id, competitor)

    async def save_competitor_enriched(
        self,
        conn: AsyncConnection,
        *,
        task_id: str,
        competitor: dict,
    ) -> None:
        """Phase-2/3 save: update one company's detail fields and save its contacts.
        Called immediately after each company's detail + contacts are fetched."""
        if competitor.get("target_table") == "lixiaoyun_raw_companies":
            await self._upsert_lixiaoyun_raw(conn, {**competitor, "task_id": task_id})
        else:
            tenant_keyword_map = await self._get_tenant_keyword_map(conn, task_id)
            for tenant_id in tenant_keyword_map:
                competitor_id = await self._upsert_competitor(conn, tenant_id, competitor)
                contacts = competitor.get("raw_data", {}).get("lx_contacts") or []
                if contacts:
                    await self._save_competitor_contacts(conn, competitor_id, tenant_id, contacts)

    async def _get_tenant_keyword_map(self, conn: AsyncConnection, task_id: str) -> dict[str, str]:
        run_meta = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT cr.keyword_master_id
                    FROM collection_tasks ct
                    JOIN collection_runs cr ON cr.id = ct.run_id
                    WHERE ct.id = :task_id
                    """
                    ),
                    {"task_id": task_id},
                )
            )
            .mappings()
            .first()
        )

        if run_meta and run_meta["keyword_master_id"]:
            run_result = await conn.execute(
                text(
                    """
                    SELECT tk.tenant_id, tk.id AS keyword_id
                    FROM tenant_keyword tk
                    WHERE tk.keyword_master_id = :keyword_master_id
                      AND tk.status = 'active'
                    ORDER BY tk.created_at ASC
                    """
                ),
                {"keyword_master_id": run_meta["keyword_master_id"]},
            )
            run_tenant_keyword_map: dict[str, str] = {}
            for row in run_result.mappings().all():
                run_tenant_keyword_map.setdefault(str(row["tenant_id"]), str(row["keyword_id"]))
            if run_tenant_keyword_map:
                return run_tenant_keyword_map

        result = await conn.execute(
            text(
                """
                SELECT tenant_id, keyword_id
                FROM collection_task_keywords
                WHERE task_id = :task_id
                ORDER BY created_at ASC
                """
            ),
            {"task_id": task_id},
        )
        tenant_keyword_map: dict[str, str] = {}
        for row in result.mappings().all():
            tenant_keyword_map.setdefault(str(row["tenant_id"]), str(row["keyword_id"]))
        return tenant_keyword_map

    async def _upsert_competitor(
        self, conn: AsyncConnection, tenant_id: str, competitor: dict
    ) -> str:
        raw = competitor.get("raw_data") or {}
        result = await conn.execute(
            text(
                """
                INSERT INTO competitor_companies
                  (id, tenant_id, company_name, company_name_en, source_id, domain, reason,
                   source_type, esdate, legalperson, reg_capital, paid_capital, reg_address,
                   contact_address, employee_scale, uncid, raw_data)
                VALUES
                  (:id, :tenant_id, :company_name, :company_name_en, :source_id, :domain, :reason,
                   :source_type, :esdate, :legalperson, :reg_capital, :paid_capital, :reg_address,
                   :contact_address, :employee_scale, :uncid, CAST(:raw_data AS jsonb))
                ON CONFLICT (tenant_id, company_name) DO UPDATE
                SET company_name_en  = COALESCE(excluded.company_name_en, competitor_companies.company_name_en),
                    source_id        = COALESCE(excluded.source_id, competitor_companies.source_id),
                    domain           = COALESCE(excluded.domain, competitor_companies.domain),
                    reason           = COALESCE(excluded.reason, competitor_companies.reason),
                    esdate           = COALESCE(excluded.esdate, competitor_companies.esdate),
                    legalperson      = COALESCE(excluded.legalperson, competitor_companies.legalperson),
                    reg_capital      = COALESCE(excluded.reg_capital, competitor_companies.reg_capital),
                    paid_capital     = COALESCE(excluded.paid_capital, competitor_companies.paid_capital),
                    reg_address      = COALESCE(excluded.reg_address, competitor_companies.reg_address),
                    contact_address  = COALESCE(excluded.contact_address, competitor_companies.contact_address),
                    employee_scale   = COALESCE(excluded.employee_scale, competitor_companies.employee_scale),
                    uncid            = COALESCE(excluded.uncid, competitor_companies.uncid),
                    raw_data         = excluded.raw_data,
                    updated_at       = now()
                RETURNING id
                """
            ),
            {
                "id": str(new_uuid()),
                "tenant_id": tenant_id,
                "company_name": competitor["company_name"],
                "company_name_en": competitor.get("company_name_en"),
                "source_id": competitor.get("source_id"),
                "domain": competitor.get("domain"),
                "reason": competitor.get("reason"),
                "source_type": competitor.get("source_type", "lixiaoyun"),
                "esdate": _parse_date(raw.get("esdate")),
                "legalperson": raw.get("legalperson"),
                "reg_capital": raw.get("reg_capital"),
                "paid_capital": raw.get("paid_capital"),
                "reg_address": raw.get("reg_address"),
                "contact_address": raw.get("contact_address"),
                "employee_scale": raw.get("employee_scale"),
                "uncid": raw.get("uncid"),
                "raw_data": json.dumps(raw, ensure_ascii=False),
            },
        )
        row = result.mappings().first()
        return str(row["id"])

    async def _save_competitor_contacts(
        self,
        conn: AsyncConnection,
        competitor_id: str,
        tenant_id: str,
        contacts: list[dict],
    ) -> None:
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            await conn.execute(
                text(
                    """
                    INSERT INTO competitor_contacts
                      (id, competitor_id, tenant_id, name, phone, position, email, raw_data)
                    VALUES
                      (:id, :competitor_id, :tenant_id, :name, :phone, :position, :email,
                       CAST(:raw_data AS jsonb))
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "competitor_id": competitor_id,
                    "tenant_id": tenant_id,
                    "name": contact.get("name"),
                    "phone": contact.get("phone"),
                    "position": contact.get("position"),
                    "email": contact.get("email"),
                    "raw_data": json.dumps(contact, ensure_ascii=False),
                },
            )

    async def _notify_credential_expired(
        self, conn: AsyncConnection, *, task_id: str, task
    ) -> None:
        source_types = list(task.get("source_types") or [])
        source_label = (
            "、".join({"lixiaoyun": "励销云", "tengdao": "腾道"}.get(s, s) for s in source_types)
            or "采集数据源"
        )

        result = await conn.execute(
            text(
                """
                SELECT DISTINCT u.id AS user_id, u.tenant_id
                FROM users u
                JOIN user_roles ur ON ur.user_id = u.id AND ur.tenant_id = u.tenant_id
                JOIN collection_task_keywords ctk ON ctk.tenant_id = u.tenant_id
                WHERE ctk.task_id = :task_id
                  AND ur.role = 'admin'
                  AND u.status = 'active'
                """
            ),
            {"task_id": task_id},
        )
        for row in result.mappings().all():
            await conn.execute(
                text(
                    """
                    INSERT INTO notifications
                      (id, tenant_id, user_id, title, content, category, entity_type, entity_id, is_read)
                    VALUES
                      (:id, :tenant_id, :user_id, :title, :content, 'collection', 'collection_task', :entity_id, false)
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "tenant_id": str(row["tenant_id"]),
                    "user_id": str(row["user_id"]),
                    "title": f"{source_label}凭证已过期",
                    "content": f"{source_label}的登录凭证已过期，采集任务已停止。请前往「管理后台 → 数据源配置」重新登录并更新凭证。",
                    "entity_id": task_id,
                },
            )

    async def _load_task_for_update(self, conn: AsyncConnection, task_id: str):
        result = await conn.execute(
            text(
                """
                SELECT id, status, lease_id, lease_owner, lease_expires_at,
                       attempt_count, max_attempts, task_type, keyword,
                       keyword_normalized, countries, context, run_id
                FROM collection_tasks
                WHERE id = :task_id
                FOR UPDATE
                """
            ),
            {"task_id": task_id},
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="collection task 不存在", status_code=404)
        return row

    def _context_with_task_defaults(self, row) -> dict:
        context = dict(row["context"] or {})
        params = dict(context.get("params") or context)
        if row.get("page_size"):
            params.setdefault("page_size", int(row["page_size"]))
            params.setdefault("max_competitors", int(row["page_size"]))
        if row.get("cursor_snapshot"):
            cursor_snapshot = row["cursor_snapshot"] or {}
            if cursor_snapshot:
                params.setdefault("cursor", cursor_snapshot)
        if row.get("run_cursor"):
            run_cursor = row["run_cursor"] or {}
            if run_cursor:
                params.setdefault("cursor", run_cursor)
        if row.get("run_skip_source_ids"):
            run_skip_source_ids = row["run_skip_source_ids"] or []
            if run_skip_source_ids:
                params.setdefault("skip_source_ids", list(run_skip_source_ids))
        context["params"] = params
        return context

    async def _update_run_after_success(
        self,
        conn: AsyncConnection,
        *,
        task,
        task_id: str,
        result_count: int,
        no_more_data: bool,
        cursor: dict | None = None,
        skip_source_ids: list[str] | None = None,
    ) -> None:
        run_id = task.get("run_id")
        if not run_id:
            return
        cursor_sql = ""
        cursor_params = {}
        if cursor is not None:
            cursor_sql += ", cursor = CAST(:cursor AS jsonb)"
            cursor_params["cursor"] = json.dumps(cursor, ensure_ascii=False)
        if skip_source_ids is not None:
            cursor_sql += ", skip_source_ids = CAST(:skip_source_ids AS jsonb)"
            cursor_params["skip_source_ids"] = json.dumps(skip_source_ids, ensure_ascii=False)
        if no_more_data:
            await conn.execute(
                text(
                    f"""
                    UPDATE collection_runs
                    SET status = 'completed',
                        completed_at = now(),
                        total_fetched = total_fetched + :result_count,
                        today_fetched = today_fetched + :result_count,
                        updated_at = now()
                        {cursor_sql}
                    WHERE id = :run_id
                    """
                ),
                {"run_id": run_id, "result_count": result_count, **cursor_params},
            )
            return

        run_row = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT km.keyword, km.keyword_normalized, cr.daily_limit,
                           cr.request_page_size, cr.today_fetched, cr.cursor,
                           cr.skip_source_ids
                    FROM collection_runs cr
                    JOIN keyword_master km ON km.id = cr.keyword_master_id
                    WHERE cr.id = :run_id
                    FOR UPDATE
                    """
                    ),
                    {"run_id": run_id},
                )
            )
            .mappings()
            .first()
        )
        if run_row is None:
            return

        next_today_fetched = int(run_row["today_fetched"] or 0) + result_count
        daily_limit = int(run_row["daily_limit"] or 1000)
        if next_today_fetched >= daily_limit:
            next_run_at = self._next_beijing_8am()
            await conn.execute(
                text(
                    f"""
                    UPDATE collection_runs
                    SET status = 'daily_limit_reached',
                        total_fetched = total_fetched + :result_count,
                        today_fetched = :today_fetched,
                        next_run_at = :next_run_at,
                        updated_at = now()
                        {cursor_sql}
                    WHERE id = :run_id
                    """
                ),
                {
                    "run_id": run_id,
                    "result_count": result_count,
                    "today_fetched": next_today_fetched,
                    "next_run_at": next_run_at,
                    **cursor_params,
                },
            )
            await self._ensure_continuation_task(
                conn,
                run_id=int(run_id),
                keyword=run_row["keyword"],
                keyword_normalized=run_row["keyword_normalized"],
                next_run_at=next_run_at,
                page_size=int(run_row["request_page_size"] or _DEFAULT_LIXIAOYUN_PAGE_SIZE),
                cursor=cursor if cursor is not None else (run_row["cursor"] or {}),
                skip_source_ids=(
                    skip_source_ids
                    if skip_source_ids is not None
                    else list(run_row["skip_source_ids"] or [])
                ),
                current_task_id=task_id,
            )
            return

        await conn.execute(
            text(
                f"""
                UPDATE collection_runs
                SET status = 'running',
                    total_fetched = total_fetched + :result_count,
                    today_fetched = today_fetched + :result_count,
                    updated_at = now()
                    {cursor_sql}
                WHERE id = :run_id
                """
            ),
            {"run_id": run_id, "result_count": result_count, **cursor_params},
        )

    def _next_beijing_8am(self) -> datetime:
        now = datetime.now(_BEIJING_TZ)
        tomorrow = now.date() + timedelta(days=1)
        return datetime(
            tomorrow.year,
            tomorrow.month,
            tomorrow.day,
            8,
            0,
            0,
            tzinfo=_BEIJING_TZ,
        )

    async def _ensure_continuation_task(
        self,
        conn: AsyncConnection,
        *,
        run_id: str,
        keyword: str,
        keyword_normalized: str,
        next_run_at: datetime,
        page_size: int,
        cursor: dict,
        skip_source_ids: list[str],
        current_task_id: str,
    ) -> None:
        existing = await conn.execute(
            text(
                """
                SELECT id
                FROM collection_tasks
                WHERE run_id = :run_id
                  AND id <> :current_task_id
                  AND status IN ('pending', 'running')
                LIMIT 1
                """
            ),
            {"run_id": run_id, "current_task_id": current_task_id},
        )
        if existing.first() is not None:
            return

        task_id = str(new_uuid())
        bounded_page_size = max(1, min(page_size, _MAX_LIXIAOYUN_PAGE_SIZE))
        context = {
            "params": {
                "max_competitors": bounded_page_size,
                "page_size": bounded_page_size,
                "skip_source_ids": skip_source_ids,
                "cursor": cursor,
            }
        }
        await conn.execute(
            text(
                """
                INSERT INTO collection_tasks
                  (id, run_id, keyword, keyword_normalized, countries, countries_hash,
                   source_types, task_type, context, status, priority, scheduled_at,
                   scheduled_biz_date, batch_no, page_size, cursor_snapshot)
                VALUES
                  (:id, :run_id, :keyword, :keyword_normalized, '[]'::jsonb, '',
                   '["lixiaoyun"]'::jsonb, 'competitor_search',
                   CAST(:context AS jsonb), 'pending', 10, :scheduled_at,
                   (:scheduled_at AT TIME ZONE 'Asia/Shanghai')::date,
                   COALESCE((
                     SELECT MAX(batch_no) + 1
                     FROM collection_tasks
                     WHERE run_id = :run_id
                   ), 1),
                   :page_size, CAST(:cursor AS jsonb))
                """
            ),
            {
                "id": task_id,
                "run_id": run_id,
                "keyword": keyword,
                "keyword_normalized": keyword_normalized,
                "context": json.dumps(context, ensure_ascii=False),
                "scheduled_at": next_run_at,
                "page_size": bounded_page_size,
                "cursor": json.dumps(cursor, ensure_ascii=False),
            },
        )
        links = await conn.execute(
            text(
                """
                SELECT DISTINCT ctk.keyword_id, ctk.tenant_id
                FROM collection_task_keywords ctk
                JOIN collection_tasks ct ON ct.id = ctk.task_id
                WHERE ct.run_id = :run_id
                """
            ),
            {"run_id": run_id},
        )
        for link in links.mappings().all():
            await conn.execute(
                text(
                    """
                    INSERT INTO collection_task_keywords (id, task_id, keyword_id, tenant_id)
                    VALUES (:id, :task_id, :keyword_id, :tenant_id)
                    ON CONFLICT (task_id, keyword_id) DO NOTHING
                    """
                ),
                {
                    "id": str(new_uuid()),
                    "task_id": task_id,
                    "keyword_id": link["keyword_id"],
                    "tenant_id": link["tenant_id"],
                },
            )

    def _assert_task_lease(self, task, lease_id: str) -> None:
        current_lease_id = str(task["lease_id"]) if task["lease_id"] is not None else None
        if (
            task["status"] != "running"
            or current_lease_id != lease_id
            or task["lease_expires_at"] is None
            or task["lease_expires_at"] <= datetime.now(timezone.utc)
        ):
            raise AppError(code="LEASE_INVALID", message="lease 无效或已过期", status_code=409)
