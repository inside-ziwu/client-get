"""情报文章序列化：published_at 与 published_to_tenant_at 必须各取各的列。

历史 bug：SELECT 中 p.created_at AS published_at 与 a.published_at 同名，
mappings 后者覆盖前者，published_to_tenant_at 恒等于文章原始发布时间。
"""

import inspect
from datetime import datetime, timezone

from app.services.intelligence_service import IntelligenceService

ARTICLE_PUBLISHED_AT = datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc)
PUBLISHED_TO_TENANT_AT = datetime(2026, 7, 20, 9, 30, 0, tzinfo=timezone.utc)


def _row() -> dict:
    return {
        "publication_id": "pub-001",
        "publication_status": "unread",
        "has_summary": False,
        "read_at": None,
        "published_to_tenant_at": PUBLISHED_TO_TENANT_AT,
        "article_id": "art-001",
        "article_created_at": datetime(2026, 7, 1, 8, 0, 0, tzinfo=timezone.utc),
        "title": "t",
        "url": None,
        "author": None,
        "published_at": ARTICLE_PUBLISHED_AT,
        "content_summary": None,
        "ai_category": None,
        "ai_tags": [],
        "ai_relevance_score": None,
    }


class TestArticleSerialization:
    def test_two_timestamps_come_from_distinct_columns(self):
        item = IntelligenceService()._serialize_article(_row())
        assert item["published_at"] == ARTICLE_PUBLISHED_AT.isoformat()
        assert item["published_to_tenant_at"] == PUBLISHED_TO_TENANT_AT.isoformat()
        assert item["published_at"] != item["published_to_tenant_at"]

    def test_sql_has_no_duplicate_published_at_alias(self):
        source = inspect.getsource(IntelligenceService)
        assert "AS published_at" not in source, "p.created_at 别名不得与 a.published_at 同名"
