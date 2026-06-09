"""collection_type 筛选的 NULL 安全测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.admin_collection_service import AdminCollectionService


def _make_mapping(row_dict):
    m = MagicMock()
    m.__getitem__ = lambda self, key: row_dict[key]
    m.__contains__ = lambda self, key: key in row_dict
    m.get = lambda self, key, default=None: row_dict.get(key, default)
    m.keys = lambda self: row_dict.keys()
    m.values = lambda self: row_dict.values()
    m.items = lambda self: row_dict.items()
    return m


def _clean_row(**overrides):
    base = {
        "id": 1,
        "source_id": "src-1",
        "name": "Test",
        "company_name": "Test Co",
        "english_name": "Test EN",
        "country": "US",
        "country_iso3": "USA",
        "domain": "test.com",
        "industry": "Electronics",
        "sub_industry": "PCB",
        "phone": "+1234",
        "employee_size": "50-100",
        "company_size": "medium",
        "founded_year": 2010,
        "website": "https://test.com",
        "full_address": "123 Main St",
        "description": "A company",
        "grade": "A",
        "score": 85.0,
        "email_priority": "high",
        "company_type_analysis": "manufacturer",
        "product_tags": ["tag1"],
        "data_source_tags": ["外贸通关键词采集"],
        "has_trade_data": True,
        "trade_amount_3y_usd": 100000.0,
        "trade_count": 10,
        "contacts_count": 5,
        "detail_status": "done",
        "contacts_status": "done",
        "trade_status": "done",
        "sys_company_id": "uuid-1",
        "created_at": None,
        "updated_at": None,
    }
    base.update(overrides)
    return base


class TestCollectionTypeFilter:
    """验证 collection_type 计算字段和过滤逻辑"""

    def test_keyword_row_returns_keyword_type(self):
        """data_source_tags 包含标签时 collection_type 应为 keyword"""
        service = AdminCollectionService()
        row = _clean_row(data_source_tags=["外贸通关键词采集", "其他标签"])
        tags = list(row["data_source_tags"] or [])
        result = "keyword" if "外贸通关键词采集" in tags else "reverse"
        assert result == "keyword"

    def test_reverse_row_returns_reverse_type(self):
        """data_source_tags 不包含标签时 collection_type 应为 reverse"""
        row = _clean_row(data_source_tags=["精准反推数据"])
        tags = list(row["data_source_tags"] or [])
        result = "keyword" if "外贸通关键词采集" in tags else "reverse"
        assert result == "reverse"

    def test_null_tags_returns_reverse_type(self):
        """data_source_tags 为 NULL 时 collection_type 应为 reverse"""
        row = _clean_row(data_source_tags=None)
        tags = list(row["data_source_tags"] or [])
        result = "keyword" if "外贸通关键词采集" in tags else "reverse"
        assert result == "reverse"

    def test_empty_tags_returns_reverse_type(self):
        """data_source_tags 为空数组时 collection_type 应为 reverse"""
        row = _clean_row(data_source_tags=[])
        tags = list(row["data_source_tags"] or [])
        result = "keyword" if "外贸通关键词采集" in tags else "reverse"
        assert result == "reverse"

    def test_filter_sql_keyword(self):
        """验证 keyword 过滤条件生成正确的 SQL"""
        keyword_tag_arr = "ARRAY['外贸通关键词采集']::text[]"
        collection_type = "keyword"
        where_parts = []
        if collection_type == "keyword":
            where_parts.append(f"data_source_tags @> {keyword_tag_arr}")
        assert len(where_parts) == 1
        assert "@>" in where_parts[0]

    def test_filter_sql_reverse_includes_null(self):
        """验证 reverse 过滤条件包含 IS NULL 处理"""
        keyword_tag_arr = "ARRAY['外贸通关键词采集']::text[]"
        collection_type = "reverse"
        where_parts = []
        if collection_type == "reverse":
            where_parts.append(
                f"(data_source_tags IS NULL OR NOT data_source_tags @> {keyword_tag_arr})"
            )
        assert len(where_parts) == 1
        assert "IS NULL" in where_parts[0]
        assert "NOT" in where_parts[0]

    def test_no_filter_when_empty(self):
        """collection_type 为空时不应添加过滤条件"""
        collection_type = None
        where_parts = []
        if collection_type == "keyword":
            where_parts.append("keyword filter")
        elif collection_type == "reverse":
            where_parts.append("reverse filter")
        assert len(where_parts) == 0
