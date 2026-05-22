from app.utils.email_text import text_from_html


def test_text_from_html_strips_tags_and_preserves_inline_spaces():
    assert text_from_html("<p>你好 <strong>张三</strong></p>") == "你好 张三"


def test_text_from_html_separates_paragraphs_with_newlines():
    assert text_from_html("<p>第一段</p><p>第二段</p>") == "第一段\n第二段"


def test_text_from_html_preserves_br_as_newline():
    assert text_from_html("第一行<br>第二行<br />第三行") == "第一行\n第二行\n第三行"


def test_text_from_html_separates_list_items():
    assert text_from_html("<ul><li>第一项</li><li>第二项</li></ul>") == "第一项\n第二项"


def test_text_from_html_returns_empty_for_empty_input():
    assert text_from_html("") == ""
    assert text_from_html(None) == ""


def test_text_from_html_decodes_entities():
    assert text_from_html("<p>A&amp;B&nbsp;Co.</p>") == "A&B Co."


def test_text_from_html_ignores_style_and_script_content():
    html = "<style>body{color:red}</style><script>alert(1)</script><p>正文</p>"

    assert text_from_html(html) == "正文"
