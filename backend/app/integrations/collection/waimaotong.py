import asyncio
import hashlib
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.errors import AppError, CredentialExpiredError
from app.integrations.collection.base import CollectionPayload, CollectionProvider, CollectionTask
from app.utils.country import to_iso3

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://waimao.office.163.com/globalSearch/api/globalSearch/v1/search"
_DETAIL_URL = "https://waimao.office.163.com/globalSearch/api/globalSearch/v1/detail/new"
_CONTACT_URL = "https://waimao.office.163.com/globalSearch/api/globalSearch/getContactPage"
_DEFAULT_PAGE_SIZE = 100
_MIN_INTERVAL = 4.5
_RETRY_MAX = 2

_COMMON_PARAMS = {
    "_device": "chrome",
    "_system": "web",
    "_appName": "sirius-web-waimao",
    "_version": "1.361.4",
}


def _generate_sign(secret_key: str, params: dict) -> tuple[str, str]:
    """返回 (sign, timestamp)。params 是已包含公共参数的查询参数。"""
    ts = str(int(time.time() * 1000))
    sign_str = (
        secret_key
        + "".join(f"{k}={v}" for k, v in sorted(params.items()) if v not in (None, "", []))
        + secret_key
    )
    sign = hashlib.md5(sign_str.encode()).hexdigest().upper()
    return sign, ts


class WaiMaoTongCollectionProvider(CollectionProvider):
    source_type = "waimao_tong"

    def __init__(self, credentials: list[dict]) -> None:
        self._credentials = credentials

    async def collect(self, task: CollectionTask) -> CollectionPayload:
        cred = self._credential()
        params = task.params or {}
        max_pages = int(params.get("max_pages", 10))
        countries = self._countries(params.get("countries"))

        payload = CollectionPayload()
        seen_ids: set[str] = set()

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            page = 1
            companies_raw: list[dict] = []
            while page <= max_pages:
                data = await self._search(client, cred, task.keyword, countries, page)
                if data is None:
                    break

                pageable = data.get("pageableResult") or {}
                items = [item for item in pageable.get("data") or [] if isinstance(item, dict)]
                total = self._to_int(pageable.get("total")) or 0
                if not items:
                    break

                for item in items:
                    cid = self._company_id(item)
                    if not cid or cid in seen_ids:
                        continue
                    seen_ids.add(cid)
                    companies_raw.append(item)

                fetched = page * _DEFAULT_PAGE_SIZE
                if total and fetched >= total:
                    break
                page += 1
                await asyncio.sleep(random.uniform(3, 8))

            for item in companies_raw:
                cid = self._company_id(item)
                if not cid:
                    continue

                await asyncio.sleep(_MIN_INTERVAL)
                detail = await self._get_detail(client, cred, cid)

                await asyncio.sleep(_MIN_INTERVAL)
                contacts_raw = await self._get_contacts(client, cred, cid)

                payload.companies.append(self._build_company(item, detail))
                payload.contacts.extend(self._build_contacts(cid, contacts_raw))

        return payload

    def _credential(self) -> dict:
        for cred in self._credentials:
            if not cred.get("is_active", True):
                continue
            cookie = self._clean_text(cred.get("cookie"))
            secret_key = self._clean_text(cred.get("secret_key"))
            device_id = self._clean_text(cred.get("device_id")) or self._cookie_value(
                cookie, "_deviceId"
            )
            if cookie and secret_key and device_id:
                return {**cred, "cookie": cookie, "secret_key": secret_key, "device_id": device_id}

        raise AppError(
            code="NO_CREDENTIAL",
            message=(
                "外贸通数据源没有可用凭证，"
                "请在管理后台配置 Cookie 会话和签名密钥"
            ),
            status_code=503,
        )

    def _headers(self, cred: dict) -> dict:
        return {
            "Cookie": cred["cookie"],
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Origin": "https://waimao.office.163.com",
            "Referer": "https://waimao.office.163.com/",
        }

    def _signed_params(self, cred: dict, params: dict | None = None) -> dict:
        query = {
            **_COMMON_PARAMS,
            "_deviceId": cred["device_id"],
            **(params or {}),
        }
        sign, timestamp = _generate_sign(cred["secret_key"], query)
        return {**query, "sign": sign, "timestamp": timestamp}

    async def _search(
        self,
        client: httpx.AsyncClient,
        cred: dict,
        keyword: str,
        countries: list[str],
        page: int,
    ) -> dict | None:
        body = {
            "searchType": "product",
            "product": keyword,
            "page": page,
            "size": _DEFAULT_PAGE_SIZE,
            "country": countries,
            "hasEmail": True,
            "hasCustomsData": True,
            "hasDomain": True,
            "allMatchQuery": False,
            "filterCustomer": False,
            "filterEdm": False,
            "sortField": "default",
            "version": 1,
        }
        response = await self._request_json(client, "POST", _SEARCH_URL, cred=cred, json=body)
        data = response.get("data") if response else None
        return data if isinstance(data, dict) else None

    async def _get_detail(
        self,
        client: httpx.AsyncClient,
        cred: dict,
        company_id: str,
    ) -> dict:
        try:
            response = await self._request_json(
                client,
                "GET",
                _DETAIL_URL,
                cred=cred,
                params={"id": company_id, "product": "", "version": 1},
            )
        except AppError:
            raise
        except Exception as exc:
            logger.warning("WaiMaoTong detail failed for '%s': %s", company_id, exc)
            return {}

        if response is None:
            logger.warning("WaiMaoTong detail failed for '%s'", company_id)
            return {}
        data = response.get("data")
        return data if isinstance(data, dict) else {}

    async def _get_contacts(
        self,
        client: httpx.AsyncClient,
        cred: dict,
        company_id: str,
    ) -> list[dict]:
        try:
            response = await self._request_json(
                client,
                "POST",
                _CONTACT_URL,
                cred=cred,
                json={"id": company_id, "page": 1, "size": _DEFAULT_PAGE_SIZE, "isHidden": False},
            )
        except AppError:
            raise
        except Exception as exc:
            logger.warning("WaiMaoTong contacts failed for '%s': %s", company_id, exc)
            return []

        if response is None:
            logger.warning("WaiMaoTong contacts failed for '%s'", company_id)
            return []
        return self._extract_contacts(response)

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        cred: dict,
        params: dict | None = None,
        **kwargs,
    ) -> dict | None:
        resp = await self._request_with_retry(
            client, method, url, cred=cred, params=params, **kwargs
        )
        body = self._json_body(resp)

        if resp.status_code == 401:
            raise CredentialExpiredError(
                message="外贸通 Cookie 会话已过期，请重新登录并更新凭证"
            )

        if resp.status_code in (403, 429) or self._body_code(body) in {"403", "429", "RATE_LIMIT"}:
            raise self._rate_limited_error()

        if resp.status_code == 200 and body.get("success") is False:
            raise CredentialExpiredError(
                message=body.get("message") or "外贸通 Cookie 会话已过期"
            )

        if resp.status_code != 200:
            logger.warning("WaiMaoTong request returned %s for %s", resp.status_code, url)
            return None

        return body

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        cred: dict,
        params: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        for attempt in range(_RETRY_MAX + 1):
            resp = await client.request(
                method,
                url,
                params=self._signed_params(cred, params),
                headers=self._headers(cred),
                **kwargs,
            )
            if not self._is_rate_limited(resp):
                return resp
            if attempt == _RETRY_MAX:
                logger.warning("WaiMaoTong rate limited after %d retries: %s", _RETRY_MAX, url)
                raise self._rate_limited_error()
            wait = self._retry_after(resp) or 60.0
            logger.info(
                "WaiMaoTong rate limited, waiting %.1fs before retry %d/%d",
                wait,
                attempt + 1,
                _RETRY_MAX,
            )
            await asyncio.sleep(wait)
        return resp

    def _build_company(self, item: dict, detail: dict | None) -> dict:
        detail = detail or {}
        cid = self._company_id(item) or ""
        country = self._clean_text(item.get("country"))
        country_iso3 = to_iso3(country) if country else None
        domain = self._clean_text(
            detail.get("domain") or detail.get("website") or item.get("domain")
        )
        website = self._website(domain)
        products = self._products(detail.get("productList"))
        raw_payload = {**item, "_detail": detail}

        return {
            "target_table": "waimaotong_raw_companies",
            "collection_type": "direct_search",
            "source_type": self.source_type,
            "source_id": cid,
            "name": self._clean_text(item.get("name") or item.get("recommendShowName")),
            "country_iso3": country_iso3,
            "country": country_iso3,
            "domain": domain,
            "website": website,
            "industry": detail.get("industry"),
            "employee_size": detail.get("employeeSize"),
            "employee_num": detail.get("employeeSize"),
            "founded_year": detail.get("foundedYear"),
            "phone": detail.get("phone"),
            "overview": detail.get("overviewDescription"),
            "products": products,
            "address": detail.get("address") or detail.get("location"),
            "data_source": "外贸通",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": raw_payload,
            "raw_data": raw_payload,
        }

    def _build_contacts(self, company_id: str, contacts_raw: list[dict]) -> list[dict]:
        contacts: list[dict] = []
        for contact in contacts_raw:
            email = self._first_email(contact)
            contacts.append(
                {
                    "target_table": "waimaotong_raw_contacts",
                    "source_type": self.source_type,
                    "source_contact_id": self._clean_text(contact.get("id")),
                    "company_source_type": self.source_type,
                    "company_source_id": company_id,
                    "name": self._clean_text(contact.get("name")),
                    "position": self._clean_text(contact.get("position")),
                    "title": self._clean_text(contact.get("position")),
                    "email": email,
                    "raw_payload": contact,
                    "raw_data": contact,
                }
            )
        return contacts

    def _extract_contacts(self, response: dict) -> list[dict]:
        data = response.get("data")
        raw_contacts: Any
        if isinstance(data, list):
            raw_contacts = data
        elif isinstance(data, dict):
            raw_contacts = data.get("content") or data.get("list") or []
        else:
            raw_contacts = []
        return [contact for contact in raw_contacts if isinstance(contact, dict)]

    def _is_rate_limited(self, resp: httpx.Response) -> bool:
        if resp.status_code in (403, 429):
            return True
        body = self._json_body(resp)
        return self._body_code(body) in {"403", "429", "RATE_LIMIT"}

    def _json_body(self, resp: httpx.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    def _body_code(self, body: dict) -> str | None:
        code = body.get("code")
        if code is None:
            return None
        return str(code).upper()

    def _retry_after(self, resp: httpx.Response) -> float | None:
        value = resp.headers.get("Retry-After")
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _rate_limited_error(self) -> AppError:
        return AppError(
            code="RATE_LIMITED",
            message="外贸通请求被限流，请稍后重试",
            status_code=429,
        )

    def _company_id(self, item: dict) -> str | None:
        return self._clean_text(item.get("id") or item.get("domain"))

    def _countries(self, value: Any) -> list[str]:
        if value is None or value == "":
            return ["全球"]
        if isinstance(value, list):
            return value or ["全球"]
        return [str(value)]

    def _website(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith(("http://", "https://")):
            return value
        return f"https://{value}"

    def _products(self, value: Any) -> str | list | None:
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        return value

    def _first_email(self, contact: dict) -> str | None:
        emails = contact.get("emails") or []
        if isinstance(emails, list):
            for item in emails:
                if isinstance(item, dict):
                    email = self._clean_text(item.get("address"))
                else:
                    email = self._clean_text(item)
                if email:
                    return email
        return self._clean_text(contact.get("email"))

    def _cookie_value(self, cookie: str | None, key: str) -> str | None:
        if not cookie:
            return None
        for part in cookie.split(";"):
            name, _, value = part.strip().partition("=")
            if name == key:
                return value.strip() or None
        return None

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _to_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
