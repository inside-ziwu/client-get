"""新增国家工作时间配置表和时区跳过记录。

revision: 20260529_0001
down_revision: 20260525_0100
"""

from __future__ import annotations

import json
from pathlib import Path

from alembic import op

revision = "20260529_0001"
down_revision = "20260525_0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS work_rule_sets (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name text NOT NULL,
          work_days int[] NOT NULL,
          time_segments jsonb NOT NULL,
          is_default boolean NOT NULL DEFAULT false,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CHECK (array_length(work_days, 1) IS NOT NULL),
          CHECK (time_segments <> '[]'::jsonb)
        );
        """
    )
    conn.exec_driver_sql(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_work_rule_sets_one_default
          ON work_rule_sets(is_default)
          WHERE is_default;
        """
    )
    conn.exec_driver_sql(
        """
        DROP TRIGGER IF EXISTS set_updated_at ON work_rule_sets;
        CREATE TRIGGER set_updated_at
          BEFORE UPDATE ON work_rule_sets
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS countries (
          iso3 char(3) PRIMARY KEY,
          name_zh text NOT NULL,
          name_en text NOT NULL,
          timezone text NOT NULL,
          rule_set_id uuid REFERENCES work_rule_sets(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CHECK (iso3 ~ '^[A-Z]{3}$')
        );
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS idx_countries_rule_set
          ON countries(rule_set_id);
        """
    )
    conn.exec_driver_sql(
        """
        DROP TRIGGER IF EXISTS set_updated_at ON countries;
        CREATE TRIGGER set_updated_at
          BEFORE UPDATE ON countries
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS country_holidays (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          country_iso3 char(3) NOT NULL REFERENCES countries(iso3) ON DELETE CASCADE,
          date date NOT NULL,
          name text,
          source varchar(20) NOT NULL DEFAULT 'manual',
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (country_iso3, date)
        );
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS idx_country_holidays_country_date
          ON country_holidays(country_iso3, date);
        """
    )
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          ADD COLUMN IF NOT EXISTS last_skip_reason text,
          ADD COLUMN IF NOT EXISTS last_skip_at timestamptz;
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS idx_emails_enrollment
          ON emails(enrollment_id)
          WHERE enrollment_id IS NOT NULL;
        """
    )
    conn.exec_driver_sql(
        """
        INSERT INTO work_rule_sets (name, work_days, time_segments, is_default)
        SELECT '默认工作时间', ARRAY[0,1,2,3,4]::int[], '[{"start":"09:00","end":"17:00"}]'::jsonb, true
        WHERE NOT EXISTS (SELECT 1 FROM work_rule_sets WHERE is_default = true);
        """
    )

    countries_path = Path(__file__).resolve().parents[2] / "app" / "data" / "countries.json"
    countries = json.loads(countries_path.read_text(encoding="utf-8"))
    conn.exec_driver_sql(
        """
        INSERT INTO countries (iso3, name_zh, name_en, timezone)
        SELECT iso3, name_zh, name_en, timezone
        FROM json_to_recordset(%(countries)s::json)
          AS item(iso3 char(3), name_zh text, name_en text, timezone text)
        ON CONFLICT (iso3) DO UPDATE
        SET name_zh = EXCLUDED.name_zh,
            name_en = EXCLUDED.name_en,
            timezone = EXCLUDED.timezone,
            updated_at = now();
        """,
        {"countries": json.dumps(countries, ensure_ascii=False)},
    )

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
    conn.exec_driver_sql("DROP INDEX IF EXISTS idx_emails_enrollment;")
    conn.exec_driver_sql(
        """
        ALTER TABLE sequence_enrollments
          DROP COLUMN IF EXISTS last_skip_at,
          DROP COLUMN IF EXISTS last_skip_reason;
        """
    )
    conn.exec_driver_sql("DROP TABLE IF EXISTS country_holidays;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS countries;")
    conn.exec_driver_sql("DROP TABLE IF EXISTS work_rule_sets;")
