"""phase1 collection schema

Revision ID: 20260430_0009
Revises: 20260429_0008
Create Date: 2026-04-30
"""

from alembic import op

revision = "20260430_0009"
down_revision = "20260429_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        r"""
        DROP TABLE IF EXISTS tenant_companies CASCADE;
        DROP TABLE IF EXISTS competitor_companies CASCADE;
        DROP TABLE IF EXISTS company_sources CASCADE;
        DROP TABLE IF EXISTS shared_companies CASCADE;

        CREATE TABLE waimaotong_raw_companies (
          id              bigserial PRIMARY KEY,
          source_id       text NOT NULL,
          collection_type text NOT NULL CHECK (collection_type IN ('direct_search','reverse_lookup')),
          name            text,
          country_iso3    char(3) CHECK (country_iso3 IS NULL OR country_iso3 ~ '^[A-Z]{3}$'),
          domain          text,
          industry        text,
          phone           text,
          customs_data    jsonb,
          emails          text[],
          task_id         uuid,
          raw_payload     jsonb,
          created_at      timestamptz DEFAULT now(),
          last_seen_at    timestamptz DEFAULT now(),
          UNIQUE (source_id)
        );

        CREATE TABLE tendata_raw_companies (
          tid                 text PRIMARY KEY,
          globiz_id           text,
          name                text,
          name_local          text,
          country_iso3        char(3) CHECK (country_iso3 IS NULL OR country_iso3 ~ '^[A-Z]{3}$'),
          website             text,
          tax_no              text,
          incorporation_date  date,
          employee_num        int,
          industry_desc       text,
          product_tags        text[],
          pcb_suppliers       text[],
          trade_amount_3y_usd numeric,
          trade_count         int,
          contacts_count      int,
          has_trade_data      boolean,
          aliases             text[],
          task_id             uuid,
          raw_payload         jsonb,
          created_at          timestamptz DEFAULT now(),
          last_seen_at        timestamptz DEFAULT now()
        );

        CREATE TABLE lixiaoyun_raw_companies (
          id              bigserial PRIMARY KEY,
          source_id       text NOT NULL,
          name            text,
          english_name    text,
          domain          text,
          esdate          date,
          legalperson     text,
          uncid           text,
          reg_capital     text,
          employee_scale  text,
          reg_address     text,
          task_id         uuid NOT NULL REFERENCES collection_tasks(id) ON DELETE CASCADE,
          raw_payload     jsonb,
          created_at      timestamptz DEFAULT now(),
          last_seen_at    timestamptz DEFAULT now(),
          UNIQUE (source_id)
        );

        CREATE TABLE clean_companies (
          id              bigserial PRIMARY KEY,
          name_normalized text NOT NULL,
          name_display    text,
          country_iso3    char(3) NOT NULL CHECK (country_iso3 ~ '^[A-Z]{3}$'),
          domain          text,
          industry        text,
          products        text[],
          contacts_count  int DEFAULT 0,
          sources         text[] DEFAULT '{}',
          last_updated    timestamptz DEFAULT now(),
          created_at      timestamptz DEFAULT now(),
          UNIQUE (name_normalized, country_iso3)
        );
        CREATE UNIQUE INDEX uq_clean_companies_domain
          ON clean_companies(domain)
          WHERE domain IS NOT NULL;

        CREATE TABLE tenant_companies (
          id                bigserial PRIMARY KEY,
          tenant_id         uuid NOT NULL,
          clean_company_id  bigint NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
          matched_keywords  text[] DEFAULT '{}',
          is_precise        boolean DEFAULT false,
          status            text DEFAULT 'new',
          created_at        timestamptz DEFAULT now(),
          last_action_at    timestamptz DEFAULT now(),
          UNIQUE (tenant_id, clean_company_id)
        );
        CREATE INDEX idx_tenant_companies_matched_keywords
          ON tenant_companies USING gin(matched_keywords);
        ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_select_companies ON tenant_companies
          FOR SELECT USING (tenant_id = current_tenant_id());
        CREATE POLICY tenant_write_companies ON tenant_companies
          FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

        CREATE TABLE cleanup_queue (
          id           bigserial PRIMARY KEY,
          raw_table    text NOT NULL,
          raw_row_id   bigint NOT NULL,
          task_id      uuid,
          enqueued_at  timestamptz DEFAULT now(),
          status       text DEFAULT 'pending' CHECK (status IN ('pending','processing','done','failed')),
          attempts     int DEFAULT 0,
          last_error   text,
          processed_at timestamptz,
          UNIQUE (raw_table, raw_row_id)
        );
        CREATE INDEX idx_cleanup_queue_pending
          ON cleanup_queue(id)
          WHERE status = 'pending';

        -- Drop old constraints/indexes that reference countries_hash before dropping the column
        ALTER TABLE collection_keywords
          DROP CONSTRAINT IF EXISTS collection_keywords_tenant_id_keyword_normalized_countries__key;
        DROP INDEX IF EXISTS idx_collection_keywords_sched;

        ALTER TABLE collection_keywords
          DROP COLUMN IF EXISTS source_types,
          DROP COLUMN IF EXISTS countries,
          DROP COLUMN IF EXISTS countries_hash,
          ADD COLUMN IF NOT EXISTS subscription_status text DEFAULT 'not_started',
          ADD COLUMN IF NOT EXISTS current_page int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS total_pages int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS today_pages int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS last_run_date date,
          ADD COLUMN IF NOT EXISTS daily_page_limit int DEFAULT 10,
          ADD COLUMN IF NOT EXISTS stage1_today_count int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS stage1_total_count int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS last_stage1_date date,
          ADD COLUMN IF NOT EXISTS stage1_status text DEFAULT 'not_started',
          ADD COLUMN IF NOT EXISTS daily_stage1_limit int DEFAULT 1000,
          ADD COLUMN IF NOT EXISTS stage2_today_count int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS stage2_total_count int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS last_stage2_date date,
          ADD COLUMN IF NOT EXISTS stage2_status text DEFAULT 'not_started',
          ADD COLUMN IF NOT EXISTS daily_stage2_limit int DEFAULT 100,
          ADD COLUMN IF NOT EXISTS total_companies int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS total_contacts int DEFAULT 0,
          ADD COLUMN IF NOT EXISTS error_msg text,
          ADD COLUMN IF NOT EXISTS started_at timestamptz;

        -- New unique constraint and index without countries_hash
        ALTER TABLE collection_keywords
          ADD CONSTRAINT collection_keywords_tenant_id_keyword_normalized_key
          UNIQUE (tenant_id, keyword_normalized);
        CREATE INDEX IF NOT EXISTS idx_collection_keywords_sched
          ON collection_keywords (status, keyword_normalized);

        ALTER TABLE data_source_credentials
          ADD COLUMN IF NOT EXISTS raw_config jsonb DEFAULT '{}'::jsonb;

        CREATE OR REPLACE FUNCTION normalize_company_name(name text) RETURNS text AS $$
        DECLARE
            result text;
            suffix_pattern text;
        BEGIN
            IF name IS NULL THEN RETURN NULL; END IF;
            result := UPPER(name);
            result := REGEXP_REPLACE(result, '[\.,;:''"\(\)&\-]', ' ', 'g');
            suffix_pattern := '\s+(SDN BHD|PVT LTD|PRIVATE LIMITED|CO LTD|CO\.|INC|CORP|CORPORATION|LLC|GMBH|MFG|LIMITED|LTD)\s*$';
            LOOP
                result := REGEXP_REPLACE(result, suffix_pattern, '', 'i');
                EXIT WHEN result = REGEXP_REPLACE(result, suffix_pattern, '', 'i');
            END LOOP;
            result := REGEXP_REPLACE(TRIM(result), '\s+', ' ', 'g');
            RETURN result;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION IF EXISTS normalize_company_name(text);

        ALTER TABLE data_source_credentials
          DROP COLUMN IF EXISTS raw_config;

        -- Restore old unique constraint / index
        ALTER TABLE collection_keywords
          DROP CONSTRAINT IF EXISTS collection_keywords_tenant_id_keyword_normalized_key;
        DROP INDEX IF EXISTS idx_collection_keywords_sched;

        ALTER TABLE collection_keywords
          DROP COLUMN IF EXISTS started_at,
          DROP COLUMN IF EXISTS error_msg,
          DROP COLUMN IF EXISTS total_contacts,
          DROP COLUMN IF EXISTS total_companies,
          DROP COLUMN IF EXISTS daily_stage2_limit,
          DROP COLUMN IF EXISTS stage2_status,
          DROP COLUMN IF EXISTS last_stage2_date,
          DROP COLUMN IF EXISTS stage2_total_count,
          DROP COLUMN IF EXISTS stage2_today_count,
          DROP COLUMN IF EXISTS daily_stage1_limit,
          DROP COLUMN IF EXISTS stage1_status,
          DROP COLUMN IF EXISTS last_stage1_date,
          DROP COLUMN IF EXISTS stage1_total_count,
          DROP COLUMN IF EXISTS stage1_today_count,
          DROP COLUMN IF EXISTS daily_page_limit,
          DROP COLUMN IF EXISTS last_run_date,
          DROP COLUMN IF EXISTS today_pages,
          DROP COLUMN IF EXISTS total_pages,
          DROP COLUMN IF EXISTS current_page,
          DROP COLUMN IF EXISTS subscription_status,
          ADD COLUMN IF NOT EXISTS countries jsonb NOT NULL DEFAULT '[]',
          ADD COLUMN IF NOT EXISTS countries_hash varchar(64) NOT NULL DEFAULT '',
          ADD COLUMN IF NOT EXISTS source_types jsonb NOT NULL DEFAULT '["waimao_tong","tengdao","lixiaoyun"]';

        ALTER TABLE collection_keywords
          ADD CONSTRAINT collection_keywords_tenant_id_keyword_normalized_countries__key
          UNIQUE (tenant_id, keyword_normalized, countries_hash);
        CREATE INDEX IF NOT EXISTS idx_collection_keywords_sched
          ON collection_keywords (status, keyword_normalized, countries_hash);

        DROP TABLE IF EXISTS cleanup_queue CASCADE;
        DROP TABLE IF EXISTS tenant_companies CASCADE;
        DROP TABLE IF EXISTS clean_companies CASCADE;
        DROP TABLE IF EXISTS lixiaoyun_raw_companies CASCADE;
        DROP TABLE IF EXISTS tendata_raw_companies CASCADE;
        DROP TABLE IF EXISTS waimaotong_raw_companies CASCADE;

        CREATE TABLE IF NOT EXISTS shared_companies (
          id uuid PRIMARY KEY,
          name varchar(500) NOT NULL,
          name_en varchar(500),
          country varchar(100),
          region varchar(100),
          city varchar(100),
          address text,
          website varchar(500),
          domain varchar(255),
          industry varchar(200),
          industry_tags jsonb NOT NULL DEFAULT '[]',
          employee_count varchar(50),
          annual_revenue varchar(100),
          established_year int,
          export_countries jsonb NOT NULL DEFAULT '[]',
          product_keywords jsonb NOT NULL DEFAULT '[]',
          hs_codes jsonb NOT NULL DEFAULT '[]',
          data_completeness numeric(3,2) NOT NULL DEFAULT 0,
          last_enriched_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_shared_companies_domain
          ON shared_companies(domain)
          WHERE domain IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_shared_companies_name_trgm
          ON shared_companies USING gin (name gin_trgm_ops);
        DROP TRIGGER IF EXISTS set_updated_at ON shared_companies;
        CREATE TRIGGER set_updated_at
          BEFORE UPDATE ON shared_companies
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

        CREATE TABLE IF NOT EXISTS company_sources (
          id uuid PRIMARY KEY,
          company_id uuid NOT NULL REFERENCES shared_companies(id),
          source_type varchar(20) NOT NULL CHECK (source_type IN ('waimao_tong','tengdao','lixiaoyun')),
          source_id varchar(200) NOT NULL,
          raw_data jsonb NOT NULL DEFAULT '{}',
          first_seen_at timestamptz NOT NULL DEFAULT now(),
          last_synced_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (source_type, source_id)
        );
        CREATE INDEX IF NOT EXISTS idx_company_sources_company ON company_sources(company_id);

        CREATE TABLE IF NOT EXISTS tenant_companies (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES tenants(id),
          company_id uuid NOT NULL REFERENCES shared_companies(id),
          business_status varchar(30) NOT NULL DEFAULT 'pending_score'
            CHECK (business_status IN ('pending_score','scoring','scored','selected','in_plan','contacted','replied','converted','excluded')),
          data_status varchar(30) NOT NULL DEFAULT 'incomplete'
            CHECK (data_status IN ('incomplete','enriching','complete','enrichment_failed')),
          grade char(1) CHECK (grade IN ('S','A','B','C','D')),
          total_score numeric(5,2),
          keyword_id uuid REFERENCES collection_keywords(id),
          collection_task_id uuid REFERENCES collection_tasks(id),
          is_precise_customer boolean NOT NULL DEFAULT false,
          source_marker varchar(30) CHECK (source_marker IS NULL OR source_marker IN ('normal','precise')),
          notes text,
          tags jsonb NOT NULL DEFAULT '[]',
          deleted_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, company_id)
        );
        CREATE INDEX IF NOT EXISTS idx_tenant_companies_tenant_status
          ON tenant_companies(tenant_id, business_status, data_status);
        CREATE INDEX IF NOT EXISTS idx_tenant_companies_grade
          ON tenant_companies(tenant_id, grade);
        DROP TRIGGER IF EXISTS set_updated_at ON tenant_companies;
        CREATE TRIGGER set_updated_at
          BEFORE UPDATE ON tenant_companies
          FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
        ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_select_companies ON tenant_companies
          FOR SELECT USING (tenant_id = current_tenant_id());
        CREATE POLICY tenant_write_companies ON tenant_companies
          FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

        CREATE TABLE IF NOT EXISTS competitor_companies (
          id uuid PRIMARY KEY,
          tenant_id uuid NOT NULL REFERENCES tenants(id),
          shared_company_id uuid REFERENCES shared_companies(id),
          company_name varchar(500) NOT NULL,
          domain varchar(255),
          reason text,
          source_type varchar(20) DEFAULT 'lixiaoyun',
          raw_data jsonb NOT NULL DEFAULT '{}',
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, company_name)
        );
        ALTER TABLE competitor_companies ENABLE ROW LEVEL SECURITY;
        """
    )
