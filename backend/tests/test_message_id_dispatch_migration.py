"""emails.engagelab_message_id 扩为 TEXT，锁增加接单阶段。downgrade 不得截断。"""

from pathlib import Path

import pytest

from tests.migration_helpers import collect_statements, load_migration

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20261028_0001_email_message_id_text_and_dispatch_locks.py"
)


@pytest.fixture(scope="module")
def migration():
    return load_migration(MIGRATION_PATH, "message_id_dispatch_migration")


def test_upgrade_widens_message_id_and_adds_dispatch_states(migration, monkeypatch):
    executed = collect_statements(migration, monkeypatch, "upgrade")
    statement = "\n".join(executed)

    assert migration.revision == "20261028_0001"
    assert migration.down_revision == "20260824_0002"
    assert "SET LOCAL lock_timeout = '5s'" in statement
    assert "SET LOCAL statement_timeout = '30s'" in statement
    assert "ALTER COLUMN engagelab_message_id TYPE text" in statement
    assert "provider_message_id text" in statement
    assert "quota_usage_date date" in statement
    assert "finalize_not_before timestamptz" in statement
    assert "idx_email_send_locks_unsent_locked" in statement
    assert "idx_email_send_locks_finalize_due" in statement
    assert "'accepted_pending'" in statement
    assert "'dispatching'" in statement
    assert "'uncertain'" in statement
    assert "email_send_locks_status_check" in statement
    assert "varchar(100)" not in statement
    assert "substring" not in statement.casefold()


def test_downgrade_refuses_long_ids_and_live_dispatch_facts(migration, monkeypatch):
    executed = collect_statements(migration, monkeypatch, "downgrade")
    statement = "\n".join(executed)

    refuse_at = statement.index("RAISE EXCEPTION")
    shrink_at = statement.index("TYPE varchar(100)")
    assert refuse_at < shrink_at
    assert "length(engagelab_message_id) > 100" in statement
    assert "dispatch states still present" in statement
    assert "dispatch facts still present" in statement
    assert "finalize_not_before IS NOT NULL" in statement
    assert "DROP INDEX idx_email_send_locks_finalize_due" in statement
    assert "DROP COLUMN finalize_not_before" in statement
    assert "substring" not in statement.casefold()
