"""T-DF-31 数据模型 V3：clean_companies uuid PK + tenant_companies uuid PK + clean_contacts + competitor 重建。

Revision ID: 20260507_0014
Revises: 20260501_0013
Create Date: 2026-05-07
"""

from alembic import op

revision = "20260507_0014"
down_revision = "20260501_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 步骤 a：删除 0009 创建的 bigserial 版本（以及级联删除依赖它的 FK）
    op.execute(
        """
        DROP TABLE IF EXISTS tenant_companies CASCADE;
        DROP TABLE IF EXISTS clean_companies CASCADE;
        DROP TABLE IF EXISTS competitor_companies CASCADE;
        DROP TABLE IF EXISTS competitor_contacts CASCADE;
        """
    )

    # 步骤 b：创建 clean_companies（uuid PK，V3 全字段 + D-038/D-039 +11 字段）
    op.execute(
        """
        CREATE TABLE clean_companies (
          id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name_normalized       text NOT NULL,
          country_iso3          char(3) NOT NULL CHECK (country_iso3 ~ '^[A-Z]{3}$'),
          name                  text,
          name_en               text,
          country               text,
          domain                text,
          industry              text,
          industry_tags         jsonb DEFAULT '[]',
          product_keywords      jsonb DEFAULT '[]',
          product_tags          text[] DEFAULT '{}',
          incorporation_date    date,
          reg_capital           text,
          employee_scale        text,
          employee_count        varchar(50),
          employee_num          int,
          trade_amount_3y_usd   numeric,
          trade_count           int,
          contacts_count        int DEFAULT 0,
          data_completeness     numeric(3,2) DEFAULT 0,
          factory_type          text,
          has_china_pcb_supplier boolean DEFAULT false,
          sources               text[] DEFAULT '{}',
          last_updated          timestamptz DEFAULT now(),
          created_at            timestamptz DEFAULT now(),
          UNIQUE (name_normalized, country_iso3)
        );
        CREATE UNIQUE INDEX uq_clean_companies_domain
          ON clean_companies(domain)
          WHERE domain IS NOT NULL;
        """
    )

    # 步骤 c：创建 tenant_companies（uuid PK，完整 V3 schema）
    op.execute(
        """
        CREATE TABLE tenant_companies (
          id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id           uuid NOT NULL REFERENCES tenants(id),
          clean_company_id    uuid NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
          business_status     varchar(30) NOT NULL DEFAULT 'pending_score'
            CHECK (business_status IN ('pending_score','scoring','scored','selected','in_plan','contacted','replied','converted','excluded')),
          data_status         varchar(30) NOT NULL DEFAULT 'incomplete'
            CHECK (data_status IN ('incomplete','enriching','complete','enrichment_failed')),
          grade               char(1) CHECK (grade IN ('S','A','B','C','D')),
          total_score         numeric(5,2),
          is_precise_customer boolean NOT NULL DEFAULT false,
          matched_keywords    jsonb DEFAULT '[]',
          source_marker       varchar(30) CHECK (source_marker IS NULL OR source_marker IN ('normal','precise')),
          notes               text,
          tags                jsonb DEFAULT '[]',
          deleted_at          timestamptz,
          created_at          timestamptz NOT NULL DEFAULT now(),
          updated_at          timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, clean_company_id)
        );
        CREATE INDEX idx_tenant_companies_tenant_status
          ON tenant_companies(tenant_id, business_status, data_status);
        CREATE INDEX idx_tenant_companies_grade
          ON tenant_companies(tenant_id, grade);
        CREATE INDEX idx_tenant_companies_matched_keywords
          ON tenant_companies USING gin(matched_keywords);
        ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_select_companies ON tenant_companies
          FOR SELECT USING (tenant_id = current_tenant_id());
        CREATE POLICY tenant_write_companies ON tenant_companies
          FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
        """
    )

    # 步骤 d：创建 clean_contacts
    op.execute(
        """
        CREATE TABLE clean_contacts (
          id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          clean_company_id uuid NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
          name             text,
          email            text,
          phone            text,
          position         text,
          is_valid_email   boolean,
          sources          text[] DEFAULT '{}',
          created_at       timestamptz DEFAULT now(),
          last_updated     timestamptz DEFAULT now()
        );
        CREATE INDEX idx_clean_contacts_company ON clean_contacts(clean_company_id);
        CREATE INDEX idx_clean_contacts_email ON clean_contacts(email) WHERE email IS NOT NULL;
        """
    )

    # 步骤 e：重建 competitor_companies（V3 schema，匹配 collection_service.py）
    op.execute(
        """
        CREATE TABLE competitor_companies (
          id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id        uuid NOT NULL REFERENCES tenants(id),
          company_name     varchar(500) NOT NULL,
          company_name_en  varchar(500),
          source_id        text,
          domain           varchar(255),
          reason           text,
          source_type      varchar(20) DEFAULT 'lixiaoyun',
          esdate           date,
          legalperson      text,
          reg_capital      text,
          paid_capital     text,
          reg_address      text,
          contact_address  text,
          employee_scale   text,
          uncid            text,
          raw_data         jsonb DEFAULT '{}',
          updated_at       timestamptz DEFAULT now(),
          created_at       timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, company_name)
        );
        ALTER TABLE competitor_companies ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_select_competitor_companies ON competitor_companies
          FOR SELECT USING (tenant_id = current_tenant_id());
        CREATE POLICY tenant_write_competitor_companies ON competitor_companies
          FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
        """
    )

    # 步骤 f：重建 competitor_contacts（V3 schema）
    op.execute(
        """
        CREATE TABLE competitor_contacts (
          id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          competitor_id  uuid NOT NULL REFERENCES competitor_companies(id) ON DELETE CASCADE,
          tenant_id      uuid NOT NULL,
          name           text,
          phone          text,
          position       text,
          email          text,
          raw_data       jsonb DEFAULT '{}',
          created_at     timestamptz NOT NULL DEFAULT now()
        );
        ALTER TABLE competitor_contacts ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_select_competitor_contacts ON competitor_contacts
          FOR SELECT USING (tenant_id = current_tenant_id());
        CREATE POLICY tenant_write_competitor_contacts ON competitor_contacts
          FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
        """
    )

    # 步骤 g：恢复被 CASCADE 删除的 FK 约束（使用 DO $$ 异常捕获避免重复报错）
    op.execute(
        """
        DO $$ BEGIN
          ALTER TABLE sending_plan_recipients
            ADD CONSTRAINT fk_spr_tenant_company
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;

        DO $$ BEGIN
          ALTER TABLE scoring_jobs
            ADD CONSTRAINT fk_scoring_jobs_tenant_company
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;

        DO $$ BEGIN
          ALTER TABLE company_scores
            ADD CONSTRAINT fk_company_scores_tenant_company
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;

        DO $$ BEGIN
          ALTER TABLE tenant_contacts
            ADD CONSTRAINT fk_tenant_contacts_tenant_company
            FOREIGN KEY (tenant_company_id) REFERENCES tenant_companies(id) ON DELETE CASCADE;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def downgrade() -> None:
    # 删除 V3 版本表
    op.execute(
        """
        DROP TABLE IF EXISTS competitor_contacts CASCADE;
        DROP TABLE IF EXISTS competitor_companies CASCADE;
        DROP TABLE IF EXISTS clean_contacts CASCADE;
        DROP TABLE IF EXISTS tenant_companies CASCADE;
        DROP TABLE IF EXISTS clean_companies CASCADE;
        """
    )

    # 恢复 0009 的 bigserial 版本
    op.execute(
        """
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
        """
    )
