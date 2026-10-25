"""采集来源共享口径测试。"""

from app.services.collection_source import (
    INSTANTLY_COLLECTION_TAG,
    INSTANTLY_TAG_JSONB,
    KEYWORD_COLLECTION_TAG,
    KEYWORD_TAG_JSONB,
    TENGDAO_COLLECTION_TAG,
    build_collection_type_filter,
    compute_collection_type,
    compute_collection_types,
)


class TestCollectionSource:
    """验证 collection_type 判定函数和 SQL 片段常量。"""

    def test_keyword_tag_returns_keyword(self):
        """只有关键词采集标签时返回 keyword。"""
        assert compute_collection_type([KEYWORD_COLLECTION_TAG]) == "keyword"

    def test_keyword_tag_with_other_tags_returns_keyword(self):
        """同时包含其他来源标签时仍返回 keyword。"""
        assert compute_collection_type(["腾道", KEYWORD_COLLECTION_TAG]) == "keyword"

    def test_manual_source_has_highest_priority(self):
        """manual source_id 即使同时存在其他证据也必须返回 manual。"""
        assert (
            compute_collection_type(
                [KEYWORD_COLLECTION_TAG, TENGDAO_COLLECTION_TAG],
                source_id="manual-123",
                has_source_competitor=True,
            )
            == "manual"
        )

    def test_keyword_has_priority_over_reverse_evidence(self):
        """关键词标签优先于腾道标签和反推公司证据。"""
        assert (
            compute_collection_type(
                [KEYWORD_COLLECTION_TAG, TENGDAO_COLLECTION_TAG],
                has_source_competitor=True,
            )
            == "keyword"
        )

    def test_tengdao_tag_returns_reverse(self):
        """显式腾道标签属于精准反推。"""
        assert compute_collection_type([TENGDAO_COLLECTION_TAG]) == "reverse"

    def test_source_competitor_returns_reverse(self):
        """非空 source_competitor 证据属于精准反推。"""
        assert compute_collection_type([], has_source_competitor=True) == "reverse"

    def test_missing_positive_evidence_returns_unknown(self):
        """NULL、空数组和无关标签不得再被反向推断为 reverse。"""
        assert compute_collection_type(None) == "unknown"
        assert compute_collection_type([]) == "unknown"
        assert compute_collection_type(["精准反推数据"]) == "unknown"

    def test_instantly_does_not_change_primary_type(self):
        """Instantly 不参与单值优先级，评分依赖的 collection_type 不变。"""
        assert compute_collection_type([INSTANTLY_COLLECTION_TAG]) == "unknown"
        tags = [TENGDAO_COLLECTION_TAG, INSTANTLY_COLLECTION_TAG]
        assert compute_collection_type(tags) == "reverse"

    def test_collection_types_appends_instantly(self):
        """多标签时列出全部类型；只有 Instantly 时不再显示 unknown。"""
        assert compute_collection_types([INSTANTLY_COLLECTION_TAG]) == ["instantly"]
        assert compute_collection_types([KEYWORD_COLLECTION_TAG, INSTANTLY_COLLECTION_TAG]) == [
            "keyword",
            "instantly",
        ]
        assert compute_collection_types([TENGDAO_COLLECTION_TAG, INSTANTLY_COLLECTION_TAG]) == [
            "reverse",
            "instantly",
        ]
        assert compute_collection_types([INSTANTLY_COLLECTION_TAG], source_id="manual-1") == [
            "manual",
            "instantly",
        ]
        assert compute_collection_types(None) == []
        assert compute_collection_types([KEYWORD_COLLECTION_TAG]) == ["keyword"]

    def test_instantly_filter_uses_indexable_contains(self):
        """instantly SQL 只看标签，并用 jsonb_path_ops 索引可命中的 @>。"""
        sql = build_collection_type_filter("instantly", company_alias="wc")

        assert sql == f"COALESCE(wc.data_source_tags, '[]'::jsonb) @> {INSTANTLY_TAG_JSONB}"
        assert "manual-%" not in sql

    def test_unknown_filter_excludes_instantly(self):
        """来源待确认不再包含带 Instantly 标签的公司。"""
        sql = build_collection_type_filter("unknown", company_alias="wc")

        instantly = f"COALESCE(wc.data_source_tags, '[]'::jsonb) @> {INSTANTLY_TAG_JSONB}"
        assert f"AND NOT ({instantly})" in sql

    def test_keyword_and_reverse_filters_ignore_instantly(self):
        """关键词采集 / 精准反推原规则不变，多标签公司仍能被筛到。"""
        for collection_type in ("keyword", "reverse"):
            sql = build_collection_type_filter(collection_type, company_alias="wc")
            assert INSTANTLY_TAG_JSONB not in sql

    def test_keyword_tag_jsonb_literal(self):
        """SQL 片段使用 jsonb 包含表达式需要的字面量。"""
        assert KEYWORD_TAG_JSONB == """'["外贸通关键词采集"]'::jsonb"""

    def test_reverse_filter_uses_only_positive_evidence(self):
        """reverse SQL 排除 manual/keyword，并要求腾道标签或反推公司证据。"""
        sql = build_collection_type_filter("reverse", company_alias="wc")

        assert "wc.source_id" in sql
        assert "manual-%" in sql
        assert KEYWORD_TAG_JSONB in sql
        assert TENGDAO_COLLECTION_TAG in sql
        assert "EXISTS" in sql
        assert "waimaotong_raw_companies" in sql
        assert "source_competitor" in sql
        assert "data_source_tags IS NULL OR NOT" not in sql
