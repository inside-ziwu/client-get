import re

import bleach

ALLOWED_HTML_TAGS = [
    "a",
    "b",
    "blockquote",
    "br",
    "center",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "span",
    "strong",
    "style",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
]
ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "*": ["style", "class", "width", "height", "align", "valign", "bgcolor"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan", "width", "height", "align", "valign"],
    "th": ["colspan", "rowspan", "width", "height", "align", "valign"],
    "table": ["border", "cellpadding", "cellspacing", "width"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_subject(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = bleach.clean(value, tags=[], attributes={}, protocols=ALLOWED_PROTOCOLS, strip=True)
    return re.sub(r"\s+", " ", cleaned.replace("\r", " ").replace("\n", " ")).strip()


def sanitize_plain_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = bleach.clean(value, tags=[], attributes={}, protocols=ALLOWED_PROTOCOLS, strip=True)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in cleaned.split("\n")).strip()


def sanitize_html(value: str | None) -> str | None:
    if value is None:
        return None
    return bleach.clean(
        value,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    ).strip()
