"""新建行业动态三表：动态源、动态、已读（PR A / A1）。

revision: 20260824_0001
down_revision: 20260723_0003

依据：`.trellis/tasks/08-23-industry-news/prd.md`（R3/R4）与 ADR 0001 / 0002；
DDL 与触发器写法见 design.md §2。动态源 / 动态为平台级（instance_id），
已读为租户业务表（tenant_id + user_id）。id 由应用层 new_uuid() 生成，无默认值。
instance_id 有意不设 DEFAULT 'default'：种子显式传、service 用 Settings.instance_id。
"""

from alembic import op

revision = "20260824_0001"
down_revision = "20260723_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    conn.exec_driver_sql(
        """
        CREATE TABLE industry_news_sources (
          id uuid PRIMARY KEY,
          instance_id varchar NOT NULL,
          industry varchar(50) NOT NULL,
          code varchar(50) NOT NULL,
          name varchar(100) NOT NULL,
          url text NOT NULL,
          category varchar(100) NOT NULL,
          lang varchar(10) NOT NULL,
          strategy varchar(20) NOT NULL CHECK (strategy IN ('rss','html','jsonld')),
          parse_config jsonb NOT NULL DEFAULT '{}',
          is_active boolean NOT NULL DEFAULT true,
          last_fetched_at timestamptz,
          last_success_at timestamptz,
          error_count integer NOT NULL DEFAULT 0,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_industry_news_sources_instance_code UNIQUE (instance_id, code)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX idx_industry_news_sources_instance_industry
          ON industry_news_sources (instance_id, industry, is_active)
        """
    )
    conn.exec_driver_sql(
        """
        DROP TRIGGER IF EXISTS set_updated_at ON industry_news_sources;
        CREATE TRIGGER set_updated_at
          BEFORE UPDATE ON industry_news_sources
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at()
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE industry_news_items (
          id uuid PRIMARY KEY,
          instance_id varchar NOT NULL,
          source_id uuid NOT NULL REFERENCES industry_news_sources(id),
          title varchar(500) NOT NULL,
          url text NOT NULL,
          canonical_url text NOT NULL,
          dedup_key varchar(40) NOT NULL,
          published_at timestamptz,
          fetched_at timestamptz NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_industry_news_items_instance_canonical_url
            UNIQUE (instance_id, canonical_url),
          CONSTRAINT uq_industry_news_items_instance_dedup_key UNIQUE (instance_id, dedup_key)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX idx_industry_news_items_instance_fetched
          ON industry_news_items (instance_id, fetched_at DESC)
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX idx_industry_news_items_source
          ON industry_news_items (source_id)
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE industry_news_reads (
          tenant_id uuid NOT NULL REFERENCES tenants(id),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          item_id uuid NOT NULL REFERENCES industry_news_items(id) ON DELETE CASCADE,
          read_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (user_id, item_id)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX idx_industry_news_reads_tenant_user
          ON industry_news_reads (tenant_id, user_id)
        """
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
    conn.exec_driver_sql("DROP TABLE industry_news_reads")
    conn.exec_driver_sql("DROP TABLE industry_news_items")
    conn.exec_driver_sql("DROP TABLE industry_news_sources")
