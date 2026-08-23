from pathlib import Path

import httpx
import pytest

from app.services.industry_news.fetchers import FetchError, IndustryNewsFetcher

FIXTURES = Path(__file__).parent / "fixtures" / "industry_news"
SEED = Path(__file__).parents[1] / "app" / "data" / "industry_news_sources_pcb.json"


def _load_seed() -> dict[str, dict]:
    import json

    rows = json.loads(SEED.read_text(encoding="utf-8"))
    return {row["code"]: row for row in rows}


def _fixture_for(code: str) -> Path:
    html = FIXTURES / f"{code}.html"
    xml = FIXTURES / f"{code}.xml"
    if html.exists():
        return html
    return xml


@pytest.mark.asyncio
async def test_each_seed_source_parses_at_least_one_item():
    seed = _load_seed()
    assert len(seed) == 14

    def handler(request: httpx.Request) -> httpx.Response:
        for code, row in seed.items():
            if str(request.url) == row["url"]:
                body = _fixture_for(code).read_text(encoding="utf-8")
                content_type = "application/rss+xml" if row["strategy"] == "rss" else "text/html"
                return httpx.Response(200, text=body, headers={"content-type": content_type})
        return httpx.Response(404, text="missing")

    fetcher = IndustryNewsFetcher(transport=httpx.MockTransport(handler))
    for code, row in seed.items():
        items = await fetcher.fetch_items(row)
        assert items, code
        assert all(item.title and item.url for item in items), code


@pytest.mark.asyncio
async def test_html_joins_relative_links_and_href_pattern():
    seed = _load_seed()["iconnect007"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=(FIXTURES / "iconnect007.html").read_text())

    items = await IndustryNewsFetcher(transport=httpx.MockTransport(handler)).fetch_items(seed)
    assert items
    assert all(item.url.startswith("https://iconnect007.com/") for item in items)
    assert all("/article/" in item.url for item in items)


@pytest.mark.asyncio
async def test_pcb_update_uses_parent_title_and_href_exclude():
    seed = _load_seed()["pcb-update"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=(FIXTURES / "pcb-update.html").read_text())

    items = await IndustryNewsFetcher(transport=httpx.MockTransport(handler)).fetch_items(seed)
    assert items
    assert all("pcbupdate.com" not in item.url for item in items)
    assert all("mediakit" not in item.url.lower() for item in items)
    # 标题取所在段落全文，外链剪报指向第三方域名
    assert any(item.url.startswith("http") and "pcbupdate.com" not in item.url for item in items)
    assert all(len(item.title) > 20 for item in items)


@pytest.mark.asyncio
async def test_jsonld_filters_href_pattern_and_strips_zero_width():
    seed = dict(_load_seed()["productronica"])
    body = """<html><body>
<script type="application/ld+json">
{
  "@type": "ItemList",
  "itemListElement": [
    {"item": {"name": "Press \u200bRelease Keep",
     "url": "/en/trade-fair/press/press-releases/detail/keep/"}},
    {"item": {"name": "Other page", "url": "/en/trade-fair/press/"}}
  ]
}
</script>
</body></html>
"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    items = await IndustryNewsFetcher(transport=httpx.MockTransport(handler)).fetch_items(seed)
    assert len(items) == 1
    assert "\u200b" not in items[0].title
    assert items[0].title == "Press Release Keep"
    assert "/press-releases/detail/" in items[0].url
    assert items[0].url.startswith("https://productronica.com/")


@pytest.mark.asyncio
async def test_4xx_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, text="nope")

    fetcher = IndustryNewsFetcher(transport=httpx.MockTransport(handler))
    with pytest.raises(FetchError):
        await fetcher.fetch_items(
            {"url": "https://example.com/missing", "strategy": "rss", "parse_config": {}}
        )
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_5xx_retries_twice():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="busy")
        return httpx.Response(
            200,
            text=(FIXTURES / "pcea.xml").read_text(),
            headers={"content-type": "application/rss+xml"},
        )

    fetcher = IndustryNewsFetcher(transport=httpx.MockTransport(handler))
    items = await fetcher.fetch_items(
        {"url": "https://pcea.net/feed/", "strategy": "rss", "parse_config": {}}
    )
    assert items
    assert calls["n"] == 3
