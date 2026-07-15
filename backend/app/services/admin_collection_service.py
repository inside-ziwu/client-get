import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.errors import AppError
from app.services.collection_source import build_collection_type_filter, compute_collection_type

_BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def _reg_cap_case(col: str) -> str:
    return f"""
CASE
  WHEN {col} ~ E'^[0-9.]+(亿|亿元)' THEN (substring({col}, E'^([0-9.]+)'))::numeric * 10000
  WHEN {col} ~ E'^[0-9.]+(万|万元)' THEN (substring({col}, E'^([0-9.]+)'))::numeric
  ELSE NULL
END"""


REG_CAP_RANGE = {
    "lt100": "< 100",
    "100_500": "BETWEEN 100 AND 499.999",
    "500_2000": "BETWEEN 500 AND 1999.999",
    "2000_1e": "BETWEEN 2000 AND 9999.999",
    "gt1e": ">= 10000",
}


def _employee_scale_case(col: str) -> str:
    return f"""
CASE
  WHEN {col} ~ E'^([0-9]+)人以下' THEN 1
  WHEN {col} ~ E'^([0-9]+)[-–]([0-9]+)' THEN (substring({col}, E'^([0-9]+)'))::int
  WHEN {col} ~ E'^([0-9]+)人以上' THEN (substring({col}, E'^([0-9]+)'))::int
  ELSE NULL
END"""


EMPLOYEE_SCALE_RANGE = {
    "lt10": "< 10",
    "10_50": "BETWEEN 10 AND 49",
    "50_200": "BETWEEN 50 AND 199",
    "200_1000": "BETWEEN 200 AND 999",
    "gt1000": ">= 1000",
}


def _parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _keyword_like(value: str) -> str:
    normalized = re.sub(r"[\s._]+", "", value.strip().lower())
    return f"%{normalized}%"


class AdminCollectionService:
    async def list_raw_companies(
        self,
        conn,
        *,
        table: str,
        page: int = 1,
        page_size: int = 20,
        include_payload: bool = False,
        keyword: str | None = None,
        country: str | None = None,
        # ── lixiaoyun 专用 ──
        keyword_filter: str | None = None,
        found_date_start: str | None = None,
        found_date_end: str | None = None,
        reg_capital: str | None = None,
        employee_scale: str | None = None,
        contacts_filter: str | None = None,
        has_name_en: bool | None = None,
        has_domain: bool | None = None,
        # ── tendata 专用 ──
        industry: str | None = None,
        tag: str | None = None,
        size: str | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        count_min: int | None = None,
        count_max: int | None = None,
        pcb: str | None = None,
        contact_min: int | None = None,
        contact_max: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        method: str | None = None,
    ) -> tuple[list[dict], int]:
        payload_select = ", raw_payload" if include_payload else ""
        table_sql = {
            "waimaotong": """
                SELECT id::text AS id, NULL::text AS source_id,
                       COALESCE(company_name, name) AS name, country,
                       domain, NULL::text AS task_id, created_at
                       {payload_select_null}
                FROM waimaotong_raw_companies
            """.format(payload_select_null=", NULL::jsonb AS raw_payload" if include_payload else ""),
            "tendata": """
                SELECT id::text AS id, source_id, name, country_iso3 AS country,
                       website AS domain, NULL::text AS task_id, created_at
                       {payload_select}
                FROM tendata_raw_companies
            """.format(payload_select=payload_select),
            "lixiaoyun": """
                SELECT id::text AS id, source_id, name, NULL::text AS country,
                       domain, NULL::text AS task_id, created_at
                       {payload_select}
                FROM lixiaoyun_raw_companies
            """.format(payload_select=payload_select),
        }
        count_sql = {
            "waimaotong": "SELECT COUNT(*) FROM waimaotong_raw_companies",
            "tendata": "SELECT COUNT(*) FROM tendata_raw_companies",
            "lixiaoyun": "SELECT COUNT(*) FROM lixiaoyun_raw_companies",
        }
        if table not in table_sql:
            raise AppError(
                code="VALIDATION_ERROR",
                message="table 必须是 waimaotong、tendata 或 lixiaoyun",
                status_code=422,
            )

        where_parts = []
        params = {"limit": page_size, "offset": (page - 1) * page_size}
        if keyword is not None:
            where_parts.append("name ILIKE '%' || :keyword || '%'")
            params["keyword"] = keyword

        if table == "tendata":
            if country is not None:
                where_parts.append("country_iso3 = :country")
                params["country"] = country
            if keyword_filter is not None:
                where_parts.append("raw_payload->>'keyword' = :keyword_filter")
                params["keyword_filter"] = keyword_filter
            if industry is not None:
                where_parts.append("industry_desc ILIKE '%' || :industry || '%'")
                params["industry"] = industry
            if tag is not None:
                where_parts.append(":tag = ANY(product_tags)")
                params["tag"] = tag
            SIZE_NUM_MAP = {
                "tiny": (None, 9),
                "small": (10, 49),
                "medium": (50, 199),
                "large": (200, None),
            }
            if size and size in SIZE_NUM_MAP:
                lo, hi = SIZE_NUM_MAP[size]
                if lo is not None:
                    where_parts.append("employee_num >= :size_lo")
                    params["size_lo"] = lo
                if hi is not None:
                    where_parts.append("employee_num <= :size_hi")
                    params["size_hi"] = hi
            if amount_min is not None:
                where_parts.append("trade_amount_3y_usd >= :amount_min")
                params["amount_min"] = amount_min
            if amount_max is not None:
                where_parts.append("trade_amount_3y_usd <= :amount_max")
                params["amount_max"] = amount_max
            if count_min is not None:
                where_parts.append("trade_count >= :count_min")
                params["count_min"] = count_min
            if count_max is not None:
                where_parts.append("trade_count <= :count_max")
                params["count_max"] = count_max
            if pcb == "yes":
                where_parts.append("array_length(pcb_suppliers, 1) > 0")
            elif pcb == "no":
                where_parts.append("(pcb_suppliers IS NULL OR array_length(pcb_suppliers, 1) = 0)")
            if contact_min is not None:
                where_parts.append("contacts_count >= :contact_min")
                params["contact_min"] = contact_min
            if contact_max is not None:
                where_parts.append("contacts_count <= :contact_max")
                params["contact_max"] = contact_max
            if year_min is not None:
                where_parts.append("EXTRACT(year FROM incorporation_date)::int >= :year_min")
                params["year_min"] = year_min
            if year_max is not None:
                where_parts.append("EXTRACT(year FROM incorporation_date)::int <= :year_max")
                params["year_max"] = year_max
            if method is not None:
                where_parts.append("raw_payload->>'collection_method' = :method")
                params["method"] = method

        elif table == "lixiaoyun":
            if keyword_filter is not None:
                where_parts.append(
                    "(raw_payload->>'keyword' = :keyword_filter OR raw_payload->>'search_keyword' = :keyword_filter)"
                )
                params["keyword_filter"] = keyword_filter
            if found_date_start is not None:
                where_parts.append("esdate >= :found_date_start")
                params["found_date_start"] = found_date_start
            if found_date_end is not None:
                where_parts.append("esdate <= :found_date_end")
                params["found_date_end"] = found_date_end
            _rc = _reg_cap_case("reg_capital")
            if reg_capital and reg_capital in REG_CAP_RANGE:
                where_parts.append(f"({_rc}) {REG_CAP_RANGE[reg_capital]}")
            _es = _employee_scale_case("employee_scale")
            if employee_scale and employee_scale in EMPLOYEE_SCALE_RANGE:
                where_parts.append(f"({_es}) {EMPLOYEE_SCALE_RANGE[employee_scale]}")
            # contacts_count 来自 raw_payload（lixiaoyun 表无此列）
            _CC_EXPR = """
COALESCE(
  CASE WHEN raw_payload->>'contacts_count' ~ E'^\\d+$' THEN (raw_payload->>'contacts_count')::int ELSE NULL END,
  CASE WHEN raw_payload->>'contact_num'    ~ E'^\\d+$' THEN (raw_payload->>'contact_num')::int ELSE NULL END,
  0
)
"""
            CC_MAP = {
                "0": f"({_CC_EXPR}) = 0",
                "1_3": f"({_CC_EXPR}) BETWEEN 1 AND 3",
                "4_10": f"({_CC_EXPR}) BETWEEN 4 AND 10",
                "gt10": f"({_CC_EXPR}) > 10",
            }
            if contacts_filter and contacts_filter in CC_MAP:
                where_parts.append(CC_MAP[contacts_filter])
            if has_name_en is True:
                where_parts.append("english_name IS NOT NULL AND english_name != ''")
            elif has_name_en is False:
                where_parts.append("(english_name IS NULL OR english_name = '')")
            if has_domain is True:
                where_parts.append("domain IS NOT NULL AND domain != ''")
            elif has_domain is False:
                where_parts.append("(domain IS NULL OR domain = '')")

        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

        total_result = await conn.execute(text(count_sql[table] + where_clause), params)
        total = int(total_result.scalar_one() or 0)

        result = await conn.execute(
            text(
                table_sql[table]
                + where_clause
                + """
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        rows = result.mappings().all()
        return (
            [
                (
                    {
                        "id": str(r["id"]),
                        "name": r["name"],
                        "country": r["country"],
                        "domain": r["domain"],
                        "task_id": str(r["task_id"]) if r["task_id"] else None,
                        "created_at": self._datetime_iso(r["created_at"]),
                        **({"source_id": r["source_id"]} if table != "tendata" else {}),
                        **(
                            {"source_id": r["source_id"], "tid": r["source_id"]}
                            if table == "tendata"
                            else {}
                        ),
                    }
                    | ({"raw_payload": r["raw_payload"]} if include_payload else {})
                )
                for r in rows
            ],
            total,
        )

    async def get_v3_raw_company_debug(
        self,
        conn,
        *,
        provider: str,
        raw_company_id: int,
    ) -> dict:
        if provider == "lixiaoyun":
            row = (
                (
                    await conn.execute(
                        text(
                            """
                            SELECT
                              c.pid, c.entname, c.entname_eng,
                              to_timestamp(c.esdate / 1000)::date AS esdate,
                              c.reg_cap,
                              c.official_website, c.regccap, c.scale, c.annual_turnover,
                              c.legalperson, c.geo_address, c.dom, c.keyword_master_id,
                              km.keyword, c.collected_at, c.entstatus, c.enttype,
                              c.opscope, c.industryphy_desc, c.secindustry_desc,
                              c.industry_l3_desc, c.industry_l4_desc,
                              c.uncid, c.ent_introduction,
                              to_timestamp(c.opfrom / 1000)::date AS opfrom,
                              to_timestamp(c.opto / 1000)::date AS opto,
                              c.regorg,
                              to_timestamp(c.apprdate / 1000)::date AS apprdate,
                              c.oploc
                            FROM lixiaoyun_api_companies c
                            JOIN keyword_master km ON km.id = c.keyword_master_id
                            WHERE c.id = :id
                            """
                        ),
                        {"id": raw_company_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise AppError(
                    code="RAW_COMPANY_NOT_FOUND",
                    message="raw company 不存在",
                    status_code=404,
                )
            item = dict(row)
            item["id"] = str(raw_company_id)
            item["provider"] = provider
            item["keyword_master_id"] = (
                str(item["keyword_master_id"]) if item.get("keyword_master_id") else None
            )
            for date_key in ("esdate", "opfrom", "opto", "apprdate"):
                if item.get(date_key):
                    item[date_key] = self._date_iso(item[date_key])
            if item.get("collected_at"):
                item["collected_at"] = self._datetime_iso(item["collected_at"])
            return item

        sql_by_provider = {
            "tendata": """
                SELECT id, source_id, raw_payload, NULL::jsonb AS search_payload,
                       NULL::jsonb AS detail_payload, NULL::jsonb AS trade_payload
                FROM tendata_raw_companies
                WHERE id = :id
            """,
            "waimaotong": """
                SELECT id, company_name, country, domain, industry, phone,
                       employee_size, founded_year, description, full_address,
                       website, source_tags,
                       source_keyword, source_competitor, source_type,
                       id_verified, api_company_id,
                       contacts_count, email_count,
                       has_detail, has_contacts,
                       created_at, updated_at
                FROM waimaotong_raw_companies
                WHERE id = :id
            """,
        }
        if provider not in sql_by_provider:
            raise AppError(
                code="VALIDATION_ERROR",
                message="provider 必须是 lixiaoyun、tendata 或 waimaotong",
                status_code=422,
            )

        row = (
            (
                await conn.execute(
                    text(sql_by_provider[provider]),
                    {"id": raw_company_id},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise AppError(
                code="RAW_COMPANY_NOT_FOUND",
                message="raw company 不存在",
                status_code=404,
            )

        # waimaotong 使用 dict(row) 模式，与 lixiaoyun 一致
        if provider == "waimaotong":
            item = dict(row)
            item["id"] = str(raw_company_id)
            item["provider"] = provider
            item["created_at"] = self._datetime_iso(item.get("created_at"))
            item["updated_at"] = self._datetime_iso(item.get("updated_at"))
            if "source_tags" in item:
                item["source_tags"] = list(item["source_tags"] or [])
            return item

        return {
            "id": str(row["id"]),
            "provider": provider,
            "source_id": row["source_id"],
            "raw_payload": row["raw_payload"] or {},
            "search_payload": row["search_payload"],
            "detail_payload": row["detail_payload"],
            "trade_payload": row["trade_payload"],
        }

    async def list_v3_raw_company_contacts(
        self,
        conn,
        *,
        provider: str,
        raw_company_id: int,
    ) -> list[dict]:
        sql_by_provider = {
            "tendata": """
                SELECT id, raw_company_id, source_contact_id, name, position, email, phone,
                       raw_payload, created_at
                FROM tendata_raw_contacts
                WHERE raw_company_id = :raw_company_id
                ORDER BY created_at ASC, id ASC
            """,
            "waimaotong": """
                SELECT id, raw_company_id, source_contact_id, name, position,
                       department, email, email_status, phone,
                       linkedin, source, confidence, created_at
                FROM waimaotong_raw_contacts
                WHERE raw_company_id = :raw_company_id
                ORDER BY created_at ASC, id ASC
            """,
        }
        sql = sql_by_provider.get(provider)
        if sql is None:
            return []

        result = await conn.execute(
            text(sql),
            {"raw_company_id": raw_company_id},
        )
        rows = []
        for row in result.mappings().all():
            item = dict(row)
            raw_payload = item.get("raw_payload") or {}
            item["id"] = str(item["id"])
            item["raw_company_id"] = str(item["raw_company_id"])
            item["email"] = str(item["email"]) if item.get("email") else None
            item["mobile"] = raw_payload.get("mobile") or raw_payload.get("phone_mobile")
            item["created_at"] = self._datetime_iso(item.get("created_at"))
            if item.get("confidence") is not None:
                item["confidence"] = float(item["confidence"])
            item.pop("raw_payload", None)
            rows.append(item)
        return rows


    async def list_v3_raw_companies(
        self,
        conn,
        *,
        provider: str,
        page: int = 1,
        page_size: int = 20,
        keyword_master_id: str | None = None,
        q: str | None = None,
        country_iso3: str | None = None,
        keyword_filter: str | None = None,
        found_date_start: str | None = None,
        found_date_end: str | None = None,
        reg_capital: str | None = None,
        employee_scale: str | None = None,
        contacts_filter: str | None = None,
        has_name_en: bool | None = None,
        has_domain: bool | None = None,
        industry: str | None = None,
        tag: str | None = None,
        size: str | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        count_min: int | None = None,
        count_max: int | None = None,
        pcb: str | None = None,
        contact_min: int | None = None,
        contact_max: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        method: str | None = None,
        # waimaotong 专属参数
        source_keyword: str | None = None,
        source_competitor: str | None = None,
        has_contacts: bool | None = None,
    ) -> tuple[list[dict], int]:
        if provider not in {"lixiaoyun", "tendata", "waimaotong"}:
            return [], 0

        where_parts = []
        params = {"limit": page_size, "offset": (page - 1) * page_size}
        if keyword_master_id:
            where_parts.append("c.keyword_master_id = :keyword_master_id")
            params["keyword_master_id"] = keyword_master_id
        if q:
            if provider == "lixiaoyun":
                where_parts.append(
                    """(
                        c.entname ILIKE :q
                        OR c.entname_eng ILIKE :q
                        OR c.official_website ILIKE :q
                        OR c.pid ILIKE :q
                    )"""
                )
            elif provider == "waimaotong":
                where_parts.append(
                    "("
                    "c.company_name ILIKE :q OR c.domain ILIKE :q"
                    ")"
                )
            else:
                where_parts.append(
                    "("
                    "c.name ILIKE :q OR c.name_local ILIKE :q "
                    "OR c.website ILIKE :q OR c.source_id ILIKE :q"
                    ")"
                )
            params["q"] = f"%{q}%"
        if provider == "tendata" and country_iso3:
            where_parts.append("c.country_iso3 = :country_iso3")
            params["country_iso3"] = country_iso3

        if provider == "lixiaoyun":
            if keyword_filter:
                where_parts.append("km.keyword ILIKE :keyword_filter")
                params["keyword_filter"] = f"%{keyword_filter}%"
            if found_date_start:
                where_parts.append(
                    "c.esdate >= EXTRACT(EPOCH FROM (CAST(:found_date_start AS date) AT TIME ZONE 'Asia/Shanghai')) * 1000"
                )
                params["found_date_start"] = _parse_date(found_date_start)
            if found_date_end:
                where_parts.append(
                    "c.esdate <= EXTRACT(EPOCH FROM (CAST(:found_date_end AS date) AT TIME ZONE 'Asia/Shanghai')) * 1000 + 86399999"
                )
                params["found_date_end"] = _parse_date(found_date_end)
            _rc = _reg_cap_case("c.reg_cap")
            if reg_capital in REG_CAP_RANGE:
                where_parts.append(f"({_rc}) {REG_CAP_RANGE[reg_capital]}")
            _es = _employee_scale_case("c.scale")
            if employee_scale in EMPLOYEE_SCALE_RANGE:
                where_parts.append(f"({_es}) {EMPLOYEE_SCALE_RANGE[employee_scale]}")
            if has_name_en is True:
                where_parts.append("c.entname_eng IS NOT NULL AND c.entname_eng != ''")
            elif has_name_en is False:
                where_parts.append("(c.entname_eng IS NULL OR c.entname_eng = '')")
            if has_domain is True:
                where_parts.append("c.official_website IS NOT NULL AND c.official_website != ''")
            elif has_domain is False:
                where_parts.append("(c.official_website IS NULL OR c.official_website = '')")
        elif provider == "waimaotong":
            # waimaotong 独立筛选分支——不引用已删除列
            if country_iso3:
                where_parts.append("c.country = :country")
                params["country"] = country_iso3
            if industry:
                where_parts.append("c.industry ILIKE :industry")
                params["industry"] = f"%{industry}%"
            _wmt_emp_expr = "NULLIF(substring(c.employee_size from '([0-9]+)'), '')::int"
            size_num_map = {
                "tiny": (None, 9),
                "small": (10, 49),
                "medium": (50, 199),
                "large": (200, None),
            }
            if size in size_num_map:
                lo, hi = size_num_map[size]
                if lo is not None:
                    where_parts.append(f"({_wmt_emp_expr}) >= :size_lo")
                    params["size_lo"] = lo
                if hi is not None:
                    where_parts.append(f"({_wmt_emp_expr}) <= :size_hi")
                    params["size_hi"] = hi
            if year_min is not None:
                where_parts.append("c.founded_year >= :year_min")
                params["year_min"] = year_min
            if year_max is not None:
                where_parts.append("c.founded_year <= :year_max")
                params["year_max"] = year_max
            if source_keyword:
                where_parts.append("c.source_keyword = :source_keyword")
                params["source_keyword"] = source_keyword
            if source_competitor:
                where_parts.append("c.source_competitor ILIKE :source_competitor")
                params["source_competitor"] = f"%{source_competitor}%"
            if has_contacts is True:
                where_parts.append("c.has_contacts = true")
        elif provider == "tendata":
            if industry:
                where_parts.append("c.industry_desc ILIKE :industry")
                params["industry"] = f"%{industry}%"
            if tag:
                where_parts.append(":tag = ANY(COALESCE(c.product_tags, ARRAY[]::text[]))")
                params["tag"] = tag
            _td_emp_expr = "NULLIF(substring(c.employee_num from '([0-9]+)'), '')::int"
            size_num_map = {
                "tiny": (None, 9),
                "small": (10, 49),
                "medium": (50, 199),
                "large": (200, None),
            }
            if size in size_num_map:
                lo, hi = size_num_map[size]
                if lo is not None:
                    where_parts.append(f"({_td_emp_expr}) >= :size_lo")
                    params["size_lo"] = lo
                if hi is not None:
                    where_parts.append(f"({_td_emp_expr}) <= :size_hi")
                    params["size_hi"] = hi
            if amount_min is not None:
                where_parts.append("c.trade_amount_3y_usd >= :amount_min")
                params["amount_min"] = amount_min
            if amount_max is not None:
                where_parts.append("c.trade_amount_3y_usd <= :amount_max")
                params["amount_max"] = amount_max
            if count_min is not None:
                where_parts.append("c.trade_count >= :count_min")
                params["count_min"] = count_min
            if count_max is not None:
                where_parts.append("c.trade_count <= :count_max")
                params["count_max"] = count_max
            if pcb == "yes":
                where_parts.append("array_length(c.pcb_suppliers, 1) > 0")
            elif pcb == "no":
                where_parts.append(
                    "(c.pcb_suppliers IS NULL OR array_length(c.pcb_suppliers, 1) = 0)"
                )
            if contact_min is not None:
                where_parts.append("c.contacts_count >= :contact_min")
                params["contact_min"] = contact_min
            if contact_max is not None:
                where_parts.append("c.contacts_count <= :contact_max")
                params["contact_max"] = contact_max
            if year_min is not None:
                where_parts.append("EXTRACT(year FROM c.incorporation_date)::int >= :year_min")
                params["year_min"] = year_min
            if year_max is not None:
                where_parts.append("EXTRACT(year FROM c.incorporation_date)::int <= :year_max")
                params["year_max"] = year_max
            if method:
                where_parts.append("c.raw_payload->>'collection_method' = :method")
                params["method"] = method

        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
        if provider == "lixiaoyun":
            count_from = """
                FROM lixiaoyun_api_companies c
                JOIN keyword_master km ON km.id = c.keyword_master_id
            """
        elif provider == "waimaotong":
            count_from = "FROM waimaotong_raw_companies c"
        else:
            count_from = """
                FROM tendata_raw_companies c
                LEFT JOIN keyword_master km ON km.id = c.keyword_master_id
            """
        total = int(
            (
                await conn.execute(
                    text(f"SELECT COUNT(*) {count_from} {where_clause}"),
                    params,
                )
            ).scalar_one()
            or 0
        )
        if provider == "lixiaoyun":
            sql = """
                SELECT c.id, c.pid, c.keyword_master_id, km.keyword,
                       c.entname, c.entname_eng,
                       to_timestamp(c.esdate / 1000)::date AS esdate,
                       c.reg_cap, c.official_website, c.regccap, c.scale,
                       c.annual_turnover, c.legalperson, c.geo_address, c.dom,
                       c.collected_at
                FROM lixiaoyun_api_companies c
                JOIN keyword_master km ON km.id = c.keyword_master_id
            """
        elif provider == "waimaotong":
            sql = """
                SELECT c.id, c.company_name, c.country, c.domain, c.industry,
                       c.employee_size, c.founded_year, c.full_address,
                       c.source_keyword, c.source_competitor, c.source_type,
                       c.contacts_count, c.email_count,
                       c.has_detail, c.has_contacts, c.id_verified,
                       c.website, c.api_company_id,
                       c.created_at
                FROM waimaotong_raw_companies c
            """
        else:
            sql = """
                SELECT c.id, c.keyword_master_id, c.source_id, c.collection_type, c.globiz_id,
                       km.keyword, c.name, c.name_local,
                       c.country_iso3, c.website, c.tax_no, c.incorporation_date, c.employee_num,
                       c.industry_desc, c.product_tags, c.pcb_suppliers, c.trade_amount_3y_usd,
                       c.trade_count, c.contacts_count, c.has_trade_data, c.aliases,
                       c.detail_status, c.detail_fetched_at, c.trade_status, c.trade_fetched_at,
                       c.contacts_status, c.contacts_fetched_at, c.created_at
                FROM tendata_raw_companies c
                LEFT JOIN keyword_master km ON km.id = c.keyword_master_id
            """
        if provider == "lixiaoyun":
            order_by = " ORDER BY c.collected_at DESC, c.id DESC LIMIT :limit OFFSET :offset"
        else:
            order_by = " ORDER BY c.created_at DESC, c.id DESC LIMIT :limit OFFSET :offset"
        result = await conn.execute(text(sql + where_clause + order_by), params)
        rows = []
        for row in result.mappings().all():
            item = dict(row)
            item["id"] = str(item["id"])
            item["keyword_master_id"] = (
                str(item["keyword_master_id"]) if item.get("keyword_master_id") else None
            )
            item["created_at"] = self._datetime_iso(item.get("created_at"))
            item["collected_at"] = self._datetime_iso(item.get("collected_at"))
            for key in ("product_tags", "pcb_suppliers", "aliases", "source_tags", "emails"):
                if key in item:
                    item[key] = list(item[key] or [])
            for key in ("trade_amount_3y_usd",):
                if key in item and item[key] is not None:
                    item[key] = float(item[key])
            if item.get("incorporation_date"):
                item["incorporation_date"] = item["incorporation_date"].isoformat()
            if item.get("esdate"):
                item["esdate"] = item["esdate"].isoformat()
            for key in ("detail_fetched_at", "trade_fetched_at", "contacts_fetched_at"):
                if item.get(key):
                    item[key] = self._datetime_iso(item[key])
            rows.append(item)
        return rows, total




    def _date_iso(self, value: date | datetime | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        return value.isoformat()

    def _datetime_iso(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    async def _scalar_int(self, conn, sql: str, params: dict | None = None) -> int:
        result = await conn.execute(text(sql), params or {})
        return int(result.scalar_one() or 0)







    # ── 同行公司（清洗）lixiaoyun_api_clean_companies ──────────

    def _esdate_to_date(self, ms_value) -> str | None:
        if ms_value is None:
            return None
        try:
            return datetime.fromtimestamp(int(ms_value) / 1000, tz=_BEIJING_TZ).date().isoformat()
        except (ValueError, TypeError, OSError):
            return None

    def _format_lixiaoyun_clean_row(self, r, *, detail: bool = False) -> dict:
        row = {
            "id": str(r["id"]),
            "pid": r["pid"],
            "entname": r["entname"],
            "entname_eng": r["entname_eng"],
            "esdate": self._esdate_to_date(r["esdate"]),
            "reg_cap": r["reg_cap"],
            "official_website": r["official_website"],
            "regccap": r["regccap"],
            "scale": r["scale"],
            "annual_turnover": r["annual_turnover"],
            "legalperson": r["legalperson"],
            "geo_address": r["geo_address"],
            "dom": r["dom"],
            "industry_tag": r["industry_tags"],
            "keyword_master": r.get("keyword_master") or [],
            "created_at": self._datetime_iso(r["created_at"]),
        }
        if detail:
            row.update(
                {
                    "uncid": r["uncid"],
                    "enttype": r["enttype"],
                    "enttype_code": r["enttype_code"],
                    "entstatus": r["entstatus"],
                    "entstatus_code": r["entstatus_code"],
                    "regno": r["regno"],
                    "organizational_code": r["organizational_code"],
                    "opfrom": r["opfrom"],
                    "opto": r["opto"],
                    "regorg": r["regorg"],
                    "apprdate": r["apprdate"],
                    "revokedate": r["revokedate"],
                    "province": r["province"],
                    "city": r["city"],
                    "district": r["district"],
                    "reg_province": r["reg_province"],
                    "reg_city": r["reg_city"],
                    "reg_district": r["reg_district"],
                    "oploc": r["oploc"],
                    "industryphy": r["industryphy"],
                    "industryphy_desc": r["industryphy_desc"],
                    "opscope": r["opscope"],
                    "secindustry": r["secindustry"],
                    "secindustry_desc": r["secindustry_desc"],
                    "industry_l3": r["industry_l3"],
                    "industry_l3_desc": r["industry_l3_desc"],
                    "industry_l4": r["industry_l4"],
                    "industry_l4_desc": r["industry_l4_desc"],
                    "historyname_list": r["historyname_list"],
                    "legalperson_desc": r["legalperson_desc"],
                    "location_code": r["location_code"],
                    "updated_at": self._datetime_iso(r["updated_at"]),
                }
            )
        return row

    def _lixiaoyun_clean_filter_parts(
        self,
        *,
        keyword: str | None = None,
        keyword_filter: str | None = None,
        industry_tag: str | None = None,
        found_date_start: str | None = None,
        found_date_end: str | None = None,
        reg_capital: str | None = None,
        employee_scale: str | None = None,
        has_name_en: bool | None = None,
        has_domain: bool | None = None,
    ) -> tuple[list[str], dict]:
        where_parts: list[str] = []
        params: dict = {}

        if keyword:
            where_parts.append(
                "(c.entname ILIKE :kw OR c.entname_eng ILIKE :kw"
                " OR c.official_website ILIKE :kw OR c.pid ILIKE :kw)"
            )
            params["kw"] = f"%{keyword}%"

        if keyword_filter:
            where_parts.append(
                "EXISTS (SELECT 1 FROM keyword_master km"
                " WHERE km.id = ANY(c.keyword_master_ids)"
                " AND (km.keyword ILIKE :keyword_filter"
                " OR km.keyword_normalized ILIKE :keyword_filter))"
            )
            params["keyword_filter"] = f"%{keyword_filter}%"

        if industry_tag:
            where_parts.append("c.industry_tags = :industry_tag")
            params["industry_tag"] = industry_tag

        if found_date_start:
            where_parts.append(
                "c.esdate >= EXTRACT(EPOCH FROM (CAST(:found_date_start AS date)"
                " AT TIME ZONE 'Asia/Shanghai')) * 1000"
            )
            params["found_date_start"] = _parse_date(found_date_start)

        if found_date_end:
            where_parts.append(
                "c.esdate <= EXTRACT(EPOCH FROM (CAST(:found_date_end AS date)"
                " AT TIME ZONE 'Asia/Shanghai')) * 1000 + 86399999"
            )
            params["found_date_end"] = _parse_date(found_date_end)

        _rc = _reg_cap_case("c.reg_cap")
        if reg_capital and reg_capital in REG_CAP_RANGE:
            where_parts.append(f"({_rc}) {REG_CAP_RANGE[reg_capital]}")

        _es = _employee_scale_case("c.scale")
        if employee_scale and employee_scale in EMPLOYEE_SCALE_RANGE:
            where_parts.append(f"({_es}) {EMPLOYEE_SCALE_RANGE[employee_scale]}")

        if has_name_en is True:
            where_parts.append("c.entname_eng IS NOT NULL AND c.entname_eng != ''")
        elif has_name_en is False:
            where_parts.append("(c.entname_eng IS NULL OR c.entname_eng = '')")

        if has_domain is True:
            where_parts.append("c.official_website IS NOT NULL AND c.official_website != ''")
        elif has_domain is False:
            where_parts.append("(c.official_website IS NULL OR c.official_website = '')")

        return where_parts, params

    async def list_lixiaoyun_clean_companies(
        self,
        conn: AsyncConnection,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        keyword_filter: str | None = None,
        industry_tag: str | None = None,
        found_date_start: str | None = None,
        found_date_end: str | None = None,
        reg_capital: str | None = None,
        employee_scale: str | None = None,
        has_name_en: bool | None = None,
        has_domain: bool | None = None,
    ) -> tuple[list[dict], int]:
        where_parts, params = self._lixiaoyun_clean_filter_parts(
            keyword=keyword,
            keyword_filter=keyword_filter,
            industry_tag=industry_tag,
            found_date_start=found_date_start,
            found_date_end=found_date_end,
            reg_capital=reg_capital,
            employee_scale=employee_scale,
            has_name_en=has_name_en,
            has_domain=has_domain,
        )
        where_clause = " AND ".join(where_parts) if where_parts else "TRUE"
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        rows = (
            await conn.execute(
                text(f"""
                    WITH filtered AS (
                        SELECT c.* FROM lixiaoyun_api_clean_companies c
                        WHERE {where_clause}
                        ORDER BY c.created_at DESC, c.id DESC
                        LIMIT :limit OFFSET :offset
                    ),
                    keyword_agg AS (
                        SELECT f.id AS company_id,
                               jsonb_agg(
                                   jsonb_build_object(
                                       'keyword_master_id', km.id::text,
                                       'keyword', km.keyword,
                                       'keyword_normalized', km.keyword_normalized
                                   ) ORDER BY km.keyword_normalized
                               ) AS keyword_master
                        FROM filtered f
                        JOIN keyword_master km ON km.id = ANY(f.keyword_master_ids)
                        GROUP BY f.id
                    )
                    SELECT f.*, COALESCE(ka.keyword_master, '[]'::jsonb) AS keyword_master
                    FROM filtered f
                    LEFT JOIN keyword_agg ka ON ka.company_id = f.id
                    ORDER BY f.created_at DESC, f.id DESC
                """),
                params,
            )
        ).mappings().all()

        total = (
            await conn.execute(
                text(f"SELECT COUNT(*) FROM lixiaoyun_api_clean_companies c WHERE {where_clause}"),
                params,
            )
        ).scalar_one()

        return [self._format_lixiaoyun_clean_row(r) for r in rows], int(total)

    async def get_lixiaoyun_clean_company_detail(
        self,
        conn: AsyncConnection,
        *,
        company_id: int,
    ) -> dict:
        row = (
            await conn.execute(
                text("""
                    SELECT c.*,
                           COALESCE(
                               (SELECT jsonb_agg(
                                   jsonb_build_object(
                                       'keyword_master_id', km.id::text,
                                       'keyword', km.keyword,
                                       'keyword_normalized', km.keyword_normalized
                                   ) ORDER BY km.keyword_normalized
                               )
                               FROM keyword_master km
                               WHERE km.id = ANY(c.keyword_master_ids)),
                               '[]'::jsonb
                           ) AS keyword_master
                    FROM lixiaoyun_api_clean_companies c
                    WHERE c.id = :company_id
                """),
                {"company_id": company_id},
            )
        ).mappings().first()

        if row is None:
            raise AppError(
                code="CLEAN_COMPANY_NOT_FOUND",
                message="清洗公司不存在",
                status_code=404,
            )

        return self._format_lixiaoyun_clean_row(row, detail=True)

    # ── waimaotong clean companies ──────────────────────────────────

    async def list_wmt_clean_companies(
        self,
        conn: AsyncConnection,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        country: str | None = None,
        industry: str | None = None,
        size: str | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        has_contacts: bool | None = None,
        grade: str | None = None,
        collection_type: str | None = None,
    ) -> tuple[list[dict], int]:
        where_parts: list[str] = []
        params: dict = {"limit": page_size, "offset": (page - 1) * page_size}

        if q:
            where_parts.append(
                "(company_name ILIKE '%' || :q || '%' OR domain ILIKE '%' || :q || '%')"
            )
            params["q"] = q
        if country:
            where_parts.append("country = :country")
            params["country"] = country
        if industry:
            where_parts.append("industry ILIKE '%' || :industry || '%'")
            params["industry"] = industry

        _emp_expr = "NULLIF(substring(employee_size from '([0-9]+)'), '')::int"
        size_num_map = {
            "tiny": (None, 9),
            "small": (10, 49),
            "medium": (50, 199),
            "large": (200, None),
        }
        if size and size in size_num_map:
            lo, hi = size_num_map[size]
            if lo is not None:
                where_parts.append(f"({_emp_expr}) >= :size_lo")
                params["size_lo"] = lo
            if hi is not None:
                where_parts.append(f"({_emp_expr}) <= :size_hi")
                params["size_hi"] = hi

        if year_min is not None:
            where_parts.append("founded_year >= :year_min")
            params["year_min"] = year_min
        if year_max is not None:
            where_parts.append("founded_year <= :year_max")
            params["year_max"] = year_max
        if has_contacts is True:
            where_parts.append("contacts_count > 0")
        if grade:
            where_parts.append("grade = :grade")
            params["grade"] = grade
        collection_type_filter = build_collection_type_filter(
            collection_type,
            company_alias="wc",
        )
        if collection_type_filter:
            where_parts.append(collection_type_filter)

        where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

        total = await self._scalar_int(
            conn,
            "SELECT COUNT(*) FROM waimaotong_clean_companies wc" + where_clause,
            params,
        )

        result = await conn.execute(
            text(
                """
                SELECT id, source_id, name, company_name, english_name,
                       country, country_iso3, domain, industry, sub_industry,
                       phone, employee_size, company_size, founded_year,
                       website, full_address, description,
                       grade, score, email_priority, company_type_analysis,
                       product_tags, data_source_tags,
                       has_trade_data, trade_amount_3y_usd, trade_count,
                       contacts_count,
                       detail_status, contacts_status, trade_status,
                       sys_company_id,
                       EXISTS (
                         SELECT 1
                         FROM waimaotong_raw_companies wr_collection_source
                         WHERE wr_collection_source.sys_company_id = wc.sys_company_id
                           AND NULLIF(BTRIM(wr_collection_source.source_competitor), '') IS NOT NULL
                       ) AS has_source_competitor,
                       created_at, updated_at
                FROM waimaotong_clean_companies wc
                """
                + where_clause
                + """
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        rows = []
        for r in result.mappings().all():
            item = dict(r)
            item["id"] = str(item["id"])
            item["sys_company_id"] = str(item["sys_company_id"]) if item.get("sys_company_id") else None
            item["score"] = float(item["score"]) if item.get("score") is not None else None
            item["trade_amount_3y_usd"] = float(item["trade_amount_3y_usd"]) if item.get("trade_amount_3y_usd") is not None else None
            item["product_tags"] = list(item["product_tags"] or [])
            item["data_source_tags"] = list(item["data_source_tags"] or [])
            item["collection_type"] = compute_collection_type(
                item["data_source_tags"],
                source_id=item.get("source_id"),
                has_source_competitor=item.pop("has_source_competitor"),
            )
            item["created_at"] = self._datetime_iso(item.get("created_at"))
            item["updated_at"] = self._datetime_iso(item.get("updated_at"))
            rows.append(item)
        return rows, total

    async def get_wmt_clean_company(
        self,
        conn: AsyncConnection,
        *,
        company_id: int,
    ) -> dict:
        row = (
            await conn.execute(
                text("""
                    SELECT wc.*,
                           EXISTS (
                             SELECT 1
                             FROM waimaotong_raw_companies wr_collection_source
                             WHERE wr_collection_source.sys_company_id = wc.sys_company_id
                               AND NULLIF(BTRIM(wr_collection_source.source_competitor), '')
                                   IS NOT NULL
                           ) AS has_source_competitor
                    FROM waimaotong_clean_companies wc
                    WHERE wc.id = :id
                """),
                {"id": company_id},
            )
        ).mappings().first()

        if row is None:
            raise AppError(
                code="NOT_FOUND",
                message="公司不存在",
                status_code=404,
            )

        item = dict(row)
        item.pop("system_grade", None)
        item.pop("system_score", None)
        item["id"] = str(item["id"])
        item["sys_company_id"] = str(item["sys_company_id"]) if item.get("sys_company_id") else None
        item["score"] = float(item["score"]) if item.get("score") is not None else None
        item["trade_amount_3y_usd"] = float(item["trade_amount_3y_usd"]) if item.get("trade_amount_3y_usd") is not None else None
        item["product_tags"] = list(item["product_tags"] or [])
        item["data_source_tags"] = list(item["data_source_tags"] or [])
        item["collection_type"] = compute_collection_type(
            item["data_source_tags"],
            source_id=item.get("source_id"),
            has_source_competitor=item.pop("has_source_competitor"),
        )
        item["created_at"] = self._datetime_iso(item.get("created_at"))
        item["updated_at"] = self._datetime_iso(item.get("updated_at"))
        return item

    async def list_wmt_clean_company_contacts(
        self,
        conn: AsyncConnection,
        *,
        company_id: int,
    ) -> list[dict]:
        result = await conn.execute(
            text("""
                SELECT id, name, position, department, email, email_status,
                       phone, mobile, linkedin, whatsapp, source, confidence,
                       created_at
                FROM waimaotong_clean_contacts
                WHERE sys_company_id = (
                    SELECT sys_company_id FROM waimaotong_clean_companies WHERE id = :id
                )
                ORDER BY created_at ASC
            """),
            {"id": company_id},
        )
        rows = []
        for r in result.mappings().all():
            item = dict(r)
            item["id"] = str(item["id"])
            if item.get("confidence") is not None:
                item["confidence"] = float(item["confidence"])
            item["created_at"] = self._datetime_iso(item.get("created_at"))
            rows.append(item)
        return rows
