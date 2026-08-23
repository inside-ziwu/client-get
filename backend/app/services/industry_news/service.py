"""行业动态：抓取入库、租户列表、管理端启停。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.errors import AppError
from app.core.ids import new_uuid
from app.services.industry_news.fetchers import IndustryNewsFetcher, RawItem
from app.services.industry_news.normalize import canonical_url, dedup_key, truncate_title
from app.utils.industry import canonical_industry

logger = logging.getLogger(__name__)

ADVISORY_LOCK_KEY = 2_026_082_401
WINDOW_DAYS = 90

_SQL_LOCK = text(
    "SELECT pg_try_advisory_xact_lock(CAST(:key AS bigint) + pg_catalog.hashtext(:instance_id))"
)
_SQL_ACTIVE_SOURCES = text(
    """
    SELECT id, instance_id, industry, code, name, url, category, lang, strategy,
           parse_config, is_active, last_fetched_at, last_success_at, error_count
    FROM industry_news_sources
    WHERE instance_id = :instance_id AND is_active = true
    ORDER BY name, id
    """
)
_SQL_ALL_SOURCES = text(
    """
    SELECT id, instance_id, industry, code, name, url, category, lang, strategy,
           parse_config, is_active, last_fetched_at, last_success_at, error_count
    FROM industry_news_sources
    WHERE instance_id = :instance_id
    ORDER BY name, id
    """
)
_SQL_INSERT_ITEM = text(
    """
    INSERT INTO industry_news_items (
      id, instance_id, source_id, title, url, canonical_url, dedup_key,
      published_at, fetched_at
    ) VALUES (
      CAST(:id AS uuid), :instance_id, CAST(:source_id AS uuid), :title, :url,
      :canonical_url, :dedup_key, :published_at, :fetched_at
    )
    ON CONFLICT DO NOTHING
    """
)
_SQL_MARK_SUCCESS = text(
    """
    UPDATE industry_news_sources
    SET last_fetched_at = :run_at,
        last_success_at = :run_at,
        error_count = 0
    WHERE id = CAST(:id AS uuid) AND instance_id = :instance_id
    """
)
_SQL_MARK_ERROR = text(
    """
    UPDATE industry_news_sources
    SET last_fetched_at = :run_at,
        error_count = error_count + 1
    WHERE id = CAST(:id AS uuid) AND instance_id = :instance_id
    """
)
_SQL_TENANT_INDUSTRY = text(
    "SELECT industry FROM tenants"
    " WHERE id = CAST(:tenant_id AS uuid) AND instance_id = :instance_id"
)
_LIST_WHERE = """
    i.instance_id = :instance_id AND s.industry = :industry AND s.is_active
      AND i.fetched_at >= :window_start
      AND (CAST(:categories AS text[]) IS NULL OR s.category = ANY(CAST(:categories AS text[])))
      AND (CAST(:source_ids AS uuid[]) IS NULL OR s.id = ANY(CAST(:source_ids AS uuid[])))
      AND (CAST(:lang AS text) IS NULL OR s.lang = CAST(:lang AS text))
      AND (NOT :unread_only OR r.item_id IS NULL)
"""
_SQL_LIST_ITEMS = text(
    f"""
    SELECT i.id, i.title, i.url, i.published_at, i.fetched_at,
           s.id AS source_id, s.name AS source_name, s.url AS source_url, s.category, s.lang,
           (r.item_id IS NOT NULL) AS is_read
    FROM industry_news_items i
    JOIN industry_news_sources s ON s.id = i.source_id
    LEFT JOIN industry_news_reads r
      ON r.item_id = i.id
     AND r.user_id = CAST(:user_id AS uuid)
     AND r.tenant_id = CAST(:tenant_id AS uuid)
    WHERE {_LIST_WHERE}
    ORDER BY i.fetched_at DESC, COALESCE(i.published_at, i.fetched_at) DESC, i.id DESC
    LIMIT :limit OFFSET :offset
    """
)
_SQL_LIST_COUNT = text(
    f"""
    SELECT count(*)
    FROM industry_news_items i
    JOIN industry_news_sources s ON s.id = i.source_id
    LEFT JOIN industry_news_reads r
      ON r.item_id = i.id
     AND r.user_id = CAST(:user_id AS uuid)
     AND r.tenant_id = CAST(:tenant_id AS uuid)
    WHERE {_LIST_WHERE}
    """
)
_SQL_FILTER_OPTIONS = text(
    """
    SELECT id, name, category, lang
    FROM industry_news_sources
    WHERE instance_id = :instance_id AND industry = :industry AND is_active = true
    ORDER BY name, id
    """
)
_SQL_VISIBLE_ITEM = text(
    """
    SELECT i.id
    FROM industry_news_items i
    JOIN industry_news_sources s ON s.id = i.source_id
    WHERE i.id = CAST(:item_id AS uuid)
      AND i.instance_id = :instance_id AND s.industry = :industry AND s.is_active
      AND i.fetched_at >= :window_start
    """
)
_SQL_MARK_READ = text(
    """
    INSERT INTO industry_news_reads (tenant_id, user_id, item_id)
    VALUES (CAST(:tenant_id AS uuid), CAST(:user_id AS uuid), CAST(:item_id AS uuid))
    ON CONFLICT (user_id, item_id) DO NOTHING
    """
)
_SQL_SET_ACTIVE = text(
    """
    UPDATE industry_news_sources
    SET is_active = :is_active
    WHERE id = CAST(:id AS uuid) AND instance_id = :instance_id
    RETURNING id, instance_id, industry, code, name, url, category, lang, strategy,
              parse_config, is_active, last_fetched_at, last_success_at, error_count
    """
)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _window_start(now: datetime) -> datetime:
    return now - timedelta(days=WINDOW_DAYS)


def _empty_filters() -> dict[str, Any]:
    return {"categories": [], "sources": [], "langs": [], "has_sources": False}


def _empty_stats(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": str(source["id"]),
        "name": source["name"],
        "fetched": 0,
        "inserted": 0,
        "duplicate": 0,
        "skipped_old": 0,
        "skipped_invalid": 0,
        "ok": False,
    }


class IndustryNewsService:
    def __init__(self, *, fetcher: IndustryNewsFetcher | None = None) -> None:
        self.fetcher = fetcher or IndustryNewsFetcher()

    async def resolve_tenant_industry(
        self, conn: AsyncConnection, tenant_id: str, instance_id: str
    ) -> str | None:
        """平台级表 tenants 必须同时过滤 instance_id（AGENTS.md §1）。"""
        result = await conn.execute(
            _SQL_TENANT_INDUSTRY, {"tenant_id": tenant_id, "instance_id": instance_id}
        )
        row = result.mappings().first()
        if row is None:
            raise AppError(code="NOT_FOUND", message="租户不存在", status_code=404)
        return canonical_industry(row["industry"])

    async def fetch_source(
        self,
        conn: AsyncConnection,
        source: dict[str, Any],
        *,
        run_at: datetime,
        items: list[RawItem],
    ) -> dict[str, Any]:
        """把已解析的条目入库并更新源健康。成功条件是解析出至少 1 条（含随后被过滤 / 去重的）。"""
        stats = _empty_stats(source)
        raw_items = items
        stats["fetched"] = len(raw_items)
        cutoff = _window_start(run_at)
        if not raw_items:
            await conn.execute(
                _SQL_MARK_ERROR,
                {"id": str(source["id"]), "instance_id": source["instance_id"], "run_at": run_at},
            )
            return stats

        for raw in raw_items:
            title = truncate_title(raw.title)
            url_key = canonical_url(raw.url)
            key = dedup_key(title)
            if not title or not url_key or not key:
                stats["skipped_invalid"] += 1
                continue
            published_at = raw.published_at
            if published_at is not None and published_at < cutoff:
                stats["skipped_old"] += 1
                continue
            result = await conn.execute(
                _SQL_INSERT_ITEM,
                {
                    "id": str(new_uuid()),
                    "instance_id": source["instance_id"],
                    "source_id": str(source["id"]),
                    "title": title,
                    "url": raw.url,
                    "canonical_url": url_key,
                    "dedup_key": key,
                    "published_at": published_at,
                    "fetched_at": run_at,
                },
            )
            if result.rowcount:
                stats["inserted"] += 1
            else:
                stats["duplicate"] += 1

        await conn.execute(
            _SQL_MARK_SUCCESS,
            {"id": str(source["id"]), "instance_id": source["instance_id"], "run_at": run_at},
        )
        stats["ok"] = True
        return stats

    async def _load_raw_items(self, source: dict[str, Any]) -> list[RawItem]:
        return await self.fetcher.fetch_items(source)

    async def fetch_source_from_network(
        self,
        conn: AsyncConnection,
        source: dict[str, Any],
        *,
        run_at: datetime,
    ) -> dict[str, Any]:
        try:
            items = await self._load_raw_items(source)
        except Exception as exc:
            logger.exception(
                "industry_news: 源失败 source=%s",
                source.get("name") or source.get("id"),
            )
            await conn.execute(
                _SQL_MARK_ERROR,
                {"id": str(source["id"]), "instance_id": source["instance_id"], "run_at": run_at},
            )
            return {**_empty_stats(source), "error": str(exc)}
        return await self.fetch_source(conn, source, run_at=run_at, items=items)

    async def run_once(
        self,
        engine: AsyncEngine,
        *,
        instance_id: str,
        clock: Callable[[], datetime] | None = None,
        source_name: str | None = None,
    ) -> dict[str, Any]:
        now = clock() if clock is not None else datetime.now(UTC)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock 必须返回 timezone-aware datetime")
        async with engine.begin() as conn:
            locked = await conn.scalar(
                _SQL_LOCK, {"key": ADVISORY_LOCK_KEY, "instance_id": instance_id}
            )
            if not locked:
                return {"skipped": True, "reason": "in_progress"}
            result = await conn.execute(_SQL_ACTIVE_SOURCES, {"instance_id": instance_id})
            sources = [dict(row) for row in result.mappings().all()]
            if source_name:
                sources = [row for row in sources if row["name"] == source_name]
            if not sources:
                return {
                    "skipped": False,
                    "reason": "no_sources",
                    "run_at": now.isoformat(),
                    "sources": [],
                }
            source_stats: list[dict[str, Any]] = []
            for source in sources:
                try:
                    async with conn.begin_nested():
                        stats = await self.fetch_source_from_network(conn, source, run_at=now)
                except Exception:
                    logger.exception(
                        "industry_news: 源 savepoint 失败 source=%s",
                        source.get("name"),
                    )
                    async with conn.begin_nested():
                        await conn.execute(
                            _SQL_MARK_ERROR,
                            {"id": str(source["id"]), "instance_id": instance_id, "run_at": now},
                        )
                    stats = _empty_stats(source)
                source_stats.append(stats)
            return {
                "skipped": False,
                "run_at": now.isoformat(),
                "source_count": len(source_stats),
                "ok_count": sum(1 for item in source_stats if item.get("ok")),
                "sources": source_stats,
            }

    def _list_params(
        self,
        *,
        tenant_id: str,
        user_id: str,
        instance_id: str,
        industry: str,
        categories: list[str] | None,
        source_ids: list[str] | None,
        lang: str | None,
        unread_only: bool,
        window_start: datetime,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "instance_id": instance_id,
            "industry": industry,
            "categories": categories or None,
            "source_ids": source_ids or None,
            "lang": lang or None,
            "unread_only": unread_only,
            "window_start": window_start,
        }
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return params

    def _serialize_item(self, row: Any) -> dict[str, Any]:
        url = row["url"]
        source_url = row["source_url"]
        target_domain = urlparse(url).netloc.lower()
        source_domain = urlparse(source_url).netloc.lower()
        time_value = row["published_at"] or row["fetched_at"]
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "url": url,
            "source_id": str(row["source_id"]),
            "source_name": row["source_name"],
            "category": row["category"],
            "lang": row["lang"],
            "time": _iso(time_value),
            "is_read": bool(row["is_read"]),
            "target_domain": target_domain,
            "is_external": target_domain != source_domain,
        }

    async def list_items(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        instance_id: str,
        categories: list[str] | None = None,
        source_ids: list[str] | None = None,
        lang: str | None = None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 50,
        now_utc: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        industry = await self.resolve_tenant_industry(conn, tenant_id, instance_id)
        if industry is None:
            return [], 0
        now = now_utc or datetime.now(UTC)
        params = self._list_params(
            tenant_id=tenant_id,
            user_id=user_id,
            instance_id=instance_id,
            industry=industry,
            categories=categories,
            source_ids=source_ids,
            lang=lang,
            unread_only=unread_only,
            window_start=_window_start(now),
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        rows = (await conn.execute(_SQL_LIST_ITEMS, params)).mappings().all()
        total = int(await conn.scalar(_SQL_LIST_COUNT, params) or 0)
        return [self._serialize_item(row) for row in rows], total

    async def list_filter_options(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        instance_id: str,
    ) -> dict[str, Any]:
        industry = await self.resolve_tenant_industry(conn, tenant_id, instance_id)
        if industry is None:
            return _empty_filters()
        rows = (
            (
                await conn.execute(
                    _SQL_FILTER_OPTIONS,
                    {"instance_id": instance_id, "industry": industry},
                )
            )
            .mappings()
            .all()
        )
        if not rows:
            return _empty_filters()
        categories = sorted({row["category"] for row in rows if row["category"]})
        langs = sorted({row["lang"] for row in rows if row["lang"]})
        sources = [{"id": str(row["id"]), "name": row["name"]} for row in rows]
        return {
            "categories": categories,
            "sources": sources,
            "langs": langs,
            "has_sources": True,
        }

    async def mark_read(
        self,
        conn: AsyncConnection,
        *,
        tenant_id: str,
        user_id: str,
        instance_id: str,
        item_id: str,
        now_utc: datetime | None = None,
    ) -> dict[str, Any]:
        industry = await self.resolve_tenant_industry(conn, tenant_id, instance_id)
        if industry is None:
            raise AppError(code="NOT_FOUND", message="动态不存在或无权访问", status_code=404)
        now = now_utc or datetime.now(UTC)
        visible = await conn.scalar(
            _SQL_VISIBLE_ITEM,
            {
                "item_id": item_id,
                "instance_id": instance_id,
                "industry": industry,
                "window_start": _window_start(now),
            },
        )
        if visible is None:
            raise AppError(code="NOT_FOUND", message="动态不存在或无权访问", status_code=404)
        await conn.execute(
            _SQL_MARK_READ,
            {"tenant_id": tenant_id, "user_id": user_id, "item_id": item_id},
        )
        return {"item_id": item_id, "is_read": True}

    def _serialize_source(self, row: Any) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "code": row["code"],
            "name": row["name"],
            "url": row["url"],
            "industry": row["industry"],
            "category": row["category"],
            "lang": row["lang"],
            "strategy": row["strategy"],
            "is_active": bool(row["is_active"]),
            "last_fetched_at": _iso(row["last_fetched_at"]),
            "last_success_at": _iso(row["last_success_at"]),
            "error_count": int(row["error_count"] or 0),
        }

    async def list_sources(self, conn: AsyncConnection, instance_id: str) -> list[dict[str, Any]]:
        rows = (await conn.execute(_SQL_ALL_SOURCES, {"instance_id": instance_id})).mappings().all()
        return [self._serialize_source(row) for row in rows]

    async def set_source_active(
        self,
        conn: AsyncConnection,
        *,
        instance_id: str,
        source_id: str,
        is_active: bool,
    ) -> dict[str, Any]:
        row = (
            (
                await conn.execute(
                    _SQL_SET_ACTIVE,
                    {"id": source_id, "instance_id": instance_id, "is_active": is_active},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise AppError(code="NOT_FOUND", message="动态源不存在或无权访问", status_code=404)
        return self._serialize_source(row)

    async def lock_is_free(self, conn: AsyncConnection, instance_id: str) -> bool:
        """探测实例级事务锁是否空闲；锁随调用方事务结束自动释放，只用于「立即抓取」的诚实回答。"""
        params = {"key": ADVISORY_LOCK_KEY, "instance_id": instance_id}
        return bool(await conn.scalar(_SQL_LOCK, params))

    async def count_active_sources(self, conn: AsyncConnection, instance_id: str) -> int:
        value = await conn.scalar(
            text(
                "SELECT count(*) FROM industry_news_sources "
                "WHERE instance_id = :instance_id AND is_active = true"
            ),
            {"instance_id": instance_id},
        )
        return int(value or 0)
