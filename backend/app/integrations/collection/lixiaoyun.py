import asyncio
import logging

import httpx

from app.core.errors import AppError, CredentialExpiredError
from app.integrations.collection.base import CollectionPayload, CollectionProvider, CollectionTask

logger = logging.getLogger(__name__)

_SEARCH_BASE_URL = "https://skb.weiwenjia.com"
_DETAIL_BASE_URL = "https://enterprise.weiwenjia.com"
_DEFAULT_PAGE_SIZE = 10
_MAX_PAGE_SIZE = 100
_DETAIL_CONCURRENCY = 3
_CONTACTS_DELAY = 0.5   # seconds before each contacts request (quota-consuming)
_RETRY_MAX = 3          # max retries on 429
_RETRY_BASE = 2.0       # exponential backoff base in seconds


class LixiaoyunCollectionProvider(CollectionProvider):
    """
    Domestic competitor company data from 励销云 (lixiaoyun).

    Credential:
      - secret      = token string from browser Authorization header (after "Token token=", no quotes)
      - account_no  = distinct_id (numeric user ID visible in browser request headers)

    Stage 1: keyword search → Chinese PCB manufacturers (competitors)
    Each competitor is enriched via detail APIs (BaseInfo + Development sections)
    and optionally contact API (phone + position, quota-consuming).
    English names (entNameEng from BaseInfo/GSInfo) are passed to Tendata Stage 2.
    """

    source_type = "lixiaoyun"

    def __init__(self, credentials: list[dict]) -> None:
        self._credentials = credentials

    def _credential(self) -> dict:
        active = [c for c in self._credentials if c.get("is_active", True)]
        if not active:
            raise AppError(
                code="NO_CREDENTIAL",
                message="励销云数据源没有可用凭证，请在管理后台配置 Token",
                status_code=503,
            )
        return active[0]

    @staticmethod
    def _ascii_header_val(value: str | None, field: str) -> str | None:
        """HTTP header value 必须是 ASCII；非 ASCII 值记录警告并返回 None。"""
        if not value:
            return None
        s = str(value)
        if not s.isascii():
            logger.warning(
                "Lixiaoyun credential field '%s' contains non-ASCII characters and will be ignored. "
                "Please update the credential in the admin panel with a valid ASCII value.",
                field,
            )
            return None
        return s

    def _search_headers(self, cred: dict) -> dict:
        token = self._ascii_header_val(cred.get("secret"), "secret/token")
        headers = {
            "Authorization": f"Token token={token or ''}",
            "crm_platform_type": "lixiaoyun",
            "app_token": "a14cc8b00f84e64b438af540390531e4",
            "platform_type": "web",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Origin": "https://lxcrm.weiwenjia.com",
            "Referer": "https://lxcrm.weiwenjia.com/",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }
        distinct_id = self._ascii_header_val(cred.get("account_no"), "account_no/distinct_id")
        if distinct_id:
            headers["distinct_id"] = distinct_id
        return headers

    def _detail_headers(self, cred: dict) -> dict:
        # Detail API (enterprise.weiwenjia.com) requires platform_type=PC and extra brand headers
        token = self._ascii_header_val(cred.get("secret"), "secret/token")
        headers = {
            "Authorization": f"Token token={token or ''}",
            "crm_platform_type": "lixiaoyun",
            "app_token": "a14cc8b00f84e64b438af540390531e4",
            "platform_type": "PC",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Origin": "https://lxcrm.weiwenjia.com",
            "Referer": "https://lxcrm.weiwenjia.com/",
            "Accept": "application/json, text/plain, */*",
        }
        distinct_id = self._ascii_header_val(cred.get("account_no"), "account_no/distinct_id")
        if distinct_id:
            headers["distinct_id"] = distinct_id
        return headers

    async def collect(self, task: CollectionTask) -> CollectionPayload:
        cred = self._credential()
        payload = CollectionPayload()
        raw_items: list[dict] = []
        params = task.params or {}
        max_competitors: int = params.get("max_competitors", 30)
        page_size = self._bounded_page_size(params.get("page_size"))
        skip_source_ids: set[str] = set(params.get("skip_source_ids") or [])
        cursor = params.get("cursor") or {}
        start_page = self._to_int(cursor.get("page")) or 1
        next_page = start_page

        # Phase 1: search — collect all pages until API returns empty
        async with httpx.AsyncClient(
            headers=self._search_headers(cred), timeout=30.0, follow_redirects=True
        ) as search_client:
            for page in range(start_page, 10_000):
                next_page = page
                body = {
                    "page": page,
                    "per_page": page_size,
                    "filters": [
                        {"name": "keyword", "value": task.keyword},
                        {"name": "entstatus", "value": [1, 3]},
                    ],
                }
                resp = await self._request_with_retry(
                    search_client, "POST", f"{_SEARCH_BASE_URL}/api_skb/v1/search", json=body
                )
                if resp.status_code in (401, 403):
                    raise CredentialExpiredError(message="励销云 Token 已过期，请重新登录并更新凭证")
                if resp.status_code != 200:
                    logger.warning("Lixiaoyun search returned %s: %s", resp.status_code, resp.text[:200])
                    break
                raw_body = resp.json()
                items = self._extract_list(raw_body)
                # 调试：记录第一页的顶层结构，便于排查 _extract_list 解析失败
                if page == 1:
                    top_keys = list(raw_body.keys()) if isinstance(raw_body, dict) else type(raw_body).__name__
                    sample_item = items[0] if items else None
                    logger.info(
                        "Lixiaoyun search page=1 status=%s top_keys=%s items_found=%d sample=%s",
                        resp.status_code, top_keys, len(items),
                        str(sample_item)[:200] if sample_item else "NONE",
                    )
                if not items:
                    break
                items = [
                    item for item in items
                    if str(item.get("id") or "") not in skip_source_ids
                ]
                raw_items.extend(items)
                if len(raw_items) >= max_competitors:
                    raw_items = raw_items[:max_competitors]
                    next_page = page + 1
                    break
                next_page = page + 1

        if not raw_items:
            payload.cursor = {"page": next_page}
            payload.skip_source_ids = sorted(skip_source_ids)
            return payload

        collected_source_ids = {
            str(item.get("id") or "")
            for item in raw_items
            if str(item.get("id") or "")
        }
        payload.cursor = {"page": next_page}
        payload.skip_source_ids = sorted(skip_source_ids | collected_source_ids)

        # Save basic search results immediately before enrichment (allows early persistence)
        if task.on_partial:
            basic = [self._map_basic(item, task.keyword) for item in raw_items]
            await task.on_partial(basic)

        # Phase 2: enrich each company; save immediately as each one completes
        semaphore = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        async with httpx.AsyncClient(
            headers=self._detail_headers(cred), timeout=30.0, follow_redirects=True
        ) as detail_client:
            async with httpx.AsyncClient(
                headers=self._search_headers(cred), timeout=30.0, follow_redirects=True
            ) as contact_client:
                enrich_tasks = [
                    self._enrich_and_notify(
                        detail_client, contact_client, semaphore,
                        item, task.keyword, task.on_company_enriched,
                    )
                    for item in raw_items
                ]
                results = await asyncio.gather(*enrich_tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Lixiaoyun enrichment failed for '%s': %s", raw_items[i].get("name"), result)
                payload.competitors.append(self._map_basic(raw_items[i], task.keyword))
            else:
                payload.competitors.append(result)

        return payload

    @staticmethod
    def _bounded_page_size(value: object) -> int:
        try:
            page_size = int(value or _DEFAULT_PAGE_SIZE)
        except (TypeError, ValueError):
            page_size = _DEFAULT_PAGE_SIZE
        return max(1, min(page_size, _MAX_PAGE_SIZE))

    @staticmethod
    def _to_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _map_basic(self, item: dict, keyword: str) -> dict:
        """Minimal competitor record from search result only (no detail API calls)."""
        name_cn = item.get("companyName") or item.get("entName") or item.get("name") or ""
        name_en = item.get("entNameEng") or ""
        # 搜索结果的 esdate 可能是毫秒时间戳，统一转为 YYYY-MM-DD
        esdate = self._parse_date(item.get("esdate"))
        # 搜索结果可能直接含地址字段（address / regAddress）
        reg_address = (
            item.get("address") or item.get("regAddress") or
            item.get("registeredAddress") or ""
        )
        legalperson = item.get("legalperson") or item.get("legalPerson") or ""
        uncid = item.get("uncid") or item.get("socialCreditCode") or item.get("unifiedSocialCreditCode") or ""
        return {
            "target_table": "lixiaoyun_raw_companies",
            "task_id": None,
            "source_id": str(item.get("id") or ""),
            "name": name_cn,
            "company_name_en": name_en,
            "domain": item.get("officialWebsite") or item.get("domain") or None,
            "esdate": esdate,
            "legalperson": legalperson,
            "uncid": uncid,
            "reg_capital": "",
            "employee_scale": "",
            "reg_address": reg_address,
            "source_type": self.source_type,
            "reason": f"搜索关键词: {keyword}",
            "raw_payload": {
                **item,
                # 规范化别名，供前端统一访问
                "name_cn": name_cn,
                "name_en": name_en,
                "keyword": keyword,
                # 覆盖原始 esdate（毫秒时间戳 → YYYY-MM-DD）
                "esdate": esdate,
                "reg_address": reg_address,
                "legalperson": legalperson,
                "uncid": uncid,
            },
        }

    async def _enrich_and_notify(
        self,
        detail_client: httpx.AsyncClient,
        contact_client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        item: dict,
        keyword: str,
        on_company_enriched,
    ) -> dict:
        result = await self._enrich(detail_client, contact_client, semaphore, item, keyword)
        if on_company_enriched:
            await on_company_enriched(result)
        return result

    async def _enrich(
        self,
        detail_client: httpx.AsyncClient,
        contact_client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        item: dict,
        keyword: str,
    ) -> dict:
        company_id = str(item.get("id") or "")
        company_name = item.get("companyName") or item.get("name") or ""

        async with semaphore:
            base_info_raw, dev_info_raw, biz_card_raw, contacts_raw = await asyncio.gather(
                self._fetch_section(detail_client, company_id, "BaseInfo"),
                self._fetch_section(detail_client, company_id, "Development"),
                self._fetch_biz_card(detail_client, company_id),
                self._fetch_contacts(contact_client, company_id, company_name),
            )

        gs_info = self._first_dict(
            base_info_raw,
            ("GSInfo", "gsInfo"),
            ("GSInfo",),
            ("gsInfo",),
        )
        name_en = gs_info.get("entNameEng") or ""
        reg_address = gs_info.get("address") or ""
        reg_capital = gs_info.get("regCapDisplay") or ""
        paid_capital = gs_info.get("regccap") or ""
        legalperson = gs_info.get("legalperson") or item.get("legalperson") or ""
        uncid = gs_info.get("uncid") or item.get("uncid") or item.get("socialCreditCode") or ""

        esdate = self._parse_date(item.get("esdate"))

        b2b_info = self._first_dict(
            dev_info_raw,
            ("B2B", "b2b", "B2BInfo", "b2bInfo"),
            ("B2B", "B2BInfo", "b2bInfo"),
            ("B2B", "B2BInfo"),
            ("B2B", "b2bInfo"),
            ("B2B",),
            ("b2b",),
            ("B2BInfo",),
            ("b2bInfo",),
        )
        employee_scale = b2b_info.get("scale") or ""

        contact_address = biz_card_raw.get("contactaddress") or ""

        return {
            "target_table": "lixiaoyun_raw_companies",
            "task_id": None,
            "source_id": company_id,
            "name": company_name,
            "company_name_en": name_en,
            "domain": item.get("officialWebsite") or None,
            "esdate": esdate,
            "legalperson": legalperson,
            "uncid": uncid,
            "reg_capital": reg_capital,
            "employee_scale": employee_scale,
            "reg_address": reg_address,
            "source_type": self.source_type,
            "reason": f"搜索关键词: {keyword}",
            "raw_payload": {
                **item,
                # 覆盖/规范化字段
                "esdate": esdate,
                "legalperson": legalperson,
                "reg_capital": reg_capital,
                "paid_capital": paid_capital,
                "reg_address": reg_address,
                "contact_address": contact_address,
                "employee_scale": employee_scale,
                "uncid": uncid,
                "lx_contacts": contacts_raw,
                # 规范化别名，供前端统一访问
                "name_cn": company_name,
                "name_en": name_en,
                "keyword": keyword,
                "contacts": contacts_raw,
                "contacts_count": len(contacts_raw),
            },
        }

    async def _fetch_section(
        self, client: httpx.AsyncClient, company_id: str, section: str
    ) -> dict:
        if not company_id:
            return {}
        try:
            resp = await self._request_with_retry(
                client, "GET",
                f"{_DETAIL_BASE_URL}/api_skb/v1/companyDetail/sectionInfo",
                params={"id": company_id, "section": section, "pageSize": 10},
            )
            if resp.status_code != 200:
                logger.debug("Lixiaoyun detail %s/%s returned %s", company_id, section, resp.status_code)
                return {}
            body = resp.json()
            return body.get("data") or body
        except Exception as exc:
            logger.warning("Lixiaoyun detail fetch %s/%s failed: %s", company_id, section, exc)
            return {}

    async def _fetch_biz_card(
        self, client: httpx.AsyncClient, company_id: str
    ) -> dict:
        if not company_id:
            return {}
        try:
            resp = await self._request_with_retry(
                client, "GET",
                f"{_DETAIL_BASE_URL}/api_skb/v1/companyDetail/bizCard",
                params={"id": company_id},
            )
            if resp.status_code != 200:
                logger.debug("Lixiaoyun bizCard %s returned %s", company_id, resp.status_code)
                return {}
            body = resp.json()
            return body.get("data") or body
        except Exception as exc:
            logger.warning("Lixiaoyun bizCard %s failed: %s", company_id, exc)
            return {}

    async def _fetch_contacts(
        self, client: httpx.AsyncClient, company_id: str, company_name: str
    ) -> list[dict]:
        if not company_id:
            return []
        try:
            await asyncio.sleep(_CONTACTS_DELAY)
            resp = await self._request_with_retry(
                client, "GET",
                f"{_SEARCH_BASE_URL}/api_skb/v1/clue/contacts",
                params={"pid": company_id, "entName": company_name, "source": "list"},
            )
            if resp.status_code != 200:
                logger.debug("Lixiaoyun contacts %s returned %s", company_id, resp.status_code)
                return []
            body = resp.json()
            data = body.get("data") or []
            raw_contacts = data if isinstance(data, list) else (
                data.get("contacts") or data.get("list") or data.get("records") or []
            )
            return [self._normalize_contact(c) for c in raw_contacts if isinstance(c, dict)]
        except Exception as exc:
            logger.warning("Lixiaoyun contacts %s failed: %s", company_id, exc)
            return []

    def _normalize_contact(self, c: dict) -> dict:
        return {
            "name": self._pick(
                c, "name", "contactName", "contact_name", "contact_person", "contactPerson", "personName",
                "contact",
            ),
            "phone": self._pick(
                c, "phone", "mobile", "mobilePhone", "mobile_phone", "tel", "telephone", "phoneNumber",
                "content",
            ),
            "position": self._pick(
                c, "position", "title", "job", "jobTitle", "job_title", "positionName", "position_name",
                "positionContent",
            ),
            "email": self._pick(c, "email", "mail", "emailAddress", "email_address"),
        }

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        last_timeout: httpx.TimeoutException | None = None
        for attempt in range(_RETRY_MAX + 1):
            try:
                resp = await client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                last_timeout = exc
                if attempt == _RETRY_MAX:
                    logger.warning("Timed out after %d retries: %s", _RETRY_MAX, url)
                    raise
                wait = _RETRY_BASE ** attempt
                logger.info(
                    "Lixiaoyun request timed out, waiting %.1fs before retry %d/%d: %s",
                    wait,
                    attempt + 1,
                    _RETRY_MAX,
                    url,
                )
                await asyncio.sleep(wait)
                continue
            if resp.status_code != 429:
                return resp
            if attempt == _RETRY_MAX:
                logger.warning("Rate limited (429) after %d retries: %s", _RETRY_MAX, url)
                return resp
            wait = float(resp.headers.get("Retry-After") or 0) or (_RETRY_BASE ** attempt)
            logger.info("Rate limited (429), waiting %.1fs before retry %d/%d", wait, attempt + 1, _RETRY_MAX)
            await asyncio.sleep(wait)
        if last_timeout is not None:
            raise last_timeout
        return resp  # unreachable but satisfies type checker

    def _parse_date(self, value) -> str:
        """Convert ms timestamp or date string to YYYY-MM-DD. Returns empty string on failure."""
        if not value:
            return ""
        try:
            if isinstance(value, (int, float)) and value > 1e10:
                from datetime import datetime, timezone, timedelta
                cst = timezone(timedelta(hours=8))
                return datetime.fromtimestamp(value / 1000, tz=cst).strftime("%Y-%m-%d")
            return str(value)[:10]
        except Exception:
            return ""

    def _extract_list(self, body: dict) -> list[dict]:
        data = body.get("data") or body
        if isinstance(data, list):
            return data
        for key in ("records", "list", "items", "result", "companies", "resources"):
            if isinstance(data.get(key), list):
                return data[key]
        return []

    def _first_dict(self, data: dict, *paths: tuple[str, ...]) -> dict:
        for path in paths:
            found = self._dig_path(data, *path)
            if found:
                return found
        return {}

    def _dig_path(self, data: dict, *keys: str) -> dict | None:
        cur = data
        for key in keys:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
            if cur is None:
                return None
        return cur if isinstance(cur, dict) else None

    def _pick(self, data: dict, *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if value not in (None, ""):
                return str(value)
        return None
