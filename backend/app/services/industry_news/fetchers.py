"""按动态源策略解析标题 + 链接。

同步解析（feedparser / selectolax）由调用方放进 ``asyncio.to_thread``。
HTTP 客户端通过 ``transport`` 注入，单测用 ``httpx.MockTransport``。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any
from urllib.parse import urljoin

import feedparser
import httpx
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT_SECONDS = 20.0
RETRY_ATTEMPTS = 2  # 瞬时错误额外重试次数，合计最多 3 次请求
_ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_WS_RE = re.compile(r"\s+")


@dataclass(slots=True, frozen=True)
class RawItem:
    title: str
    url: str
    published_at: datetime | None = None


class FetchError(Exception):
    """抓取或解析失败。"""


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _from_struct_time(parsed: struct_time | None) -> datetime | None:
    if parsed is None:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _parse_datetime(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return _as_aware(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return _as_aware(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        pass
    try:
        return _as_aware(parsedate_to_datetime(text))
    except (TypeError, ValueError, OverflowError):
        return None


def _href_allowed(href: str, parse_config: dict[str, Any]) -> bool:
    pattern = parse_config.get("href_pattern")
    exclude = parse_config.get("href_exclude")
    if pattern and not re.search(pattern, href):
        return False
    return not (exclude and re.search(exclude, href))


def _clean_text(value: str | None) -> str:
    """合并空白并去零宽字符（慕尼黑两站 JSON-LD 名称带零宽字符）。"""
    return _WS_RE.sub(" ", _ZERO_WIDTH_RE.sub("", value or "")).strip()


def parse_rss(body: str) -> list[RawItem]:
    feed = feedparser.parse(body)
    items: list[RawItem] = []
    for entry in feed.entries:
        title = _clean_text(getattr(entry, "title", "") or "")
        link = _clean_text(getattr(entry, "link", "") or "")
        if not title or not link:
            continue
        published = _from_struct_time(getattr(entry, "published_parsed", None))
        if published is None:
            published = _from_struct_time(getattr(entry, "updated_parsed", None))
        if published is None:
            published = _parse_datetime(
                getattr(entry, "published", None) or getattr(entry, "updated", None)
            )
        items.append(RawItem(title=title, url=link, published_at=published))
    return items


def _title_from_node(node, parse_config: dict[str, Any]) -> str:
    title_selector = parse_config.get("title_selector")
    if title_selector:
        found = node.css_first(title_selector)
        if found is not None:
            return _clean_text(found.text())
    if parse_config.get("title_from") == "parent":
        parent = node.parent
        if parent is not None:
            return _clean_text(parent.text())
    return _clean_text(node.text())


def _href_from_node(node, parse_config: dict[str, Any], base_url: str) -> str:
    link_selector = parse_config.get("link_selector")
    target = node.css_first(link_selector) if link_selector else node
    if target is None:
        target = node
    href = target.attributes.get("href") if target is not None else None
    if not href:
        return ""
    return urljoin(base_url, href.strip())


def parse_html(body: str, *, base_url: str, parse_config: dict[str, Any]) -> list[RawItem]:
    tree = HTMLParser(body)
    selector = parse_config.get("item_selector") or "a"
    items: list[RawItem] = []
    seen: set[str] = set()
    for node in tree.css(selector):
        href = _href_from_node(node, parse_config, base_url)
        if not href or not _href_allowed(href, parse_config):
            continue
        title = _title_from_node(node, parse_config)
        if not title:
            continue
        key = href
        if key in seen:
            continue
        seen.add(key)
        items.append(RawItem(title=title, url=href, published_at=None))
    return items


def _walk_jsonld(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            found.extend(_walk_jsonld(item))
        return found
    if not isinstance(payload, dict):
        return found
    types = payload.get("@type")
    type_set = {types} if isinstance(types, str) else set(types or [])
    if "ItemList" in type_set:
        for element in payload.get("itemListElement") or []:
            if isinstance(element, dict):
                item = element.get("item") or element
                if isinstance(item, dict):
                    found.append(item)
    found.extend(_walk_jsonld(payload.get("@graph")))
    return found


def parse_jsonld(body: str, *, base_url: str, parse_config: dict[str, Any]) -> list[RawItem]:
    tree = HTMLParser(body)
    items: list[RawItem] = []
    seen: set[str] = set()
    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text() or ""
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for entry in _walk_jsonld(payload):
            name = _clean_text(str(entry.get("name") or ""))
            url = str(entry.get("url") or "").strip()
            if not name or not url:
                continue
            absolute = urljoin(base_url, url)
            if not _href_allowed(absolute, parse_config):
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            items.append(
                RawItem(
                    title=name,
                    url=absolute,
                    published_at=_parse_datetime(
                        entry.get("datePublished") or entry.get("dateCreated")
                    ),
                )
            )
    return items


def parse_body(
    strategy: str,
    body: str,
    *,
    source_url: str,
    parse_config: dict[str, Any] | None,
) -> list[RawItem]:
    config = parse_config or {}
    if strategy == "rss":
        return parse_rss(body)
    if strategy == "html":
        return parse_html(body, base_url=source_url, parse_config=config)
    if strategy == "jsonld":
        return parse_jsonld(body, base_url=source_url, parse_config=config)
    raise FetchError(f"未知解析策略: {strategy}")


class IndustryNewsFetcher:
    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = HTTP_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.transport = transport
        self.timeout = timeout
        self.user_agent = user_agent

    async def fetch_items(self, source: dict[str, Any]) -> list[RawItem]:
        url = source["url"]
        strategy = source["strategy"]
        parse_config = source.get("parse_config") or {}
        body = await self._get_text(url)
        return await asyncio.to_thread(
            parse_body, strategy, body, source_url=url, parse_config=parse_config
        )

    async def _get_text(self, url: str) -> str:
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        last_error: Exception | None = None
        attempts = 1 + RETRY_ATTEMPTS
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=headers,
            transport=self.transport,
        ) as client:
            for attempt in range(attempts):
                try:
                    response = await client.get(url)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise FetchError(f"请求失败: {url}") from exc
                    continue
                if 400 <= response.status_code < 500:
                    raise FetchError(f"源返回 {response.status_code}: {url}")
                if response.status_code >= 500:
                    last_error = FetchError(f"源返回 {response.status_code}: {url}")
                    if attempt + 1 >= attempts:
                        raise last_error
                    continue
                return response.text
        raise FetchError(f"请求失败: {url}") from last_error
