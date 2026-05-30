"""初始化 2026 国家假日种子数据。

revision: 20260529_0003
down_revision: 20260529_0002
"""

from __future__ import annotations

import json
from pathlib import Path

from alembic import op

revision = "20260529_0003"
down_revision = "20260529_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    holidays_path = Path(__file__).resolve().parents[2] / "app" / "data" / "country_holidays_2026.json"
    holidays = json.loads(holidays_path.read_text(encoding="utf-8"))
    conn.exec_driver_sql(
        """
        INSERT INTO country_holidays (country_iso3, date, name, source)
        SELECT country_iso3, date, name, source
        FROM json_to_recordset(%(holidays)s::json)
          AS item(country_iso3 char(3), date date, name text, source varchar(20))
        ON CONFLICT (country_iso3, date) DO NOTHING;
        """,
        {"holidays": json.dumps(holidays, ensure_ascii=False)},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("DELETE FROM country_holidays WHERE source = 'seed';")
