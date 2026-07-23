"""sanitize_subject / sanitize_plain_text 不得把 & 实体化为 &amp; 发出（生产实害修复）。"""

from app.utils.html_sanitizer import sanitize_html, sanitize_plain_text, sanitize_subject


class TestSanitizeUnescape:
    def test_subject_keeps_ampersand(self):
        assert sanitize_subject("Johnson & Johnson 采购部") == "Johnson & Johnson 采购部"

    def test_plain_text_keeps_ampersand_and_strips_tags(self):
        assert sanitize_plain_text("PCB & PCBA <b>manufacturer</b>") == "PCB & PCBA manufacturer"

    def test_script_payload_stays_inert_text(self):
        # unescape 在 strip 标签之后，还原出的 <script> 只是纯文本内容，不进入 HTML 路径
        out = sanitize_plain_text("&lt;script&gt;alert(1)&lt;/script&gt;")
        assert out == "<script>alert(1)</script>"

    def test_html_path_unchanged_still_escapes(self):
        # 富文本路径不受影响：& 在 HTML 语境保持实体化是正确行为
        assert sanitize_html("A & B") == "A &amp; B"
