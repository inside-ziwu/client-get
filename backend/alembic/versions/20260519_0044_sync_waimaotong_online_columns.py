"""同步外贸通线上直接添加的列到 Alembic 迁移。

waimaotong_raw_companies 补齐 18 列，waimaotong_raw_contacts 补齐 5 列。
使用 ADD COLUMN IF NOT EXISTS，幂等操作——线上已有这些列，跑迁移不报错。

revision: 20260519_0044
down_revision: 20260518_0043
"""

from alembic import op

revision = "20260519_0044"
down_revision = "20260518_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_companies
            ADD COLUMN IF NOT EXISTS company_id text,
            ADD COLUMN IF NOT EXISTS sys_company_id uuid,
            ADD COLUMN IF NOT EXISTS api_company_id text,
            ADD COLUMN IF NOT EXISTS company_name text,
            ADD COLUMN IF NOT EXISTS country text,
            ADD COLUMN IF NOT EXISTS source_type text,
            ADD COLUMN IF NOT EXISTS source_keyword text,
            ADD COLUMN IF NOT EXISTS source_competitor text,
            ADD COLUMN IF NOT EXISTS id_verified boolean,
            ADD COLUMN IF NOT EXISTS plan_id int,
            ADD COLUMN IF NOT EXISTS full_address text,
            ADD COLUMN IF NOT EXISTS website text,
            ADD COLUMN IF NOT EXISTS has_detail boolean,
            ADD COLUMN IF NOT EXISTS has_contacts boolean,
            ADD COLUMN IF NOT EXISTS email_count int,
            ADD COLUMN IF NOT EXISTS detail_raw_data text,
            ADD COLUMN IF NOT EXISTS raw_data text,
            ADD COLUMN IF NOT EXISTS error_msg text;
    """)

    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_contacts
            ADD COLUMN IF NOT EXISTS sys_contact_id uuid,
            ADD COLUMN IF NOT EXISTS contact_id text,
            ADD COLUMN IF NOT EXISTS sys_company_id uuid,
            ADD COLUMN IF NOT EXISTS api_company_id text,
            ADD COLUMN IF NOT EXISTS company_id text;
    """)


def downgrade() -> None:
    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_contacts
            DROP COLUMN IF EXISTS sys_contact_id,
            DROP COLUMN IF EXISTS contact_id,
            DROP COLUMN IF EXISTS sys_company_id,
            DROP COLUMN IF EXISTS api_company_id,
            DROP COLUMN IF EXISTS company_id;
    """)

    op.get_bind().exec_driver_sql("""
        ALTER TABLE waimaotong_raw_companies
            DROP COLUMN IF EXISTS company_id,
            DROP COLUMN IF EXISTS sys_company_id,
            DROP COLUMN IF EXISTS api_company_id,
            DROP COLUMN IF EXISTS company_name,
            DROP COLUMN IF EXISTS country,
            DROP COLUMN IF EXISTS source_type,
            DROP COLUMN IF EXISTS source_keyword,
            DROP COLUMN IF EXISTS source_competitor,
            DROP COLUMN IF EXISTS id_verified,
            DROP COLUMN IF EXISTS plan_id,
            DROP COLUMN IF EXISTS full_address,
            DROP COLUMN IF EXISTS website,
            DROP COLUMN IF EXISTS has_detail,
            DROP COLUMN IF EXISTS has_contacts,
            DROP COLUMN IF EXISTS email_count,
            DROP COLUMN IF EXISTS detail_raw_data,
            DROP COLUMN IF EXISTS raw_data,
            DROP COLUMN IF EXISTS error_msg;
    """)
