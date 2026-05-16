"""Link lixiaoyun API companies to keyword_master.

revision: 20260515_0041
down_revision: 20260514_0040
"""

from alembic import op

revision = "20260515_0041"
down_revision = "20260514_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE lixiaoyun_api_companies
          ADD COLUMN IF NOT EXISTS keyword_master_id uuid REFERENCES keyword_master(id);

        UPDATE lixiaoyun_api_companies ac
        SET keyword_master_id = km.id
        FROM keyword_master km
        WHERE ac.keyword_master_id IS NULL
          AND km.keyword = ac.keyword;

        DELETE FROM lixiaoyun_api_companies
        WHERE keyword_master_id IS NULL;

        ALTER TABLE lixiaoyun_api_companies
          DROP COLUMN IF EXISTS keyword;

        CREATE INDEX IF NOT EXISTS idx_lixiaoyun_api_companies_keyword_master_id
          ON lixiaoyun_api_companies(keyword_master_id);

        CREATE INDEX IF NOT EXISTS idx_lixiaoyun_api_companies_collected_at
          ON lixiaoyun_api_companies(collected_at DESC);
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        DROP INDEX IF EXISTS idx_lixiaoyun_api_companies_collected_at;
        DROP INDEX IF EXISTS idx_lixiaoyun_api_companies_keyword_master_id;

        ALTER TABLE lixiaoyun_api_companies
          ADD COLUMN IF NOT EXISTS keyword text;

        UPDATE lixiaoyun_api_companies ac
        SET keyword = km.keyword
        FROM keyword_master km
        WHERE ac.keyword IS NULL
          AND km.id = ac.keyword_master_id;

        ALTER TABLE lixiaoyun_api_companies
          DROP COLUMN IF EXISTS keyword_master_id;
        """
    )
