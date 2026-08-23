"""行业动态 URL / 标题规范化与同稿键。"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
}
_UTM_PREFIX = "utm_"
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)
_KEEP_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff\u3400-\u4dbf]+", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")
TITLE_MAX_LEN = 500


def canonical_url(url: str) -> str | None:
    """规范化 URL：scheme/host 小写，去跟踪参数、fragment 与尾斜杠。"""
    raw = (url or "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return None
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or ""
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS and not key.lower().startswith(_UTM_PREFIX)
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title(title: str) -> str:
    """NFKC → 去零宽 → unescape → 小写 → 去非字母数字（保留 CJK）→ 合并空白。"""
    text = unicodedata.normalize("NFKC", title or "")
    text = text.translate(_ZERO_WIDTH)
    text = html.unescape(text).lower()
    text = _KEEP_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def truncate_title(title: str) -> str:
    return title.strip()[:TITLE_MAX_LEN]


def dedup_key(title: str) -> str | None:
    normalized = normalize_title(title)
    if not normalized:
        return None
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()
