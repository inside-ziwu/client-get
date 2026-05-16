import asyncio
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Any

import httpx

from app.core.errors import AppError, CredentialExpiredError
from app.integrations.collection.base import CollectionPayload, CollectionProvider, CollectionTask
from app.utils.country import to_iso3

logger = logging.getLogger(__name__)

_T1_ALL_DATABASES = (
    "america,america_ship,america_stat,canada_stat,canada,dominica,mexico_bol,mexico,"
    "costarica,dominican_republic,dominican_republic_stat,guatemala_nboe,guatemala_stat,"
    "guatemala,panama,panama_exp,honduras_stat,honduras,salvador_stat,salvador,"
    "nicaragua_boe,nicaragua,brazil_pro,brazil_stat,brazil_bol,brazil_air,brazil_proc,"
    "brazil,argentina,argentina_bol,colon_free_zone,ecuador,ecuador_bol,chile,peru,"
    "peru_exp,colombia,colombia_nboe,venezuela,venezuela_bol,bolivia,bolivia_stat,"
    "paraguay,uruguay,uruguay_nboe,uruguay_bol,china_stat,vietnam,india,india_exp,"
    "turkey,turkey_stat,philippines,philippines_stat,thailand,thailand_stat,japan,"
    "south_korea_co,south_korea_stat,south_korea,taiwan_stat,taiwan,hongkong_stat,"
    "indonesia_pro,indonesia_stat,indonesia,kyrghyzstan,uzbekistan,pakistan,"
    "pakistan_nboe,pakistan_bol,kazakhstan,sri_lanka,bangladesh,armenia,russia,"
    "russia_rail,bahrain_stat,maritime_silk_bol,qatar_stat,cis,european_union,"
    "eurasian_eu,eurasian_bol,malaysia_pro,spain,spain_co,afghanistan,england,"
    "england_stat,moldova,ukraine,eurasian_eu_kz,kenya_nboe,kenya_tboe,kenya,nigeria,"
    "united_nations_stat,uganda,iran,ethiopia,ivory_coast,south_africa_stat,ghana,"
    "zimbabwe,namibia,cameroon,tanzania,maldives,tanzania_tboe,liberia,mongolia,"
    "botswana,lesotho,burundi,central_african_republic,chad,palestine,rwanda,australia,"
    "malawi,new_zealand,fiji,congo_kinshasa,angola,angola_stat,sao_tome_and_principe,"
    "egypt_co,south_sudan,madagascar,madagascar_free_zone"
)
_DATA_HOST = "https://data.tendata.cn"
_BIZR_HOST = "https://bizr.tendata.cn"
_T1_PAGE_SIZE = 20
_CONTACTS_PAGE_SIZE = 20
_SEMAPHORE_CONCURRENCY = 3
_RETRY_MAX = 3
_RETRY_BASE = 2.0


class TendataCollectionProvider(CollectionProvider):
    source_type = "tengdao"

    def __init__(self, credentials: list[dict]) -> None:
        self._credentials = credentials

    async def collect(self, task: CollectionTask) -> CollectionPayload:
        if not task.competitor_names:
            return CollectionPayload()

        cred = self._credential()
        max_buyers = self._max_buyers(task.params)

        async with httpx.AsyncClient(
            headers=self._headers(cred),
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            buyers_by_key: dict[str, dict] = {}
            for competitor_name in task.competitor_names:
                for item in await self._fetch_t1_importers(client, competitor_name):
                    self._merge_buyer(buyers_by_key, item, competitor_name)

            buyers = list(buyers_by_key.values())
            if max_buyers is not None:
                buyers = buyers[:max(0, max_buyers)]

            semaphore = asyncio.Semaphore(_SEMAPHORE_CONCURRENCY)
            results = await asyncio.gather(
                *(self._collect_company(client, semaphore, buyer) for buyer in buyers),
                return_exceptions=True,
            )

        companies: list[dict] = []
        for buyer, result in zip(buyers, results):
            if isinstance(result, CredentialExpiredError):
                raise result
            if isinstance(result, Exception):
                logger.warning("Tendata enrichment failed for '%s': %s", buyer["name"], result)
                continue
            if result:
                companies.append(result)

        return CollectionPayload(companies=companies)

    def _credential(self) -> dict:
        active = [cred for cred in self._credentials if cred.get("is_active", True)]
        if not active:
            raise AppError(
                code="NO_CREDENTIAL",
                message="腾道数据源没有可用凭证，请在管理后台配置 Cookie 会话",
                status_code=503,
            )
        return active[0]

    def _headers(self, cred: dict) -> dict:
        # JSESSIONID 为可选字段，腾道仅凭 token + userId Cookie 即可通过认证
        cookie = f"token={cred['token']}; userId={cred['userId']}"
        if cred.get("jsessionid"):
            cookie += f"; JSESSIONID={cred['jsessionid']}"
        return {
            "Cookie": cookie,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
        }

    def _max_buyers(self, params: dict | None) -> int | None:
        if not params or params.get("max_buyers") is None:
            return None
        return int(params["max_buyers"])

    async def _fetch_t1_importers(
        self,
        client: httpx.AsyncClient,
        competitor_name: str,
    ) -> list[dict]:
        items: list[dict] = []
        page = 1

        today = date.today().isoformat()
        start_date = (date.today() - timedelta(days=3 * 365)).isoformat()

        while True:
            body = {
                "country": _T1_ALL_DATABASES,
                "catalog": "imports",
                "conditionGroups": [{
                    "conditions": [{
                        "param": "exporter",
                        "character": "",
                        "value": [competitor_name],
                        "queryFields": ["exporter", "exporterOrig"],
                    }]
                }],
                "startDate": start_date,
                "endDate": today,
                "filterBlankFields": ["importer"],
                "filterRepetitive": True,
                "active": True,
                "level": "LOW",
                "size": _T1_PAGE_SIZE,
                "page": page,
            }
            try:
                data = await self._request_json(
                    client,
                    "POST",
                    f"{_DATA_HOST}/api/tradec1/v2/search",
                    json=body,
                )
            except CredentialExpiredError:
                raise
            except Exception as exc:
                logger.warning("Tendata T1 failed for '%s': %s", competitor_name, exc)
                break

            if data is None:
                break

            page_items = [item for item in data.get("items") or [] if isinstance(item, dict)]
            items.extend(page_items)

            total = self._to_int(data.get("total")) or 0
            size = self._to_int(data.get("size")) or _T1_PAGE_SIZE
            current_page = self._to_int(data.get("page")) or page
            if not page_items or current_page * size >= total:
                break
            page += 1

        return items

    def _merge_buyer(
        self,
        buyers_by_key: dict[str, dict],
        item: dict,
        competitor_name: str,
    ) -> None:
        importer = self._clean_text(item.get("importer"))
        if not importer:
            return

        key = importer.lower()
        buyer = buyers_by_key.setdefault(
            key,
            {
                "name": importer,
                "country": self._clean_text(item.get("country")),
                "records": [],
                "pcb_suppliers": [],
                "product_tags": [],
                "trade_sources": [],
            },
        )
        if not buyer.get("country"):
            buyer["country"] = self._clean_text(item.get("country"))

        buyer["records"].append(item)
        self._append_unique(buyer["pcb_suppliers"], item.get("exporter") or competitor_name)
        self._append_unique(buyer["product_tags"], item.get("productTag"))
        self._append_unique(buyer["trade_sources"], item.get("database"))

    async def _collect_company(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        buyer: dict,
    ) -> dict | None:
        async with semaphore:
            name = buyer["name"]
            raw_country = buyer.get("country")
            country_iso3 = to_iso3(raw_country) if raw_country else None
            brief = await self._fetch_brief(client, name, country_iso3)
            if not brief:
                logger.warning("Tendata BRIEF failed for '%s'; skipping company", name)
                return None

            tid = self._clean_text(brief.get("tid"))
            if not tid:
                logger.warning("Tendata BRIEF missing tid for '%s'; skipping company", name)
                return None

            t3, vot, stats = await self._gather_optional(
                ("T3", self._fetch_t3(client, tid)),
                ("VOT", self._fetch_vot(client, brief)),
                ("STATS", self._fetch_stats(client, brief)),
                company_name=name,
            )
            li_contacts, net_contacts, more_contacts = await self._gather_optional(
                ("T4-LI", self._fetch_linkedin_contacts(client, brief)),
                ("T4-NET", self._fetch_internet_contacts(client, brief)),
                ("T4-MORE", self._fetch_more_contacts(client, tid)),
                company_name=name,
            )

        contacts = self._merge_contacts(
            li_contacts or [],
            net_contacts or [],
            more_contacts or [],
        )
        return self._build_company(buyer, brief, t3 or {}, vot or {}, stats or {}, contacts)

    async def _gather_optional(
        self,
        *calls: tuple[str, Any],
        company_name: str,
    ) -> list[Any]:
        results = await asyncio.gather(*(call for _, call in calls), return_exceptions=True)
        values: list[Any] = []
        for (label, _), result in zip(calls, results):
            if isinstance(result, CredentialExpiredError):
                raise result
            if isinstance(result, Exception):
                logger.warning("Tendata %s failed for '%s': %s", label, company_name, result)
                values.append(None)
                continue
            if result is None:
                logger.warning("Tendata %s failed for '%s'", label, company_name)
            values.append(result)
        return values

    async def _fetch_brief(
        self,
        client: httpx.AsyncClient,
        company_name: str,
        country_iso3: str | None = None,
    ) -> dict | None:
        params: dict = {
            "queryType": "BRIEF",
            "catalog": "BUYER",
            "name": company_name,
            "source": "TRADE",
        }
        if country_iso3:
            params["country"] = country_iso3
        return await self._request_json(
            client,
            "GET",
            f"{_BIZR_HOST}/api/corp/v2/companies/brief/0",
            params=params,
        )

    async def _fetch_t3(self, client: httpx.AsyncClient, tid: str) -> dict | None:
        return await self._request_json(
            client,
            "GET",
            f"{_BIZR_HOST}/api/corp/v2/companies/0/{tid}",
        )

    async def _fetch_vot(self, client: httpx.AsyncClient, brief: dict) -> dict | None:
        body = {**self._company_report_body(brief), "reportType": "volume_of_trade"}
        return await self._request_json(
            client,
            "POST",
            f"{_BIZR_HOST}/api/bizr/v1/user/trade/company/report/0/volume_of_trade",
            json=body,
        )

    async def _fetch_stats(self, client: httpx.AsyncClient, brief: dict) -> dict | None:
        body = {**self._company_report_body(brief), "statFields": "trades,top_items,exporter"}
        return await self._request_json(
            client,
            "POST",
            f"{_BIZR_HOST}/api/bizr/v1/user/trade/company/reports/0/stats",
            json=body,
        )

    async def _fetch_linkedin_contacts(
        self,
        client: httpx.AsyncClient,
        brief: dict,
    ) -> list[dict] | None:
        tid = brief.get("tid") or ""
        # Extract LinkedIn company slug from moreInfo.linkedins[0].value URL
        linkedin_slug = self._extract_linkedin_slug(
            (brief.get("moreInfo") or {}).get("linkedins") or []
        )
        params: dict = {
            "tid": tid,
            "globizCompanyId": brief.get("globizId") or "",
            "companyName": brief.get("name") or "",
            "website": brief.get("website") or "",
            "country": brief.get("country") or "",
            "taxNo": brief.get("taxNo") or "",
            "linkedInCompanyId": linkedin_slug or "",
            "page": 0,
            "size": _CONTACTS_PAGE_SIZE,
        }
        data = await self._request_json(
            client,
            "GET",
            f"{_BIZR_HOST}/api/contactx/v3/contacts/linkedin",
            params=params,
        )
        if data is None:
            return None
        content = [item for item in data.get("content") or [] if isinstance(item, dict)]
        return self._dedupe_endpoint_contacts(
            [self._normalize_linkedin_contact(item) for item in content],
            content,
            "uniqueKey",
        )

    async def _fetch_internet_contacts(
        self,
        client: httpx.AsyncClient,
        brief: dict,
    ) -> list[dict] | None:
        tid = brief.get("tid") or ""
        params: dict = {
            "tid": tid,
            "companyName": brief.get("name") or "",
            "website": brief.get("website") or "",
            "taxNo": brief.get("taxNo") or "",
            "page": 0,
            "size": _CONTACTS_PAGE_SIZE,
        }
        data = await self._request_json(
            client,
            "GET",
            f"{_BIZR_HOST}/api/contactx/v3/contacts/internet",
            params=params,
        )
        if data is None:
            return None
        content = [item for item in data.get("content") or [] if isinstance(item, dict)]
        return self._dedupe_endpoint_contacts(
            [self._normalize_internet_contact(item) for item in content],
            content,
            "uniqueKey",
        )

    def _extract_linkedin_slug(self, linkedins: list) -> str | None:
        """Extract company slug from LinkedIn URL, e.g. 'nordin-technologies' from URL."""
        for item in linkedins:
            url = (item.get("value") if isinstance(item, dict) else None) or ""
            # URL like: https://www.linkedin.com/company/nordin-technologies
            parts = url.rstrip("/").split("/")
            if "company" in parts:
                idx = parts.index("company")
                if idx + 1 < len(parts) and parts[idx + 1]:
                    return parts[idx + 1]
        return None

    async def _fetch_more_contacts(
        self,
        client: httpx.AsyncClient,
        tid: str,
    ) -> list[dict] | None:
        contacts: list[dict] = []
        seen_ids: set[str] = set()
        page = 1

        while True:
            data = await self._request_json(
                client,
                "GET",
                f"{_BIZR_HOST}/api/contactx/v2/contacts/more",
                params={"tid": tid, "page": page, "size": _CONTACTS_PAGE_SIZE},
            )
            if data is None:
                return None

            content = [item for item in data.get("content") or [] if isinstance(item, dict)]
            for item in content:
                contact_id = self._clean_text(item.get("id"))
                if contact_id and contact_id in seen_ids:
                    continue
                if contact_id:
                    seen_ids.add(contact_id)
                contact = self._normalize_more_contact(item)
                if contact.get("email"):
                    contacts.append(contact)

            if len(content) < _CONTACTS_PAGE_SIZE:
                break
            page += 1

        return contacts

    def _company_report_body(self, brief: dict) -> dict:
        """Base body for VOT and STATS requests. Callers add reportType or statFields."""
        today = date.today().isoformat()
        start_date = (date.today() - timedelta(days=3 * 365)).isoformat()
        # Extract all checked aliases from BRIEF
        aliases_raw = brief.get("aliases") or []
        if isinstance(aliases_raw, list):
            aliases = [
                item["alias"] if isinstance(item, dict) else str(item)
                for item in aliases_raw
                if item
            ]
        else:
            aliases = []
        if brief.get("name") and brief["name"] not in aliases:
            aliases.insert(0, brief["name"])
        return {
            "catalog": "all",
            "country": "all",
            "startDate": start_date,
            "endDate": today,
            "productNames": [],
            "productTags": [],
            "importers": [],
            "exporters": [],
            "filterRepetitive": True,
            "tradeCountries": [],
            "hsCodes": [],
            "companyType": "IMPORTER",
            "keyword": brief.get("name") or "",
            "aliases": aliases,
            "size": 50,
        }

    def _build_company(
        self,
        buyer: dict,
        brief: dict,
        t3: dict,
        vot: dict,
        stats: dict,
        contacts: list[dict],
    ) -> dict:
        country = brief.get("country") or buyer.get("country")
        website = brief.get("website") or self._first(t3.get("websites"))
        trade_stats = vot.get("stats") or {}
        pcb_suppliers = list(buyer["pcb_suppliers"])
        product_tags = list(buyer["product_tags"])
        trade_sources = list(buyer["trade_sources"])

        exporter_results = ((stats.get("exporter") or {}).get("results")) or []
        for item in exporter_results:
            if isinstance(item, dict):
                self._append_unique(pcb_suppliers, item.get("__gk"))

        for item in stats.get("top_items") or []:
            if isinstance(item, dict):
                self._append_unique(product_tags, item.get("productTag") or item.get("name"))

        return {
            "target_table": "tendata_raw_companies",
            "tid": brief.get("tid"),
            "globiz_id": brief.get("globizId"),
            "name": brief.get("name") or buyer["name"],
            "country_iso3": to_iso3(country) if country else None,
            "website": website,
            "tax_no": brief.get("taxNo"),
            "industry_desc": t3.get("industryDesc"),
            "employee_num": t3.get("employeeNum"),
            "incorporation_date": t3.get("incorporationDate"),
            "trade_amount_3y_usd": self._to_float(trade_stats.get("total_sumOfMoney_sum")),
            "trade_count": self._to_int(trade_stats.get("total_trades_sum")),
            "pcb_suppliers": pcb_suppliers,
            "product_tags": product_tags,
            "trade_sources": trade_sources,
            "contacts_count": len(contacts),
            "contacts": contacts,
            "data_source": "腾道",
            "has_trade_data": True,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": {
                "t1": buyer["records"],
                "brief": brief,
                "t3": t3,
                "vot": vot,
                "stats": stats,
            },
        }

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs,
    ) -> dict | None:
        resp = await self._request_with_retry(client, method, url, **kwargs)
        body = self._json_body(resp)

        if resp.status_code == 401 or self._body_code(body) == 401:
            raise CredentialExpiredError(message="腾道 Cookie 会话已过期，请重新登录并更新凭证")

        if resp.status_code != 200:
            if resp.status_code == 429 or resp.status_code >= 500:
                logger.warning("Tendata request returned %s for %s", resp.status_code, url)
            return None

        return body

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        for attempt in range(_RETRY_MAX + 1):
            resp = await client.request(method, url, **kwargs)
            if resp.status_code != 429:
                return resp
            if attempt == _RETRY_MAX:
                logger.warning("Tendata rate limited after %d retries: %s", _RETRY_MAX, url)
                return resp
            wait = self._retry_after(resp) or (_RETRY_BASE ** attempt)
            logger.info(
                "Tendata rate limited, waiting %.1fs before retry %d/%d",
                wait,
                attempt + 1,
                _RETRY_MAX,
            )
            await asyncio.sleep(wait)
        return resp

    def _json_body(self, resp: httpx.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    def _body_code(self, body: dict) -> int | None:
        try:
            return int(body.get("code"))
        except (TypeError, ValueError):
            return None

    def _retry_after(self, resp: httpx.Response) -> float | None:
        value = resp.headers.get("Retry-After")
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _normalize_linkedin_contact(self, item: dict) -> dict:
        email = item.get("email") or ((item.get("personalEmail1") or {}).get("email"))
        return {
            "name": self._clean_text(item.get("name")),
            "position": self._clean_text(item.get("position")),
            "email": self._clean_email(email),
            "importance": None,
            "description": None,
            "verified": item.get("emailVerify"),
        }

    def _normalize_internet_contact(self, item: dict) -> dict:
        return {
            "name": self._clean_text(item.get("name")),
            "position": None,
            "email": self._clean_email(item.get("email")),
            "importance": item.get("important"),
            "description": item.get("description"),
            "verified": None,
        }

    def _normalize_more_contact(self, item: dict) -> dict:
        return {
            "name": self._clean_text(item.get("name")),
            "position": self._clean_text(item.get("position")),
            "email": self._clean_email(item.get("email")),
            "importance": None,
            "description": None,
            "verified": self._verified_from_status(item.get("status")),
        }

    def _dedupe_endpoint_contacts(
        self,
        contacts: list[dict],
        raw_items: list[dict],
        key_name: str,
    ) -> list[dict]:
        result: list[dict] = []
        seen_keys: set[str] = set()
        for contact, raw in zip(contacts, raw_items):
            key = self._clean_text(raw.get(key_name))
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)
            if contact.get("email"):
                result.append(contact)
        return result

    def _merge_contacts(self, *contact_groups: list[dict]) -> list[dict]:
        by_email: dict[str, dict] = {}

        for group in contact_groups:
            for contact in group:
                self._merge_contact(by_email, contact)

        return list(by_email.values())

    def _merge_contact(self, by_email: dict[str, dict], contact: dict) -> None:
        email = self._clean_email(contact.get("email"))
        if not email:
            return
        contact = {**contact, "email": email}
        current = by_email.get(email)
        if current is None:
            by_email[email] = contact
            return

        if self._contact_score(contact) > self._contact_score(current):
            current["name"] = contact.get("name")
            current["position"] = contact.get("position")
        for field in ("importance", "description", "verified"):
            if current.get(field) in (None, "") and contact.get(field) not in (None, ""):
                current[field] = contact.get(field)

    def _contact_score(self, contact: dict) -> int:
        return sum(1 for field in ("name", "position") if contact.get(field))

    def _clean_email(self, value: Any) -> str | None:
        text = self._clean_text(value)
        if not text:
            return None
        return text.split("^", 1)[0].strip().lower() or None

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _append_unique(self, values: list, value: Any) -> None:
        text = self._clean_text(value)
        if text and text not in values:
            values.append(text)

    def _first(self, values: Any) -> Any:
        if isinstance(values, list) and values:
            return values[0]
        return None

    def _to_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _verified_from_status(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        text = self._clean_text(value)
        if not text:
            return None
        return text.lower() in {"verified", "valid", "success", "已验证", "有效"}
