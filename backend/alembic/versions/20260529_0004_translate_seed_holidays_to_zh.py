"""将 2026 seed 假日名称同步为中文。

revision: 20260529_0004
down_revision: 20260529_0003
"""

from __future__ import annotations

import json
from pathlib import Path

from alembic import op

revision = "20260529_0004"
down_revision = "20260529_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    holidays_path = Path(__file__).resolve().parents[2] / "app" / "data" / "country_holidays_2026.json"
    holidays = json.loads(holidays_path.read_text(encoding="utf-8"))
    conn.exec_driver_sql(
        """
        UPDATE country_holidays AS ch
        SET name = item.name
        FROM json_to_recordset(%(holidays)s::json)
          AS item(country_iso3 char(3), date date, name text, source varchar(20))
        WHERE ch.country_iso3 = item.country_iso3
          AND ch.date = item.date
          AND ch.source = 'seed';
        """,
        {"holidays": json.dumps(holidays, ensure_ascii=False)},
    )


def downgrade() -> None:
    pass
