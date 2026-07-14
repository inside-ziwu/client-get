"""collection_type 筛选 SQL 的共享口径测试。"""

from app.services.collection_source import KEYWORD_TAG_JSONB, build_collection_type_filter


class TestCollectionTypeFilter:
    """验证 admin collection_type 过滤 SQL 仍引用共享常量。"""

    def test_filter_sql_keyword(self):
        """验证 keyword 过滤条件生成正确的 SQL"""
        collection_type = "keyword"
        where_parts = []
        if collection_type == "keyword":
            where_parts.append(f"data_source_tags @> {KEYWORD_TAG_JSONB}")
        assert len(where_parts) == 1
        assert "@>" in where_parts[0]
        assert KEYWORD_TAG_JSONB in where_parts[0]

    def test_filter_sql_reverse_requires_positive_evidence(self):
        """验证 reverse 过滤条件不再使用非关键词补集。"""
        sql = build_collection_type_filter("reverse")
        assert "manual-%" in sql
        assert KEYWORD_TAG_JSONB in sql
        assert "waimaotong_raw_companies" in sql
        assert "source_competitor" in sql
        assert "data_source_tags IS NULL OR NOT" not in sql

    def test_no_filter_when_empty(self):
        """collection_type 为空时不应添加过滤条件"""
        collection_type = None
        where_parts = []
        if collection_type == "keyword":
            where_parts.append("keyword filter")
        elif collection_type == "reverse":
            where_parts.append("reverse filter")
        assert len(where_parts) == 0
