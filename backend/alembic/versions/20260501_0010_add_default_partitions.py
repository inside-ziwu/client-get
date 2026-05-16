"""Add DEFAULT partitions as fallback for audit_logs, emails, intelligence_articles.

Without a DEFAULT partition, any INSERT whose created_at doesn't match an
existing monthly partition raises a CheckViolationError at runtime.  The
DEFAULT partition absorbs those rows so the application never crashes due to
a missing monthly partition.  The monthly partitions created by the startup
hook take priority for new rows; the default is only a safety net.

revision: 20260501_0010
"""

from alembic import op

revision = "20260501_0010"
down_revision = "20260430_0009"
branch_labels = None
depends_on = None

_TABLES = [
    ("audit_logs", "audit_logs_default"),
    ("emails", "emails_default"),
    ("intelligence_articles", "intelligence_articles_default"),
]


def upgrade() -> None:
    for parent, child in _TABLES:
        op.get_bind().exec_driver_sql(
            f"""
            CREATE TABLE IF NOT EXISTS {child}
            PARTITION OF {parent} DEFAULT;
            """
        )


def downgrade() -> None:
    for _, child in reversed(_TABLES):
        op.get_bind().exec_driver_sql(f"DROP TABLE IF EXISTS {child};")
