-- ClientGet Backend Canonical Schema Draft
-- PostgreSQL 16+
-- This file is a blueprint for Alembic migrations, not a one-shot production migration.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

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
  level int NOT NULL CHECK (level BETWEEN 1 AND 6),
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
  model_type varchar(40) NOT NULL CHECK (model_type IN ('scoring','email_generation','intelligence_summary','data_analysis','general')),
  input_price numeric(12,6) NOT NULL,
  output_price numeric(12,6) NOT NULL,
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
  fallback_model_ids jsonb NOT NULL DEFAULT '[]',
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

-- Shared pool -----------------------------------------------------------------
CREATE TABLE shared_companies (
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
CREATE INDEX idx_shared_companies_domain ON shared_companies(domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_shared_companies_name_trgm ON shared_companies USING gin (name gin_trgm_ops);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON shared_companies FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE company_sources (
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
CREATE INDEX idx_company_sources_company ON company_sources(company_id);

CREATE TABLE shared_contacts (
  id uuid PRIMARY KEY,
  company_id uuid NOT NULL REFERENCES shared_companies(id),
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

-- Collection ------------------------------------------------------------------
CREATE TABLE collection_keywords (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  keyword text NOT NULL,
  keyword_normalized text NOT NULL,
  countries jsonb NOT NULL DEFAULT '[]',
  countries_hash varchar(64) NOT NULL,
  source_types jsonb NOT NULL DEFAULT '["waimao_tong","tengdao","lixiaoyun"]',
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','deleted')),
  daily_limit int,
  last_scheduled_at timestamptz,
  created_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, keyword_normalized, countries_hash)
);
CREATE INDEX idx_collection_keywords_sched ON collection_keywords(status, keyword_normalized, countries_hash);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON collection_keywords FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE collection_tasks (
  id uuid PRIMARY KEY,
  keyword text NOT NULL,
  keyword_normalized text NOT NULL,
  countries jsonb NOT NULL DEFAULT '[]',
  countries_hash varchar(64) NOT NULL,
  source_types jsonb NOT NULL,
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
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_collection_tasks_claim ON collection_tasks(status, priority DESC, scheduled_at) WHERE status='pending';
CREATE INDEX idx_collection_tasks_lease ON collection_tasks(lease_id) WHERE lease_id IS NOT NULL;
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

-- Tenant company and scoring ---------------------------------------------------
CREATE TABLE tenant_companies (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  company_id uuid NOT NULL REFERENCES shared_companies(id),
  business_status varchar(30) NOT NULL DEFAULT 'pending_score' CHECK (business_status IN ('pending_score','scoring','scored','selected','in_plan','contacted','replied','converted','excluded')),
  data_status varchar(30) NOT NULL DEFAULT 'incomplete' CHECK (data_status IN ('incomplete','enriching','complete','enrichment_failed')),
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
CREATE INDEX idx_tenant_companies_tenant_status ON tenant_companies(tenant_id, business_status, data_status);
CREATE INDEX idx_tenant_companies_grade ON tenant_companies(tenant_id, grade);
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_companies FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE scoring_templates (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  source_platform_template_id uuid REFERENCES platform_scoring_templates(id),
  name varchar(200) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  dimensions jsonb NOT NULL,
  grade_thresholds jsonb NOT NULL DEFAULT '{"S":90,"A":80,"B":60,"C":40,"D":0}',
  version int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_scoring_templates_active ON scoring_templates(tenant_id) WHERE is_active;
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
  shared_company_id uuid REFERENCES shared_companies(id),
  match_domain varchar(255),
  match_name_pattern varchar(500),
  reason text NOT NULL,
  blocked_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (shared_company_id IS NOT NULL OR match_domain IS NOT NULL OR match_name_pattern IS NOT NULL)
);
CREATE INDEX idx_company_blacklist_tenant ON company_blacklist(tenant_id);

CREATE TABLE competitor_companies (
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

-- Contacts and groups ----------------------------------------------------------
CREATE TABLE tenant_contacts (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  tenant_company_id uuid NOT NULL REFERENCES tenant_companies(id),
  contact_id uuid NOT NULL REFERENCES shared_contacts(id),
  grade char(1) CHECK (grade IN ('A','B','C','D')),
  status varchar(20) NOT NULL DEFAULT 'available' CHECK (status IN ('available','in_plan','contacted','replied','bounced','unsubscribed')),
  is_default boolean NOT NULL DEFAULT false,
  deleted_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, contact_id)
);
CREATE UNIQUE INDEX idx_tenant_contacts_one_default ON tenant_contacts(tenant_id, tenant_company_id) WHERE is_default AND deleted_at IS NULL;
CREATE INDEX idx_tenant_contacts_company ON tenant_contacts(tenant_company_id);
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
  warmup_level int NOT NULL DEFAULT 1 CHECK (warmup_level BETWEEN 1 AND 6),
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

CREATE TABLE sending_plans (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  created_by uuid NOT NULL REFERENCES users(id),
  name varchar(200) NOT NULL,
  description text,
  status varchar(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','scheduled','running','paused','completed','cancelled')),
  recipient_source varchar(20) NOT NULL CHECK (recipient_source IN ('group','manual','filter')),
  recipient_config jsonb NOT NULL,
  send_strategy jsonb NOT NULL DEFAULT '{"timezone_aware":true,"preferred_hours":[9,17],"daily_limit":100,"interval_seconds":[30,120]}',
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
  status varchar(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','replied','bounced','unsubscribed','paused','cancelled')),
  enrolled_at timestamptz NOT NULL DEFAULT now(),
  last_step_sent_at timestamptz,
  next_step_due_at timestamptz,
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
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_emails_tenant_created ON emails(tenant_id, created_at DESC, id DESC);
CREATE INDEX idx_emails_engagelab ON emails(engagelab_message_id) WHERE engagelab_message_id IS NOT NULL;

CREATE TABLE email_events (
  id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  email_id uuid NOT NULL,
  email_created_at timestamptz NOT NULL,
  event_type varchar(20) NOT NULL CHECK (event_type IN ('sent','delivered','opened','clicked','replied','bounced','complained','unsubscribed')),
  metadata jsonb NOT NULL DEFAULT '{}',
  source varchar(20) NOT NULL DEFAULT 'engagelab' CHECK (source IN ('engagelab','system')),
  provider_event_id varchar(100),
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

-- RLS enablement ---------------------------------------------------------------
-- Apply RLS to tenant-scoped tables. Admin/service roles need grants as separate migrations.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_task_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE scoring_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE scoring_template_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_blacklist ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_companies ENABLE ROW LEVEL SECURITY;
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
CREATE POLICY tenant_select_companies ON tenant_companies FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY tenant_write_companies ON tenant_companies FOR ALL USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());
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
