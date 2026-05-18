"""删除管道代码引用的 waimaotong_raw_companies 20 列。

管道代码（collection/cleanup/scoring）已删除，这些列不再有代码引用。
数据已备份至 ~/.clientget/db-backups/drop-pipeline-columns-backup-20260518/
注意：waimaotong_raw_contacts 的 5 列兼容列保留（与原项目 contact_data 保持一致）。

revision: 20260518_0043
down_revision: 20260518_0042
"""

from alembic import op

revision = "20260518_0043"
down_revision = "20260518_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_companies
            DROP COLUMN IF EXISTS keyword_master_id,
            DROP COLUMN IF EXISTS collection_type,
            DROP COLUMN IF EXISTS source_id,
            DROP COLUMN IF EXISTS country_iso3,
            DROP COLUMN IF EXISTS address,
            DROP COLUMN IF EXISTS emails,
            DROP COLUMN IF EXISTS trade_amount_3y_usd,
            DROP COLUMN IF EXISTS trade_count,
            DROP COLUMN IF EXISTS has_trade_data,
            DROP COLUMN IF EXISTS customs_data,
            DROP COLUMN IF EXISTS search_payload,
            DROP COLUMN IF EXISTS detail_payload,
            DROP COLUMN IF EXISTS trade_payload,
            DROP COLUMN IF EXISTS raw_payload,
            DROP COLUMN IF EXISTS detail_fetched_at,
            DROP COLUMN IF EXISTS trade_status,
            DROP COLUMN IF EXISTS trade_fetched_at,
            DROP COLUMN IF EXISTS contacts_status,
            DROP COLUMN IF EXISTS contacts_fetched_at,
            DROP COLUMN IF EXISTS enrichment_error;
    """)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_companies
            ADD COLUMN IF NOT EXISTS keyword_master_id uuid,
            ADD COLUMN IF NOT EXISTS collection_type text,
            ADD COLUMN IF NOT EXISTS source_id text,
            ADD COLUMN IF NOT EXISTS country_iso3 char(3),
            ADD COLUMN IF NOT EXISTS address text,
            ADD COLUMN IF NOT EXISTS emails text[],
            ADD COLUMN IF NOT EXISTS trade_amount_3y_usd numeric,
            ADD COLUMN IF NOT EXISTS trade_count integer,
            ADD COLUMN IF NOT EXISTS has_trade_data boolean,
            ADD COLUMN IF NOT EXISTS customs_data jsonb,
            ADD COLUMN IF NOT EXISTS search_payload jsonb,
            ADD COLUMN IF NOT EXISTS detail_payload jsonb,
            ADD COLUMN IF NOT EXISTS trade_payload jsonb,
            ADD COLUMN IF NOT EXISTS raw_payload jsonb,
            ADD COLUMN IF NOT EXISTS detail_fetched_at timestamptz,
            ADD COLUMN IF NOT EXISTS trade_status text,
            ADD COLUMN IF NOT EXISTS trade_fetched_at timestamptz,
            ADD COLUMN IF NOT EXISTS contacts_status text,
            ADD COLUMN IF NOT EXISTS contacts_fetched_at timestamptz,
            ADD COLUMN IF NOT EXISTS enrichment_error jsonb;
    """)
