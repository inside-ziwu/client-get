from app.services.email_template_backfill_service import build_body_text_backfill_candidates


def test_build_body_text_backfill_candidates_extracts_plain_text():
    rows = [
        {"id": "tpl-1", "body_html": "<p>第一段</p><p>第二段</p>"},
        {"id": "tpl-2", "body_html": "<style>body{color:red}</style>"},
    ]

    candidates, skipped = build_body_text_backfill_candidates(rows)

    assert [(item.id, item.body_text) for item in candidates] == [
        ("tpl-1", "第一段\n第二段"),
    ]
    assert skipped == 1


def test_build_body_text_backfill_candidates_decodes_entities():
    rows = [{"id": "tpl-1", "body_html": "<p>A&amp;B&nbsp;Co.</p>"}]

    candidates, skipped = build_body_text_backfill_candidates(rows)

    assert [(item.id, item.body_text) for item in candidates] == [("tpl-1", "A&B Co.")]
    assert skipped == 0
