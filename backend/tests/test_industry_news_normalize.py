from app.services.industry_news.normalize import (
    canonical_url,
    dedup_key,
    normalize_title,
    truncate_title,
)


def test_canonical_url_strips_tracking_and_slash():
    assert (
        canonical_url("HTTPS://Example.COM/a/b/?utm_source=x&fbclid=1&ref=home#frag")
        == "https://example.com/a/b"
    )
    assert canonical_url("https://example.com/a/b/") == "https://example.com/a/b"
    assert (
        canonical_url("https://example.com/a/b?keep=1&utm_campaign=z")
        == "https://example.com/a/b?keep=1"
    )


def test_canonical_url_rejects_empty_or_relative():
    assert canonical_url("") is None
    assert canonical_url("/relative") is None
    assert canonical_url("   ") is None


def test_normalize_title_keeps_cjk_and_strips_zero_width():
    title = "PCB\u200b 行业\u3000News &amp; 动态!!!"
    assert normalize_title(title) == "pcb 行业 news 动态"


def test_normalize_title_empty_after_cleanup():
    assert normalize_title("!!!") == ""
    assert dedup_key("!!!") is None
    assert dedup_key("") is None


def test_title_truncated_to_500():
    long_title = "A" * 600
    assert len(truncate_title(long_title)) == 500


def test_dedup_key_is_sha1_hex():
    key = dedup_key("Hello World")
    assert key is not None
    assert len(key) == 40
    assert key == dedup_key("hello   world")
