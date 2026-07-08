-- ClientGet Backend Canonical Schema Draft
-- PostgreSQL 16+
-- This file is a blueprint for Alembic migrations, not a one-shot production migration.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

-- Helpers ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS uuid AS $$
  SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

-- 公司名标准化函数（0009 新增，cleanup_service UPSERT 去重使用）-----------------
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

-- Platform auth ----------------------------------------------------------------
CREATE TABLE platform_users (
  id uuid PRIMARY KEY,
  email varchar(255) NOT NULL UNIQUE,
  password_hash varchar(255) NOT NULL,
  name varchar(100) NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  failed_login_count int NOT NULL DEFAULT 0,
  locked_until timestamptz,
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON platform_users FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE tenants (
  id uuid PRIMARY KEY,
  name varchar(100) NOT NULL,
  slug varchar(50) NOT NULL UNIQUE,
  industry varchar(100) NOT NULL,
  contact_name varchar(100),
  contact_phone varchar(50),
  contact_email varchar(255),
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','archived')),
  settings jsonb NOT NULL DEFAULT '{}',
  needs_onboarding boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE users (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email varchar(255) NOT NULL,
  password_hash varchar(255) NOT NULL,
  name varchar(100) NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  must_change_pwd boolean NOT NULL DEFAULT true,
  failed_login_count int NOT NULL DEFAULT 0,
  locked_until timestamptz,
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TYPE user_role AS ENUM ('admin','operator','viewer');
CREATE TABLE user_roles (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role user_role NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id, role)
);

-- Platform configuration -------------------------------------------------------
CREATE TABLE data_sources (
  id uuid PRIMARY KEY,
  source_type varchar(20) NOT NULL UNIQUE CHECK (source_type IN ('waimao_tong','tengdao','lixiaoyun')),
  name varchar(100) NOT NULL,
  alias_code varchar(20) NOT NULL,
  purpose text,
  is_active boolean NOT NULL DEFAULT true,
  config jsonb NOT NULL DEFAULT '{}',
  landing_rules jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON data_sources FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE data_source_credentials (
  id uuid PRIMARY KEY,
  source_type varchar(20) NOT NULL REFERENCES data_sources(source_type),
  account_no varchar(50) NOT NULL,
  username varchar(200) NOT NULL,
  credentials_encrypted text NOT NULL,
  encryption_key_version int NOT NULL DEFAULT 1,
  rotation_order int NOT NULL DEFAULT 0,
  daily_quota int,
  current_day_used int NOT NULL DEFAULT 0,
  current_day_reset_at date,
  is_active boolean NOT NULL DEFAULT true,
  last_used_at timestamptz,
  last_error_at timestamptz,
  last_error_message text,
  consecutive_error_count int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_type, account_no)
);
CREATE INDEX idx_data_source_credentials_active ON data_source_credentials(source_type, rotation_order) WHERE is_active;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON data_source_credentials FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE platform_scoring_templates (
  id uuid PRIMARY KEY,
  industry varchar(100) NOT NULL,
  name varchar(200) NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  dimensions jsonb NOT NULL,
  grade_thresholds jsonb NOT NULL DEFAULT '{"S":90,"A":80,"B":60,"C":40,"D":0}',
  version int NOT NULL DEFAULT 1,
  created_by uuid REFERENCES platform_users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_platform_scoring_templates_active ON platform_scoring_templates(industry) WHERE is_active;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON platform_scoring_templates FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE platform_scoring_template_versions (
  id uuid PRIMARY KEY,
  template_id uuid NOT NULL REFERENCES platform_scoring_templates(id),
  version int NOT NULL,
  dimensions jsonb NOT NULL,
  grade_thresholds jsonb NOT NULL,
  changed_by uuid REFERENCES platform_users(id),
  change_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (template_id, version)
);

CREATE TABLE platform_email_templates (
  id uuid PRIMARY KEY,
  industry varchar(100) NOT NULL,
  name varchar(200) NOT NULL,
  description text,
  category varchar(50) NOT NULL,
  subject text NOT NULL,
  body_html text NOT NULL,
  body_text text,
  variables jsonb NOT NULL DEFAULT '[]',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_platform_email_templates_industry ON platform_email_templates(industry, category) WHERE is_active;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON platform_email_templates FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE warmup_rules (
  id uuid PRIMARY KEY,
  name varchar(100) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  min_observation_emails int NOT NULL DEFAULT 20,
  bounce_alert_rate numeric(5,4) NOT NULL DEFAULT 0.05,
  config jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_warmup_rules_active ON warmup_rules(is_active) WHERE is_active;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON warmup_rules FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE warmup_rule_levels (
  id uuid PRIMARY KEY,
  rule_id uuid NOT NULL REFERENCES warmup_rules(id) ON DELETE CASCADE,
  level int NOT NULL CHECK (level >= 1),
  daily_limit int NOT NULL,
  min_stay_days int NOT NULL DEFAULT 1,
  min_delivery_rate numeric(5,4) NOT NULL DEFAULT 0.95,
  max_bounce_rate numeric(5,4) NOT NULL DEFAULT 0.02,
  max_complaint_rate numeric(5,4) NOT NULL DEFAULT 0.001,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (rule_id, level)
);

CREATE TABLE ai_models (
  id uuid PRIMARY KEY,
  provider varchar(50) NOT NULL DEFAULT 'openrouter',
  model_id varchar(150) NOT NULL,
  display_name varchar(100) NOT NULL,
  -- model_type 已由 0013 删除；input_price / output_price 已由 0011 删除
  is_active boolean NOT NULL DEFAULT true,
  config jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, model_id)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON ai_models FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE ai_scene_defaults (
  id uuid PRIMARY KEY,
  scene varchar(40) NOT NULL UNIQUE CHECK (scene IN ('scoring','email_generation','intelligence_summary','data_analysis')),
  model_id uuid NOT NULL REFERENCES ai_models(id),
  -- fallback_model_ids 已由 0013 删除
  config jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON ai_scene_defaults FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- Tenant AI provider configuration ---------------------------------------------
CREATE TABLE tenant_ai_provider_configs (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider varchar(40) NOT NULL CHECK (provider IN ('openrouter')),
  api_key_encrypted text NOT NULL,
  encryption_key_version int NOT NULL DEFAULT 1,
  configured_by_user_id uuid REFERENCES users(id),
  configured_by_platform_user_id uuid REFERENCES platform_users(id),
  last_rotated_at timestamptz NOT NULL DEFAULT now(),
  balance_status varchar(30) NOT NULL CHECK (balance_status IN ('available','insufficient_balance','unknown','invalid_api_key','provider_error')),
  balance_source varchar(20) CHECK (balance_source IN ('credits','key')),
  balance_amount numeric(12,4),
  balance_currency varchar(10) NOT NULL DEFAULT 'USD',
  total_credits numeric(12,4),
  total_usage numeric(12,4),
  key_limit numeric(12,4),
  key_limit_remaining numeric(12,4),
  balance_checked_at timestamptz,
  last_error_code varchar(100),
  last_error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider)
);
CREATE INDEX idx_tenant_ai_provider_configs_tenant ON tenant_ai_provider_configs(tenant_id);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_ai_provider_configs FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE ai_usage_logs (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid REFERENCES users(id),
  model_id uuid NOT NULL REFERENCES ai_models(id),
  usage_type varchar(40) NOT NULL CHECK (usage_type IN ('scoring','email_generation','intelligence_summary','data_analysis')),
  entity_type varchar(50),
  entity_id uuid,
  input_tokens int NOT NULL DEFAULT 0,
  output_tokens int NOT NULL DEFAULT 0,
  total_tokens int NOT NULL DEFAULT 0,
  estimated_cost numeric(12,4),
  actual_cost numeric(12,4),
  status varchar(20) NOT NULL CHECK (status IN ('pending','completed','failed')),
  provider_response jsonb,
  idempotency_key varchar(200),
  provider_request_id varchar(200),
  latency_ms int,
  error_code varchar(100),
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX idx_ai_usage_logs_tenant ON ai_usage_logs(tenant_id, created_at DESC);

-- Clean companies pool (V3 D-008=B，0014 重建) --------------------------------
CREATE TABLE clean_companies (
  id                     bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name                   text,
  name_normalized        text NOT NULL,
  country_iso3           char(3) CHECK (country_iso3 IS NULL OR country_iso3 ~ '^[A-Z]{3}$'),
  website                text,
  tax_no                 text,
  incorporation_date     date,
  reg_capital            numeric,
  employee_num           text,
  industry_desc          text,
  industry_tags          text[] DEFAULT '{}',
  product_tags           text[] DEFAULT '{}',
  pcb_suppliers          text[] DEFAULT '{}',
  trade_amount_3y_usd    numeric,
  trade_count            int,
  contacts_count         int DEFAULT 0,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name_normalized, country_iso3)
);
CREATE INDEX idx_clean_companies_country ON clean_companies(country_iso3);
CREATE INDEX idx_clean_companies_incorporation_date ON clean_companies(incorporation_date);
CREATE INDEX idx_clean_companies_reg_capital ON clean_companies(reg_capital);
CREATE INDEX idx_clean_companies_industry_tags ON clean_companies USING gin(industry_tags);
CREATE INDEX idx_clean_companies_product_tags ON clean_companies USING gin(product_tags);
CREATE INDEX idx_clean_companies_employee_num ON clean_companies(employee_num);
CREATE INDEX idx_clean_companies_trade_amount ON clean_companies(trade_amount_3y_usd);
CREATE INDEX idx_clean_companies_trade_count ON clean_companies(trade_count);
CREATE INDEX idx_clean_companies_contacts_count ON clean_companies(contacts_count);

-- 原始联系人池（shared_contacts 保留但不再被代码引用，Slice 2 已完成）-----------
-- 注：0009 DROP shared_companies CASCADE 后 company_id FK 已移除；
--     0015 Slice 2 将 tenant_contacts.contact_id 改为 clean_contact_id → clean_contacts(id)，
--     shared_contacts 不再有 FK 引用，保留供历史查询。
CREATE TABLE shared_contacts (
  id uuid PRIMARY KEY,
  company_id uuid,                                           -- FK 已移除（shared_companies 已删除）；Slice 2 迁移为 clean_company_id
  name varchar(200),
  name_en varchar(200),
  email varchar(255),
  phone varchar(50),
  title varchar(200),
  department varchar(100),
  seniority_level varchar(30),
  source_type varchar(20) NOT NULL CHECK (source_type IN ('waimao_tong','tengdao','lixiaoyun')),
  source_contact_id varchar(200),
  raw_data jsonb NOT NULL DEFAULT '{}',
  is_valid_email boolean,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, email),
  UNIQUE (company_id, source_type, source_contact_id)
);
CREATE INDEX idx_shared_contacts_company ON shared_contacts(company_id);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON shared_contacts FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- 清洗后联系人（0014 新增，与 clean_companies 关联）--------------------------
CREATE TABLE clean_contacts (
  id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  clean_company_id bigint NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
  name             text,
  position         text,
  email            citext,
  phone            text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_clean_contacts_company ON clean_contacts(clean_company_id);
CREATE INDEX idx_clean_contacts_email ON clean_contacts(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX uq_clean_contacts_company_email ON clean_contacts(clean_company_id, email) WHERE email IS NOT NULL;

CREATE TABLE clean_company_sources (
  id               bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  clean_company_id bigint NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
  source_type      text NOT NULL CHECK (source_type IN ('tendata','waimaotong')),
  source_company_id bigint NOT NULL,
  source_key       text,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_type, source_company_id)
);
CREATE INDEX idx_clean_company_sources_company ON clean_company_sources(clean_company_id);
CREATE INDEX idx_clean_company_sources_type ON clean_company_sources(source_type);

-- Keyword Master（0016 新增）-------------------------------------------------
-- keyword_master：全平台去重关键词主表，归一化后全局唯一
CREATE TABLE keyword_master (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  keyword             text NOT NULL,
  keyword_normalized  text NOT NULL UNIQUE,
  created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_keyword_master_normalized ON keyword_master(keyword_normalized);

-- tenant_keyword：租户订阅的关键词关联表（0016 新增）
CREATE TABLE tenant_keyword (
  id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  keyword_master_id   uuid NOT NULL REFERENCES keyword_master(id) ON DELETE CASCADE,
  keyword_raw         text NOT NULL,
  created_by          uuid REFERENCES users(id),
  created_at          timestamptz NOT NULL DEFAULT now(),
  status              text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted')),
  UNIQUE (tenant_id, keyword_master_id)
);
CREATE INDEX idx_tenant_keyword_tenant_status ON tenant_keyword(tenant_id, status);
CREATE INDEX idx_tenant_keyword_master ON tenant_keyword(keyword_master_id);

CREATE TABLE clean_company_keywords (
  id                bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  clean_company_id  bigint NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
  keyword_master_id uuid NOT NULL REFERENCES keyword_master(id) ON DELETE CASCADE,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (clean_company_id, keyword_master_id)
);
CREATE INDEX idx_clean_company_keywords_keyword ON clean_company_keywords(keyword_master_id);

-- Collection ------------------------------------------------------------------
-- collection_keywords：0009 重写（去除 countries/countries_hash/source_types）
CREATE TABLE collection_keywords (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  keyword text NOT NULL,
  keyword_normalized text NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','deleted')),
  daily_limit int,
  last_scheduled_at timestamptz,
  created_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  -- 0009 新增：采集进度跟踪字段
  subscription_status text DEFAULT 'not_started',
  current_page        int DEFAULT 0,
  total_pages         int DEFAULT 0,
  today_pages         int DEFAULT 0,
  last_run_date       date,
  daily_page_limit    int DEFAULT 10,
  stage1_today_count  int DEFAULT 0,
  stage1_total_count  int DEFAULT 0,
  last_stage1_date    date,
  stage1_status       text DEFAULT 'not_started',
  daily_stage1_limit  int DEFAULT 1000,
  stage2_today_count  int DEFAULT 0,
  stage2_total_count  int DEFAULT 0,
  last_stage2_date    date,
  stage2_status       text DEFAULT 'not_started',
  daily_stage2_limit  int DEFAULT 100,
  total_companies     int DEFAULT 0,
  total_contacts      int DEFAULT 0,
  error_msg           text,
  started_at          timestamptz,
  -- 0017 新增：关联 keyword_master（允许 NULL，逐步迁移）
  keyword_master_id   uuid REFERENCES keyword_master(id) ON DELETE SET NULL,
  UNIQUE (tenant_id, keyword_normalized)
);
CREATE INDEX idx_collection_keywords_sched ON collection_keywords(status, keyword_normalized);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON collection_keywords FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE collection_runs (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  keyword_master_id uuid REFERENCES keyword_master(id) ON DELETE SET NULL,
  provider text NOT NULL CHECK (provider IN ('lixiaoyun', 'tendata')),
  stage text NOT NULL CHECK (stage IN ('lixiaoyun_competitors', 'tendata_customers')),
  status text NOT NULL DEFAULT 'not_started'
    CHECK (status IN ('not_started','running','daily_limit_reached','completed','stopped','failed')),
  daily_limit int NOT NULL DEFAULT 1000,
  request_page_size int NOT NULL DEFAULT 10,
  cursor jsonb NOT NULL DEFAULT '{}'::jsonb,
  skip_source_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  total_fetched int NOT NULL DEFAULT 0,
  today_fetched int NOT NULL DEFAULT 0,
  biz_date date NOT NULL DEFAULT ((now() AT TIME ZONE 'Asia/Shanghai')::date),
  next_run_at timestamptz,
  manual_stopped_at timestamptz,
  completed_at timestamptz,
  error_message text,
  triggered_by uuid REFERENCES users(id) ON DELETE SET NULL,
  triggered_tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (provider = 'lixiaoyun' AND stage = 'lixiaoyun_competitors')
    OR
    (provider = 'tendata' AND stage = 'tendata_customers')
  )
);
CREATE INDEX idx_collection_runs_keyword_stage_status
  ON collection_runs(keyword_master_id, provider, stage, status);
CREATE INDEX idx_collection_runs_resume ON collection_runs(next_run_at) WHERE status='daily_limit_reached';
CREATE INDEX idx_collection_runs_triggered_tenant
  ON collection_runs(triggered_tenant_id)
  WHERE triggered_tenant_id IS NOT NULL;
CREATE UNIQUE INDEX uq_collection_runs_active
  ON collection_runs(keyword_master_id, provider, stage)
  WHERE status IN ('not_started','running','daily_limit_reached');
CREATE TRIGGER set_updated_at BEFORE UPDATE ON collection_runs FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE collection_tasks (
  id uuid PRIMARY KEY,
  run_id bigint REFERENCES collection_runs(id) ON DELETE SET NULL,
  keyword text NOT NULL,
  keyword_normalized text NOT NULL,
  countries jsonb NOT NULL DEFAULT '[]',
  countries_hash varchar(64) NOT NULL,
  source_types jsonb NOT NULL,
  task_type varchar(50) NOT NULL DEFAULT 'competitor_search',  -- 0007
  context jsonb NOT NULL DEFAULT '{}',                          -- 0007
  status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','cancelled')),
  priority int NOT NULL DEFAULT 0,
  lease_id uuid,
  lease_owner varchar(100),
  lease_expires_at timestamptz,
  attempt_count int NOT NULL DEFAULT 0,
  max_attempts int NOT NULL DEFAULT 3,
  result_summary jsonb NOT NULL DEFAULT '{}',
  error_message text,
  scheduled_at timestamptz NOT NULL DEFAULT now(),
  scheduled_biz_date date,
  batch_no int NOT NULL DEFAULT 1,
  page_size int NOT NULL DEFAULT 10,
  cursor_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_collection_tasks_claim ON collection_tasks(status, priority DESC, scheduled_at) WHERE status='pending';
CREATE INDEX idx_collection_tasks_lease ON collection_tasks(lease_id) WHERE lease_id IS NOT NULL;
CREATE INDEX idx_collection_tasks_type ON collection_tasks(task_type, status) WHERE status='pending';  -- 0007
CREATE INDEX idx_collection_tasks_run ON collection_tasks(run_id);
CREATE INDEX idx_collection_tasks_run_status_scheduled ON collection_tasks(run_id, status, scheduled_at);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON collection_tasks FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE collection_task_keywords (
  id uuid PRIMARY KEY,
  task_id uuid NOT NULL REFERENCES collection_tasks(id) ON DELETE CASCADE,
  keyword_id uuid NOT NULL REFERENCES collection_keywords(id),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (task_id, keyword_id)
);
CREATE INDEX idx_collection_task_keywords_task ON collection_task_keywords(task_id);
CREATE INDEX idx_collection_task_keywords_tenant ON collection_task_keywords(tenant_id);

-- 原始数据表（0009 新增，0042 删除 13 列，0043 删除 20 列，0044 补齐线上 18 列）--
-- 线上真实 33 列（反映 0042+0043 删除 + 0044 补齐后的最终状态）
CREATE TABLE waimaotong_raw_companies (
  id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  -- 原有 15 列（0042/0043 删除后剩余）
  real_id             text,
  name                text,
  domain              text,
  industry            text,
  phone               text,
  employee_size       text,
  founded_year        int,
  description         text,
  products            text[],
  source_tags         text[],
  contacts_count      int,
  detail_status       text NOT NULL DEFAULT 'pending'
    CHECK (detail_status IN ('pending','fetched','failed','skipped')),
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now(),
  -- 线上新增 18 列（0044 补齐）
  company_id          text,
  sys_company_id      uuid,
  api_company_id      text,
  company_name        text,
  country             text,
  source_type         text,
  source_keyword      text,
  source_competitor   text,
  id_verified         boolean,
  plan_id             int,
  full_address        text,
  website             text,
  has_detail          boolean,
  has_contacts        boolean,
  email_count         int,
  detail_raw_data     text,
  raw_data            text,
  error_msg           text
);
CREATE INDEX idx_wmt_raw_companies_domain ON waimaotong_raw_companies(domain) WHERE domain IS NOT NULL;

CREATE TABLE tendata_raw_companies (
  id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  keyword_master_id   uuid REFERENCES keyword_master(id) ON DELETE SET NULL,
  source_id           text NOT NULL,
  collection_type     text NOT NULL DEFAULT 'reverse_lookup'
    CHECK (collection_type IN ('direct_search','reverse_lookup')),
  globiz_id           text,
  name                text,
  name_local          text,
  country_iso3        char(3) CHECK (country_iso3 IS NULL OR country_iso3 ~ '^[A-Z]{3}$'),
  website             text,
  tax_no              text,
  incorporation_date  date,
  employee_num        text,
  industry_desc       text,
  product_tags        text[],
  pcb_suppliers       text[],
  trade_amount_3y_usd numeric,
  trade_count         int,
  contacts_count      int,
  has_trade_data      boolean,
  aliases             text[],
  raw_payload         jsonb,
  detail_status       text NOT NULL DEFAULT 'pending'
    CHECK (detail_status IN ('pending','fetched','failed','skipped')),
  detail_fetched_at   timestamptz,
  trade_status        text NOT NULL DEFAULT 'pending'
    CHECK (trade_status IN ('pending','fetched','failed','skipped')),
  trade_fetched_at    timestamptz,
  contacts_status     text NOT NULL DEFAULT 'pending'
    CHECK (contacts_status IN ('pending','fetched','failed','skipped')),
  contacts_fetched_at timestamptz,
  enrichment_error    jsonb,
  created_at          timestamptz DEFAULT now(),
  UNIQUE (keyword_master_id, source_id, collection_type)
);
CREATE INDEX idx_tendata_raw_companies_keyword ON tendata_raw_companies(keyword_master_id);
CREATE INDEX idx_tendata_raw_companies_source ON tendata_raw_companies(source_id);
CREATE INDEX idx_tendata_raw_companies_globiz ON tendata_raw_companies(globiz_id) WHERE globiz_id IS NOT NULL;
CREATE INDEX idx_tendata_raw_companies_country ON tendata_raw_companies(country_iso3);

CREATE TABLE tendata_raw_contacts (
  id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  raw_company_id      bigint NOT NULL REFERENCES tendata_raw_companies(id) ON DELETE CASCADE,
  source_contact_id   text,
  name                text,
  position            text,
  email               citext,
  phone               text,
  raw_payload         jsonb,
  created_at          timestamptz DEFAULT now()
);
CREATE INDEX idx_tendata_raw_contacts_company ON tendata_raw_contacts(raw_company_id);
CREATE UNIQUE INDEX uq_tendata_raw_contacts_source_contact
  ON tendata_raw_contacts(raw_company_id, source_contact_id)
  WHERE source_contact_id IS NOT NULL;
CREATE UNIQUE INDEX uq_tendata_raw_contacts_email_fallback
  ON tendata_raw_contacts(raw_company_id, email)
  WHERE source_contact_id IS NULL AND email IS NOT NULL;
CREATE INDEX idx_tendata_raw_contacts_email
  ON tendata_raw_contacts(email)
  WHERE email IS NOT NULL;

CREATE TABLE lixiaoyun_raw_companies (
  id                bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  keyword_master_id uuid REFERENCES keyword_master(id) ON DELETE SET NULL,
  source_id         text NOT NULL,
  name              text,
  english_name      text,
  domain            text,
  esdate            date,
  legalperson       text,
  uncid             text,
  reg_capital       text,
  employee_scale    text,
  reg_address       text,
  raw_payload       jsonb,
  created_at        timestamptz DEFAULT now(),
  UNIQUE (keyword_master_id, source_id)
);
CREATE INDEX idx_lxy_raw_companies_keyword ON lixiaoyun_raw_companies(keyword_master_id);
CREATE INDEX idx_lxy_raw_companies_source ON lixiaoyun_raw_companies(source_id);

CREATE TABLE lixiaoyun_raw_contacts (
  id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  raw_company_id      bigint NOT NULL REFERENCES lixiaoyun_raw_companies(id) ON DELETE CASCADE,
  source_contact_id   text,
  name                text,
  position            text,
  email               citext,
  phone               text,
  raw_payload         jsonb,
  created_at          timestamptz DEFAULT now()
);
CREATE INDEX idx_lxy_raw_contacts_company ON lixiaoyun_raw_contacts(raw_company_id);
CREATE UNIQUE INDEX uq_lxy_raw_contacts_source_contact
  ON lixiaoyun_raw_contacts(raw_company_id, source_contact_id)
  WHERE source_contact_id IS NOT NULL;
CREATE UNIQUE INDEX uq_lxy_raw_contacts_email_fallback
  ON lixiaoyun_raw_contacts(raw_company_id, email)
  WHERE source_contact_id IS NULL AND email IS NOT NULL;
CREATE INDEX idx_lxy_raw_contacts_email
  ON lixiaoyun_raw_contacts(email)
  WHERE email IS NOT NULL;

-- 清洗队列（0009 新增，cleanup_service 消费）----------------------------------
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

CREATE OR REPLACE FUNCTION enqueue_tendata_raw_company_cleanup()
RETURNS trigger AS $$
BEGIN
  INSERT INTO cleanup_queue (raw_table, raw_row_id, status)
  VALUES ('tendata_raw_companies', NEW.id, 'pending')
  ON CONFLICT (raw_table, raw_row_id) DO NOTHING;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tendata_raw_companies_enqueue_cleanup_after_insert
AFTER INSERT ON tendata_raw_companies
FOR EACH ROW
EXECUTE FUNCTION enqueue_tendata_raw_company_cleanup();

-- Tenant company and scoring (V3 T-DF-31，0014 重建) ---------------------------
CREATE TABLE tenant_companies (
  id                  bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  tenant_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  clean_company_id    bigint NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
  business_status     text NOT NULL DEFAULT 'new',
  data_status         text NOT NULL DEFAULT 'ready',
  model_score         numeric,
  score               numeric,
  note                text,
  tags                text[] DEFAULT '{}',
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, clean_company_id)
);
CREATE INDEX idx_tenant_companies_tenant_business_status
  ON tenant_companies(tenant_id, business_status);
CREATE INDEX idx_tenant_companies_tenant_data_status
  ON tenant_companies(tenant_id, data_status);
CREATE INDEX idx_tenant_companies_tenant_score
  ON tenant_companies(tenant_id, score);
CREATE INDEX idx_tenant_companies_tags
  ON tenant_companies USING gin(tags);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_companies FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_select_companies ON tenant_companies
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_write_companies ON tenant_companies
  FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

CREATE TABLE scoring_templates (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  source_platform_template_id uuid REFERENCES platform_scoring_templates(id),
  name varchar(200) NOT NULL,
  -- C6：行业字段，便于 admin 按行业分组展示（0026）
  industry text NOT NULL DEFAULT 'PCB',
  is_active boolean NOT NULL DEFAULT true,
  dimensions jsonb NOT NULL,
  grade_thresholds jsonb NOT NULL DEFAULT '{"S":90,"A":80,"B":60,"C":40,"D":0}',
  version int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_scoring_templates_active ON scoring_templates(tenant_id) WHERE is_active;
CREATE INDEX idx_scoring_templates_industry ON scoring_templates(industry);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON scoring_templates FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE scoring_template_versions (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  template_id uuid NOT NULL REFERENCES scoring_templates(id),
  version int NOT NULL,
  dimensions jsonb NOT NULL,
  grade_thresholds jsonb NOT NULL,
  changed_by uuid REFERENCES users(id),
  change_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (template_id, version)
);

-- C6：租户评分维度自定义权重（0027）---------------------------------------------
CREATE TABLE tenant_scoring_weights (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  template_id uuid NOT NULL REFERENCES scoring_templates(id) ON DELETE CASCADE,
  dimension   text NOT NULL,
  weight      numeric(5,2) NOT NULL DEFAULT 1.0 CHECK (weight >= 0),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, template_id, dimension)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_scoring_weights
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
CREATE INDEX idx_tenant_scoring_weights_tenant_template
  ON tenant_scoring_weights(tenant_id, template_id);
ALTER TABLE tenant_scoring_weights ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_scoring_weights_select ON tenant_scoring_weights
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_scoring_weights_write ON tenant_scoring_weights
  FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

CREATE TABLE company_scores (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  tenant_company_id uuid NOT NULL REFERENCES tenant_companies(id),
  template_id uuid NOT NULL REFERENCES scoring_templates(id),
  template_version_id uuid NOT NULL REFERENCES scoring_template_versions(id),
  total_score numeric(5,2) NOT NULL,
  grade char(1) NOT NULL CHECK (grade IN ('S','A','B','C','D')),
  dimension_scores jsonb NOT NULL,
  llm_pending boolean NOT NULL DEFAULT false,
  llm_score numeric(5,2),
  llm_reasoning text,
  llm_model_id uuid REFERENCES ai_models(id),
  llm_usage_log_id uuid REFERENCES ai_usage_logs(id),
  is_retry boolean NOT NULL DEFAULT false,
  retry_count int NOT NULL DEFAULT 0,
  related_score_id uuid REFERENCES company_scores(id),
  scored_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_company_scores_unique_non_retry ON company_scores(tenant_company_id, template_version_id) WHERE is_retry=false;
CREATE INDEX idx_company_scores_tenant ON company_scores(tenant_id, scored_at DESC);

-- 评分任务队列（由 0003 创建，F2 补入）---------------------------------------
CREATE TABLE scoring_jobs (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  tenant_company_id uuid NOT NULL REFERENCES tenant_companies(id) ON DELETE CASCADE,
  status varchar(20) NOT NULL CHECK (status IN ('pending','leased','waiting_balance','completed','failed')),
  lease_id uuid,
  lease_owner varchar(100),
  lease_expires_at timestamptz,
  attempt_count int NOT NULL DEFAULT 0,
  last_error text,
  payload jsonb NOT NULL DEFAULT '{}',
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON scoring_jobs FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
CREATE INDEX idx_scoring_jobs_claim ON scoring_jobs(status, lease_expires_at, created_at);
CREATE UNIQUE INDEX idx_scoring_jobs_unique_active ON scoring_jobs(tenant_company_id)
  WHERE completed_at IS NULL AND status IN ('pending','leased','waiting_balance');
ALTER TABLE scoring_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_scoring_jobs_select ON scoring_jobs
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_scoring_jobs_write ON scoring_jobs
  FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

CREATE TABLE contact_rules (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  name varchar(200) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  rules jsonb NOT NULL,
  version int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_contact_rules_active ON contact_rules(tenant_id) WHERE is_active;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON contact_rules FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE company_blacklist (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  shared_company_id uuid,                                    -- FK 已移除（shared_companies 已删除，0009 CASCADE）
  match_domain varchar(255),
  match_name_pattern varchar(500),
  reason text NOT NULL,
  blocked_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (shared_company_id IS NOT NULL OR match_domain IS NOT NULL OR match_name_pattern IS NOT NULL)
);
CREATE INDEX idx_company_blacklist_tenant ON company_blacklist(tenant_id);

-- 竞品公司（0014 重建，V3 schema）--------------------------------------------
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

-- 竞品联系人（0014 重建，V3 schema）------------------------------------------
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
CREATE INDEX idx_competitor_contacts_competitor ON competitor_contacts(competitor_id);
CREATE INDEX idx_competitor_contacts_tenant ON competitor_contacts(tenant_id);

-- Contacts and groups ----------------------------------------------------------
-- 注：0015 Slice 2 将 contact_id → clean_contact_id，FK 改为 clean_contacts(id)，nullable
CREATE TABLE tenant_contacts (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  clean_contact_id bigint NOT NULL REFERENCES clean_contacts(id) ON DELETE CASCADE,
  clean_company_id bigint NOT NULL REFERENCES clean_companies(id) ON DELETE CASCADE,
  contact_status text NOT NULL DEFAULT 'available',
  is_sendable boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_tenant_contacts_clean_contact ON tenant_contacts(tenant_id, clean_contact_id);
CREATE INDEX idx_tenant_contacts_tenant_company ON tenant_contacts(tenant_id, clean_company_id);
CREATE INDEX idx_tenant_contacts_tenant_status ON tenant_contacts(tenant_id, contact_status);
CREATE INDEX idx_tenant_contacts_tenant_sendable ON tenant_contacts(tenant_id, is_sendable);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_contacts FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE groups (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  name varchar(200) NOT NULL,
  description text,
  auto_rules jsonb,
  member_count int NOT NULL DEFAULT 0,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, name)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON groups FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE group_members (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  group_id uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  tenant_company_id uuid NOT NULL REFERENCES tenant_companies(id),
  tenant_contact_id uuid REFERENCES tenant_contacts(id),
  added_by varchar(10) NOT NULL DEFAULT 'manual' CHECK (added_by IN ('manual','auto')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (group_id, tenant_company_id)
);
CREATE INDEX idx_group_members_group ON group_members(group_id);

-- Domains and email ------------------------------------------------------------
CREATE TABLE domain_warmup_status (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  domain varchar(255) NOT NULL,
  spf_record text,
  dkim_record text,
  dmarc_record text,
  verification_status varchar(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','verifying','verified','failed')),
  dns_verified_at timestamptz,
  dns_last_checked_at timestamptz,
  warmup_rule_id uuid REFERENCES warmup_rules(id),
  warmup_level int NOT NULL DEFAULT 1 CHECK (warmup_level >= 1),
  daily_limit int NOT NULL DEFAULT 50,
  total_sent int NOT NULL DEFAULT 0,
  bounce_rate numeric(5,4) DEFAULT 0,
  complaint_rate numeric(5,4) DEFAULT 0,
  open_rate numeric(5,4) DEFAULT 0,
  level_changed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, domain)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON domain_warmup_status FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE domain_warmup_history (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  warmup_status_id uuid NOT NULL REFERENCES domain_warmup_status(id) ON DELETE CASCADE,
  domain varchar(255) NOT NULL,
  warmup_level int NOT NULL,
  daily_limit int NOT NULL,
  total_sent int NOT NULL,
  bounce_rate numeric(5,4),
  complaint_rate numeric(5,4),
  open_rate numeric(5,4),
  change_type varchar(20) NOT NULL CHECK (change_type IN ('level_up','level_down','daily_snapshot','manual_adjust')),
  change_reason text,
  changed_by uuid REFERENCES users(id),
  snapshot_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE domain_daily_usage (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  domain_id uuid NOT NULL REFERENCES domain_warmup_status(id),
  usage_date date NOT NULL,
  daily_limit int NOT NULL,
  reserved_count int NOT NULL DEFAULT 0,
  sent_count int NOT NULL DEFAULT 0,
  failed_count int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (domain_id, usage_date)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON domain_daily_usage FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE email_templates (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  source_type varchar(20) NOT NULL DEFAULT 'custom' CHECK (source_type IN ('custom','platform_copy')),
  platform_template_id uuid REFERENCES platform_email_templates(id),
  name varchar(200) NOT NULL,
  category varchar(50) NOT NULL,
  subject text NOT NULL,
  body_html text NOT NULL,
  body_text text,
  variables jsonb NOT NULL DEFAULT '[]',
  is_ai_generated boolean NOT NULL DEFAULT false,
  ai_prompt text,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON email_templates FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE work_rule_sets (
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
CREATE UNIQUE INDEX idx_work_rule_sets_one_default ON work_rule_sets(is_default) WHERE is_default;
CREATE TRIGGER set_updated_at BEFORE UPDATE ON work_rule_sets FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE countries (
  iso3 char(3) PRIMARY KEY,
  name_zh text NOT NULL,
  name_en text NOT NULL,
  timezone text NOT NULL,
  rule_set_id uuid REFERENCES work_rule_sets(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (iso3 ~ '^[A-Z]{3}$')
);
CREATE INDEX idx_countries_rule_set ON countries(rule_set_id);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON countries FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE country_holidays (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_iso3 char(3) NOT NULL REFERENCES countries(iso3) ON DELETE CASCADE,
  date date NOT NULL,
  name text,
  source varchar(20) NOT NULL DEFAULT 'manual',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (country_iso3, date)
);
CREATE INDEX idx_country_holidays_country_date ON country_holidays(country_iso3, date);

CREATE TABLE sending_plans (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  created_by uuid NOT NULL REFERENCES users(id),
  name varchar(200) NOT NULL,
  description text,
  status varchar(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','scheduled','running','paused','completed','cancelled')),
  recipient_source varchar(20) NOT NULL CHECK (recipient_source IN ('group','manual','filter')),
  recipient_config jsonb NOT NULL,
  send_strategy jsonb NOT NULL DEFAULT '{"interval_seconds":[3,3]}',
  sender_name varchar(200),
  sender_email varchar(255),
  domain_id uuid REFERENCES domain_warmup_status(id),
  total_recipients int NOT NULL DEFAULT 0,
  sent_count int NOT NULL DEFAULT 0,
  scheduled_at timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_sending_plans_tenant_status ON sending_plans(tenant_id, status);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON sending_plans FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE sending_plan_recipients (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  plan_id uuid NOT NULL REFERENCES sending_plans(id) ON DELETE CASCADE,
  tenant_company_id uuid NOT NULL REFERENCES tenant_companies(id),
  tenant_contact_id uuid NOT NULL REFERENCES tenant_contacts(id),
  source_type varchar(20) NOT NULL CHECK (source_type IN ('group','manual','filter')),
  source_ref uuid,
  locked_at timestamptz NOT NULL DEFAULT now(),
  appended_after_start boolean NOT NULL DEFAULT false,
  excluded_at timestamptz,
  excluded_reason varchar(100),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plan_id, tenant_contact_id)
);
CREATE INDEX idx_sending_plan_recipients_plan ON sending_plan_recipients(plan_id);

CREATE TABLE sequence_steps (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  plan_id uuid NOT NULL REFERENCES sending_plans(id) ON DELETE CASCADE,
  step_number int NOT NULL CHECK (step_number BETWEEN 1 AND 10),
  template_id uuid NOT NULL REFERENCES email_templates(id),
  delay_days int NOT NULL DEFAULT 0,
  condition_type varchar(20) NOT NULL DEFAULT 'no_reply' CHECK (condition_type IN ('always','no_reply','no_open','opened','clicked')),
  use_ai_personalization boolean NOT NULL DEFAULT false,
  ai_instructions text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plan_id, step_number),
  CHECK ((step_number=1 AND condition_type='always' AND delay_days=0) OR step_number > 1)
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON sequence_steps FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE sequence_enrollments (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  plan_id uuid NOT NULL REFERENCES sending_plans(id),
  plan_recipient_id uuid NOT NULL REFERENCES sending_plan_recipients(id),
  tenant_contact_id uuid NOT NULL REFERENCES tenant_contacts(id),
  current_step int NOT NULL DEFAULT 1,
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','replied','bounced','unsubscribed','paused','cancelled','failed')),
  send_attempt_count int NOT NULL DEFAULT 0,
  enrolled_at timestamptz NOT NULL DEFAULT now(),
  last_step_sent_at timestamptz,
  next_step_due_at timestamptz,
  last_skip_reason text,
  last_skip_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plan_id, tenant_contact_id)
);
CREATE INDEX idx_sequence_enrollments_due ON sequence_enrollments(status, next_step_due_at) WHERE status='active';
CREATE TRIGGER set_updated_at BEFORE UPDATE ON sequence_enrollments FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE email_send_locks (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  enrollment_id uuid NOT NULL REFERENCES sequence_enrollments(id),
  step_id uuid NOT NULL REFERENCES sequence_steps(id),
  status varchar(20) NOT NULL DEFAULT 'locked' CHECK (status IN ('locked','sent','failed','released')),
  locked_by varchar(100),
  locked_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz,
  email_id uuid,
  email_created_at timestamptz,
  UNIQUE (enrollment_id, step_id)
);

CREATE TABLE emails (
  id uuid NOT NULL,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  plan_id uuid REFERENCES sending_plans(id),
  step_id uuid REFERENCES sequence_steps(id),
  step_number int,
  template_id uuid REFERENCES email_templates(id),
  enrollment_id uuid REFERENCES sequence_enrollments(id),
  tenant_contact_id uuid NOT NULL REFERENCES tenant_contacts(id),
  from_email varchar(255) NOT NULL,
  from_name varchar(200),
  to_email varchar(255) NOT NULL,
  to_name varchar(200),
  subject text NOT NULL,
  body_html text NOT NULL,
  body_text text,
  reply_message_id varchar(200),
  reply_from_email varchar(255),
  reply_subject text,
  reply_body_text text,
  reply_received_at timestamptz,
  status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','queued','sent','delivered','opened','clicked','replied','bounced','complained','unsubscribed','failed')),
  is_ai_personalized boolean NOT NULL DEFAULT false,
  ai_usage_log_id uuid REFERENCES ai_usage_logs(id),
  engagelab_message_id varchar(100),
  scheduled_at timestamptz,
  sent_at timestamptz,
  delivered_at timestamptz,
  opened_at timestamptz,
  clicked_at timestamptz,
  replied_at timestamptz,
  bounced_at timestamptz,
  -- D-041 投递追踪字段（由 migration 20260507_0020 添加）
  first_opened_at timestamptz,
  open_count int NOT NULL DEFAULT 0,
  soft_bounce bool NOT NULL DEFAULT false,
  invalid_email bool NOT NULL DEFAULT false,
  report_spam bool NOT NULL DEFAULT false,
  unsubscribed bool NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_emails_tenant_created ON emails(tenant_id, created_at DESC, id DESC);
CREATE INDEX idx_emails_engagelab ON emails(engagelab_message_id) WHERE engagelab_message_id IS NOT NULL;
CREATE INDEX idx_emails_enrollment ON emails(enrollment_id) WHERE enrollment_id IS NOT NULL;
CREATE INDEX idx_emails_open_tracking ON emails(tenant_id, first_opened_at) WHERE first_opened_at IS NOT NULL;
CREATE INDEX idx_emails_delivery_flags ON emails(tenant_id, soft_bounce, report_spam, unsubscribed) WHERE soft_bounce OR report_spam OR unsubscribed;

CREATE TABLE email_events (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email_id uuid NOT NULL,
  email_created_at timestamptz NOT NULL,
  event_type varchar(20) NOT NULL CHECK (event_type IN ('sent','delivered','opened','clicked','replied','bounced','complained','unsubscribed')),
  metadata jsonb NOT NULL DEFAULT '{}',
  source varchar(20) NOT NULL DEFAULT 'engagelab' CHECK (source IN ('engagelab','system')),
  provider_event_id text,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_email_events_provider_unique ON email_events(source, provider_event_id) WHERE provider_event_id IS NOT NULL;
CREATE INDEX idx_email_events_email ON email_events(email_id, email_created_at);

-- Intelligence ----------------------------------------------------------------
CREATE TABLE intelligence_sources (
  id uuid PRIMARY KEY,
  tenant_id uuid REFERENCES tenants(id),
  name varchar(200) NOT NULL,
  source_type varchar(20) NOT NULL CHECK (source_type IN ('rss','website','manual')),
  url text,
  fetch_config jsonb NOT NULL DEFAULT '{"frequency_hours":24}',
  industry_tags jsonb NOT NULL DEFAULT '[]',
  is_active boolean NOT NULL DEFAULT true,
  last_fetched_at timestamptz,
  error_count int NOT NULL DEFAULT 0,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON intelligence_sources FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE intelligence_articles (
  id uuid NOT NULL,
  source_id uuid,
  title varchar(500) NOT NULL,
  url text,
  author varchar(200),
  published_at timestamptz,
  content_raw text,
  content_summary text,
  ai_category varchar(100),
  ai_tags jsonb NOT NULL DEFAULT '[]',
  ai_relevance_score numeric(3,2),
  ai_model_id uuid REFERENCES ai_models(id),
  ai_usage_log_id uuid REFERENCES ai_usage_logs(id),
  status varchar(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processed','published','archived')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE intelligence_subscriptions (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES users(id),
  industry_tags jsonb NOT NULL DEFAULT '[]',
  min_relevance numeric(3,2) NOT NULL DEFAULT 0.5,
  notify_enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON intelligence_subscriptions FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE intelligence_article_publications (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  article_id uuid NOT NULL,
  article_created_at timestamptz NOT NULL,
  status varchar(20) NOT NULL DEFAULT 'unread' CHECK (status IN ('unread','read','starred','archived')),
  has_summary boolean NOT NULL DEFAULT true,
  read_at timestamptz,
  matched_by varchar(30) CHECK (matched_by IN ('subscription','manual','system')),
  subscription_id uuid REFERENCES intelligence_subscriptions(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, article_id)
);
CREATE INDEX idx_article_publications_tenant ON intelligence_article_publications(tenant_id, status);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON intelligence_article_publications FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- System ----------------------------------------------------------------------
CREATE TABLE notifications (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  user_id uuid NOT NULL REFERENCES users(id),
  title varchar(200) NOT NULL,
  content text NOT NULL,
  category varchar(30) NOT NULL CHECK (category IN ('scoring_complete','plan_complete','reply_received','balance_low','intelligence','domain_warmup','collection','system')),
  entity_type varchar(50),
  entity_id uuid,
  is_read boolean NOT NULL DEFAULT false,
  read_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user_unread ON notifications(tenant_id, user_id, is_read, created_at DESC);

CREATE TABLE audit_logs (
  id uuid NOT NULL,
  tenant_id uuid REFERENCES tenants(id),
  user_id uuid REFERENCES users(id),
  platform_user_id uuid REFERENCES platform_users(id),
  action varchar(30) NOT NULL,
  entity_type varchar(50) NOT NULL,
  entity_id uuid,
  old_value jsonb,
  new_value jsonb,
  ip_address inet,
  user_agent text,
  request_id varchar(100),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE service_idempotency_keys (
  id uuid PRIMARY KEY,
  service_name varchar(100) NOT NULL,
  request_id varchar(200) NOT NULL,
  endpoint varchar(200) NOT NULL,
  request_hash varchar(128),
  response_status int,
  response_body jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (service_name, request_id, endpoint)
);

-- 外贸通原始联系人（由 0012 创建，0044 补齐线上 5 列，共 21 列）-----------------
CREATE TABLE waimaotong_raw_contacts (
  id                bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  raw_company_id    bigint NOT NULL REFERENCES waimaotong_raw_companies(id) ON DELETE CASCADE,
  source_contact_id text,
  name              text,
  position          text,
  department        text,
  email             citext,
  email_status      text,
  phone             text,
  mobile            text,
  linkedin          text,
  whatsapp          text,
  source            text,
  confidence        numeric,
  raw_payload       jsonb,
  created_at        timestamptz DEFAULT now(),
  -- 线上新增 5 列（0044 补齐）
  sys_contact_id    uuid,
  contact_id        text,
  sys_company_id    uuid,
  api_company_id    text,
  company_id        text
);
CREATE INDEX idx_wmt_raw_contacts_company ON waimaotong_raw_contacts(raw_company_id);
CREATE UNIQUE INDEX uq_wmt_raw_contacts_source_contact
  ON waimaotong_raw_contacts(raw_company_id, source_contact_id)
  WHERE source_contact_id IS NOT NULL;
CREATE UNIQUE INDEX uq_wmt_raw_contacts_email_fallback
  ON waimaotong_raw_contacts(raw_company_id, email)
  WHERE source_contact_id IS NULL AND email IS NOT NULL;
CREATE INDEX idx_wmt_raw_contacts_email
  ON waimaotong_raw_contacts(email)
  WHERE email IS NOT NULL;

-- RLS enablement ---------------------------------------------------------------
-- Apply RLS to tenant-scoped tables. Admin/service roles need grants as separate migrations.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_task_keywords ENABLE ROW LEVEL SECURITY;
-- tenant_companies RLS 已在表定义处 inline 开启
ALTER TABLE scoring_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE scoring_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_blacklist ENABLE ROW LEVEL SECURITY;
-- competitor_companies/competitor_contacts RLS 已在表定义处 inline 开启
ALTER TABLE tenant_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_warmup_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_warmup_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE domain_daily_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE sending_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE sending_plan_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE sequence_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE sequence_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_send_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_article_publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_ai_provider_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_logs ENABLE ROW LEVEL SECURITY;

-- Policy examples; generate the rest in Alembic using table list.
CREATE POLICY tenant_select_users ON users FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_update_users ON users FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
-- tenant_companies 的 select/write policies 已在表定义处 inline 声明
CREATE POLICY tenant_select_contacts ON tenant_contacts FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_write_contacts ON tenant_contacts FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_select_plans ON sending_plans FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_write_plans ON sending_plans FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_select_emails ON emails FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_write_emails ON emails FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());


-- Additional RLS policies that were verified during self-audit.
-- For full migrations, generate equivalent SELECT/INSERT/UPDATE/DELETE policies for every tenant-scoped table.
CREATE POLICY tenant_collection_task_keywords_all ON collection_task_keywords
  FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_intelligence_sources_select ON intelligence_sources
  FOR SELECT USING (tenant_id IS NULL OR tenant_id = current_tenant_id());
CREATE POLICY tenant_intelligence_sources_write ON intelligence_sources
  FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_audit_select ON audit_logs
  FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_audit_insert ON audit_logs
  FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY tenant_ai_provider_configs_all ON tenant_ai_provider_configs
  FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

-- Recommended in Alembic after grants are finalized:
-- ALTER TABLE <tenant_scoped_table> FORCE ROW LEVEL SECURITY;

-- ── 联系人职位分类（migration 0029，平台全局表，无 RLS）────────────────────────

CREATE TABLE position_classification_levels (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name         text NOT NULL,
    display_name text NOT NULL,
    sort_order   int  NOT NULL DEFAULT 0,
    is_sendable  bool NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE position_classification_categories (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    level_id     uuid NOT NULL REFERENCES position_classification_levels(id) ON DELETE CASCADE,
    name         text NOT NULL,
    display_name text NOT NULL,
    sort_order   int  NOT NULL DEFAULT 0,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_pos_cat_level ON position_classification_categories(level_id);

CREATE TABLE position_classification_keywords (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id uuid NOT NULL REFERENCES position_classification_categories(id) ON DELETE CASCADE,
    keyword     text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE(category_id, keyword)
);
CREATE INDEX idx_pos_kw_cat ON position_classification_keywords(category_id);

-- 视图：对 clean_contacts 中的 position 字段实时分类
CREATE VIEW v_tenant_contact_classified AS
SELECT
    tc.id         AS contact_id,
    cl.id         AS level_id,
    ca.id         AS category_id,
    cl.is_sendable
FROM clean_contacts tc
JOIN LATERAL (
    SELECT pck.category_id, pcc.level_id
    FROM position_classification_keywords pck
    JOIN position_classification_categories pcc ON pcc.id = pck.category_id
    WHERE lower(tc.position) LIKE '%%' || pck.keyword || '%%'
    ORDER BY pcc.sort_order DESC
    LIMIT 1
) matched ON true
JOIN position_classification_categories ca ON ca.id = matched.category_id
JOIN position_classification_levels cl ON cl.id = matched.level_id;
