"""采集来源共享口径测试。"""

from app.services.collection_source import (
    KEYWORD_COLLECTION_TAG,
    KEYWORD_TAG_JSONB,
    compute_collection_type,
)


class TestCollectionSource:
    """验证 collection_type 判定函数和 SQL 片段常量。"""

    def test_keyword_tag_returns_keyword(self):
        """只有关键词采集标签时返回 keyword。"""
        assert compute_collection_type([KEYWORD_COLLECTION_TAG]) == "keyword"

    def test_keyword_tag_with_other_tags_returns_keyword(self):
        """同时包含其他来源标签时仍返回 keyword。"""
        assert compute_collection_type(["腾道", KEYWORD_COLLECTION_TAG]) == "keyword"

    def test_none_tags_returns_reverse(self):
        """data_source_tags 为 NULL 时返回 reverse。"""
        assert compute_collection_type(None) == "reverse"

    def test_empty_tags_returns_reverse(self):
        """data_source_tags 为空数组时返回 reverse。"""
        assert compute_collection_type([]) == "reverse"

    def test_other_tags_returns_reverse(self):
        """不包含关键词采集标签时返回 reverse。"""
        assert compute_collection_type(["精准反推数据"]) == "reverse"

    def test_keyword_tag_jsonb_literal(self):
        """SQL 片段使用 jsonb 包含表达式需要的字面量。"""
        assert KEYWORD_TAG_JSONB == """'["外贸通关键词采集"]'::jsonb"""
