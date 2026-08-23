import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.seed_industry_news_sources import _same, seed

SEED = Path(__file__).parents[1] / "app" / "data" / "industry_news_sources_pcb.json"
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "20260824_0001_industry_news.py"

EXPECTED_CODES = [
    "pcb-update",
    "pcea",
    "iconnect007",
    "pcdandf",
    "circuits-assembly",
    "ipc",
    "pcb-west",
    "pcb-east",
    "tpca",
    "nepcon-japan",
    "productronica",
    "electronica",
    "cpca-news",
    "cpca-weekly",
]


def test_seed_has_fourteen_stable_codes():
    rows = json.loads(SEED.read_text(encoding="utf-8"))
    assert [row["code"] for row in rows] == EXPECTED_CODES
    assert len(set(EXPECTED_CODES)) == 14
    for row in rows:
        assert row["industry"] == "PCB"
        assert row["strategy"] in {"rss", "html", "jsonld"}
        assert row["url"].startswith("http")
        assert "parse_config" in row


def test_migration_revision_and_timeouts():
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260824_0001"' in text
    assert 'down_revision = "20260723_0003"' in text
    assert "SET LOCAL lock_timeout = '5s'" in text
    assert "SET LOCAL statement_timeout = '30s'" in text
    assert "CREATE TRIGGER set_updated_at" in text
    assert "DROP TABLE industry_news_reads" in text
    assert "DROP TABLE industry_news_items" in text
    assert "DROP TABLE industry_news_sources" in text


@pytest.mark.asyncio
async def test_seed_refuses_non_default_instance_without_confirm():
    args = argparse.Namespace(
        instance="instance_b", confirm_instance=None, file=str(SEED), dry_run=True
    )
    with (
        patch("scripts.seed_industry_news_sources.initialize_engines") as init_engines,
        pytest.raises(SystemExit) as exc,
    ):
        await seed(args)
    assert exc.value.code == 2
    init_engines.assert_not_called()


def test_same_compares_seed_attributes_only():
    row = {
        "code": "pcea",
        "name": "PCEA",
        "url": "https://pcea.net/feed/",
        "industry": "PCB",
        "category": "PCB 技术 / 工程",
        "lang": "en",
        "strategy": "rss",
        "parse_config": {},
    }
    existing = {
        **{k: v for k, v in row.items() if k != "code"},
        "parse_config": "{}",
        "is_active": False,
        "error_count": 7,
    }
    assert _same(existing, row) is True
    assert _same({**existing, "url": "https://pcea.net/feed2/"}, row) is False
