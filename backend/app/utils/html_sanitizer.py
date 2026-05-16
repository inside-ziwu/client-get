import re

import bleach

ALLOWED_HTML_TAGS = [
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "ul",
]
ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
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
