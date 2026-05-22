"""邮件模板 body_html 迁移辅助函数的单元测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from migrate_email_templates_html import (
    classify_html,
    plain_text_to_html,
    raw_text_to_html,
    text_from_html,
)


# ── classify_html ──────────────────────────────────────────────


class TestClassifyHtml:
    def test_p_tag_returns_proper_html(self):
        assert classify_html("<p>hello</p>") == "proper_html"

    def test_br_tag_returns_proper_html(self):
        assert classify_html("line1<br>line2") == "proper_html"

    def test_br_self_closing_returns_proper_html(self):
        assert classify_html("line1<br/>line2") == "proper_html"

    def test_br_self_closing_with_space_returns_proper_html(self):
        assert classify_html("line1<br />line2") == "proper_html"

    def test_plain_text_returns_raw_text(self):
        assert classify_html("just plain text") == "raw_text"

    def test_escaped_entities_without_tags_returns_raw_text(self):
        assert classify_html("含 &amp; 字符") == "raw_text"

    def test_style_only_returns_style_only(self):
        assert classify_html("<style>body{color:red}</style>") == "style_only"

    def test_empty_string_returns_empty_html(self):
        assert classify_html("") == "empty_html"

    def test_none_returns_empty_html(self):
        assert classify_html(None) == "empty_html"

    def test_whitespace_only_returns_empty_html(self):
        assert classify_html("   \n\t  ") == "empty_html"


# ── raw_text_to_html ──────────────────────────────────────────


class TestRawTextToHtml:
    def test_double_newline_splits_paragraphs(self):
        assert raw_text_to_html("第一段\n\n第二段") == "<p>第一段</p><p>第二段</p>"

    def test_single_newline_becomes_br(self):
        assert raw_text_to_html("第一行\n第二行") == "<p>第一行<br>第二行</p>"

    def test_preserves_escaped_entities(self):
        assert raw_text_to_html("含 &amp; 字符") == "<p>含 &amp; 字符</p>"

    def test_single_paragraph_no_newline(self):
        assert raw_text_to_html("单段落无换行") == "<p>单段落无换行</p>"


# ── plain_text_to_html ────────────────────────────────────────


class TestPlainTextToHtml:
    def test_escapes_script_tag(self):
        result = plain_text_to_html("hello <script>alert(1)</script>")
        assert result == "<p>hello &lt;script&gt;alert(1)&lt;/script&gt;</p>"

    def test_double_newline_splits_paragraphs(self):
        assert plain_text_to_html("第一段\n\n第二段") == "<p>第一段</p><p>第二段</p>"

    def test_escapes_ampersand(self):
        assert plain_text_to_html("a&b") == "<p>a&amp;b</p>"


# ── text_from_html ────────────────────────────────────────────


class TestTextFromHtml:
    def test_strips_tags_and_extracts_text(self):
        assert text_from_html("<p>你好 <strong>张三</strong></p>") == "你好 张三"

    def test_paragraphs_separated_by_newline(self):
        result = text_from_html("<p>第一段</p><p>第二段</p>")
        assert "第一段" in result
        assert "第二段" in result
        assert "\n" in result

    def test_empty_string_returns_empty(self):
        assert text_from_html("") == ""

    def test_none_returns_empty(self):
        assert text_from_html(None) == ""
