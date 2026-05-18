"""删除 raw_companies 13 列和 raw_contacts 8 列未使用字段。

数据已备份至 ~/.clientget/db-backups/drop-columns-backup-20260518/

revision: 20260518_0042
down_revision: 20260515_0041
"""

from alembic import op

revision = "20260518_0042"
down_revision = "20260515_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_companies
            DROP COLUMN IF EXISTS country_name,
            DROP COLUMN IF EXISTS country_code,
            DROP COLUMN IF EXISTS logo,
            DROP COLUMN IF EXISTS origin,
            DROP COLUMN IF EXISTS social_medias,
            DROP COLUMN IF EXISTS tags,
            DROP COLUMN IF EXISTS revenue,
            DROP COLUMN IF EXISTS founded_date,
            DROP COLUMN IF EXISTS legal_name,
            DROP COLUMN IF EXISTS company_type,
            DROP COLUMN IF EXISTS sic_codes,
            DROP COLUMN IF EXISTS naics_codes,
            DROP COLUMN IF EXISTS website_url;

        ALTER TABLE waimaotong_raw_contacts
            DROP COLUMN IF EXISTS job_title,
            DROP COLUMN IF EXISTS country,
            DROP COLUMN IF EXISTS region,
            DROP COLUMN IF EXISTS score,
            DROP COLUMN IF EXISTS emails,
            DROP COLUMN IF EXISTS linkedin_url,
            DROP COLUMN IF EXISTS twitter_url,
            DROP COLUMN IF EXISTS facebook_url;
    """)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("""
        -- waimaotong_raw_companies：恢复 13 列结构（数据不可恢复）
        ALTER TABLE waimaotong_raw_companies
            ADD COLUMN IF NOT EXISTS country_name text,
            ADD COLUMN IF NOT EXISTS country_code text,
            ADD COLUMN IF NOT EXISTS logo text,
            ADD COLUMN IF NOT EXISTS origin text,
            ADD COLUMN IF NOT EXISTS social_medias jsonb,
            ADD COLUMN IF NOT EXISTS tags text[],
            ADD COLUMN IF NOT EXISTS revenue text,
            ADD COLUMN IF NOT EXISTS founded_date text,
            ADD COLUMN IF NOT EXISTS legal_name text,
            ADD COLUMN IF NOT EXISTS company_type text,
            ADD COLUMN IF NOT EXISTS sic_codes jsonb,
            ADD COLUMN IF NOT EXISTS naics_codes jsonb,
            ADD COLUMN IF NOT EXISTS website_url text;

        -- waimaotong_raw_contacts：恢复 8 列结构（数据不可恢复）
        ALTER TABLE waimaotong_raw_contacts
            ADD COLUMN IF NOT EXISTS job_title text,
            ADD COLUMN IF NOT EXISTS country text,
            ADD COLUMN IF NOT EXISTS region text,
            ADD COLUMN IF NOT EXISTS score integer,
            ADD COLUMN IF NOT EXISTS emails text[],
            ADD COLUMN IF NOT EXISTS linkedin_url text,
            ADD COLUMN IF NOT EXISTS twitter_url text,
            ADD COLUMN IF NOT EXISTS facebook_url text;
    """)
