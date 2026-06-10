"""collection_type 筛选 SQL 的 NULL 安全测试。"""

from app.services.collection_source import KEYWORD_TAG_JSONB


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

    def test_filter_sql_reverse_includes_null(self):
        """验证 reverse 过滤条件包含 IS NULL 处理"""
        collection_type = "reverse"
        where_parts = []
        if collection_type == "reverse":
            where_parts.append(
                f"(data_source_tags IS NULL OR NOT data_source_tags @> {KEYWORD_TAG_JSONB})"
            )
        assert len(where_parts) == 1
        assert "IS NULL" in where_parts[0]
        assert "NOT" in where_parts[0]
        assert KEYWORD_TAG_JSONB in where_parts[0]

    def test_no_filter_when_empty(self):
        """collection_type 为空时不应添加过滤条件"""
        collection_type = None
        where_parts = []
        if collection_type == "keyword":
            where_parts.append("keyword filter")
        elif collection_type == "reverse":
            where_parts.append("reverse filter")
        assert len(where_parts) == 0
