"""采集来源口径的单一真源。"""

from collections.abc import Iterable

KEYWORD_COLLECTION_TAG = "外贸通关键词采集"
KEYWORD_TAG_JSONB = """'["外贸通关键词采集"]'::jsonb"""


def compute_collection_type(data_source_tags: Iterable[str] | None) -> str:
    """包含关键词采集标签返回 keyword，否则返回 reverse。"""
    if data_source_tags is None:
        return "reverse"
    return "keyword" if KEYWORD_COLLECTION_TAG in data_source_tags else "reverse"
