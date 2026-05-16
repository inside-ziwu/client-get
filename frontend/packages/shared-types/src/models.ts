import type {
  TenantStatus,
  UserStatus,
  UserRole,
  DataSourceType,
  TenantCompanyStatus,
  CompanyGrade,
  ContactGrade,
  SeniorityLevel,
  TenantContactStatus,
  GroupMemberAddedBy,
  EmailTemplateSourceType,
  SendingPlanStatus,
  RecipientSource,
  SequenceConditionType,
  EmailStatus,
  IntelligenceSourceType,
  IntelligenceArticleStatus,
  ArticlePublicationStatus,
  DomainVerificationStatus,
  AiModelType,
  NotificationCategory,
} from './enums';

// === 租户 ===

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  industry?: string;
  status: TenantStatus;
  settings?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// === 用户 ===

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  name: string;
  role: UserRole;
  status: UserStatus;
  must_change_pwd: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

// === 共享公司 ===

export interface SharedCompany {
  id: string;
  name: string;
  name_en?: string;
  country?: string;
  region?: string;
  city?: string;
  address?: string;
  website?: string;
  domain?: string;
  industry?: string;
  industry_tags?: string[];
  employee_count?: number;
  annual_revenue?: string;
  established_year?: number;
  export_countries?: string[];
  product_keywords?: string[];
  hs_codes?: string[];
  data_completeness?: number;
  last_enriched_at?: string;
  created_at: string;
  updated_at: string;
}

// === 租户公司 ===

export interface TenantCompany {
  id: string;
  tenant_id: string;
  company_id: string;
  status: TenantCompanyStatus;
  grade?: CompanyGrade;
  total_score?: number;
  keyword_id?: string;
  collection_task_id?: string;
  notes?: string;
  tags?: string[];
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TenantCompanyWithDetails extends TenantCompany {
  company: SharedCompany;
}

// === 共享联系人 ===

export interface SharedContact {
  id: string;
  company_id: string;
  name?: string;
  name_en?: string;
  email?: string;
  phone?: string;
  title?: string;
  department?: string;
  seniority_level?: SeniorityLevel;
  source_type?: DataSourceType;
  is_valid_email?: boolean;
  created_at: string;
  updated_at: string;
}

// === 租户联系人 ===

export interface TenantContact {
  id: string;
  tenant_id: string;
  tenant_company_id: string;
  contact_id: string;
  grade?: ContactGrade;
  status: TenantContactStatus;
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TenantContactWithDetails extends TenantContact {
  contact: SharedContact;
  company?: TenantCompanyWithDetails;
}

// === 评分模板 ===

export interface ScoringRule {
  condition: string;
  values?: string[];
  min?: number;
  max?: number;
  value?: string;
  regions?: string[];
  score: number;
}

export interface ScoringDimension {
  id: string;
  name: string;
  weight: number;
  type: string;
  rules?: ScoringRule[];
  prompt_template?: string;
}

export interface GradeThresholds {
  S: number;
  A: number;
  B: number;
  C: number;
  D: number;
}

export interface ScoringTemplate {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  dimensions: ScoringDimension[];
  grade_thresholds: GradeThresholds;
  version: number;
  created_at: string;
  updated_at: string;
}

// === 公司评分 ===

export interface DimensionScore {
  dimension_id: string;
  name: string;
  score: number;
  weight: number;
  weighted_score: number;
  matched_rules?: string[];
}

export interface CompanyScore {
  id: string;
  tenant_company_id: string;
  tenant_id: string;
  template_id: string;
  template_version_id?: string;
  total_score: number;
  grade: CompanyGrade;
  dimension_scores: DimensionScore[];
  llm_score?: number;
  llm_reasoning?: string;
  scored_at: string;
  created_at: string;
}

// === 联系人评分规则 ===

export interface ContactRule {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  rules: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

// === 分组 ===

export interface GroupAutoRules {
  grade_in?: CompanyGrade[];
  min_score?: number;
}

export interface Group {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  auto_rules?: GroupAutoRules;
  member_count: number;
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface GroupMember {
  id: string;
  group_id: string;
  tenant_id: string;
  tenant_contact_id: string;
  added_by: GroupMemberAddedBy;
  created_at: string;
}

// === 邮件模板 ===

export interface TemplateVariable {
  name: string;
  label: string;
}

export interface EmailTemplate {
  id: string;
  tenant_id: string;
  source_type: EmailTemplateSourceType;
  platform_template_id?: string;
  name: string;
  category?: string;
  subject: string;
  body_html: string;
  body_text?: string;
  variables?: TemplateVariable[];
  is_ai_generated: boolean;
  ai_prompt?: string;
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface PlatformEmailTemplate {
  id: string;
  name: string;
  description?: string;
  category?: string;
  subject: string;
  body_html: string;
  body_text?: string;
  variables?: TemplateVariable[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// === 发送计划 ===

export interface SendStrategy {
  timezone_aware: boolean;
  preferred_hours?: { start: number; end: number };
  daily_limit?: number;
  interval_minutes?: number;
}

export interface SendingPlan {
  id: string;
  tenant_id: string;
  created_by: string;
  name: string;
  description?: string;
  status: SendingPlanStatus;
  recipient_source: RecipientSource;
  recipient_config?: Record<string, unknown>;
  send_strategy?: SendStrategy;
  sender_name?: string;
  sender_email?: string;
  domain_id?: string;
  total_recipients: number;
  sent_count: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SequenceStep {
  id: string;
  plan_id: string;
  tenant_id: string;
  step_number: number;
  template_id: string;
  delay_days: number;
  condition_type: SequenceConditionType;
  use_ai_personalization: boolean;
  ai_instructions?: string;
  created_at: string;
  updated_at: string;
}

// === 邮件 ===

export interface Email {
  id: string;
  tenant_id: string;
  plan_id: string;
  step_id?: string;
  step_number?: number;
  template_id: string;
  tenant_contact_id: string;
  from_email: string;
  from_name?: string;
  to_email: string;
  to_name?: string;
  subject: string;
  status: EmailStatus;
  is_ai_personalized: boolean;
  sent_at?: string;
  delivered_at?: string;
  opened_at?: string;
  clicked_at?: string;
  replied_at?: string;
  bounced_at?: string;
  created_at: string;
}

// === 情报 ===

export interface FetchConfig {
  frequency_hours: number;
  selector?: string;
}

export interface IntelligenceSource {
  id: string;
  tenant_id: string;
  name: string;
  source_type: IntelligenceSourceType;
  url?: string;
  fetch_config?: FetchConfig;
  industry_tags?: string[];
  is_active: boolean;
  last_fetched_at?: string;
  error_count: number;
  deleted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface IntelligenceArticle {
  id: string;
  source_id: string;
  title: string;
  url?: string;
  author?: string;
  published_at?: string;
  content_summary?: string;
  ai_category?: string;
  ai_tags?: string[];
  ai_relevance_score?: number;
  status: IntelligenceArticleStatus;
  created_at: string;
}

export interface IntelligenceArticlePublication {
  id: string;
  tenant_id: string;
  article_id: string;
  status: ArticlePublicationStatus;
  read_at?: string;
  matched_by?: string;
  created_at: string;
  updated_at: string;
}

export interface IntelligenceArticlePublicationWithArticle extends IntelligenceArticlePublication {
  article: IntelligenceArticle;
}

// === 域名预热 ===

export interface DomainWarmupStatus {
  id: string;
  tenant_id: string;
  domain: string;
  verification_status: DomainVerificationStatus;
  warmup_level: number;
  daily_limit: number;
  total_sent: number;
  bounce_rate: number;
  complaint_rate: number;
  open_rate: number;
  created_at: string;
  updated_at: string;
}

// === 数据源凭证 ===

export interface DataSourceCredential {
  id: string;
  source_type: DataSourceType;
  account_no?: string;
  username?: string;
  is_active: boolean;
  daily_quota: number;
  current_day_used: number;
  last_used_at?: string;
  last_error_at?: string;
  last_error_message?: string;
  consecutive_error_count: number;
  created_at: string;
  updated_at: string;
}

// === 采集关键词 ===

export interface CollectionKeyword {
  id: string;
  tenant_id: string;
  keyword: string;
  source_types: DataSourceType[];
  is_active: boolean;
  auto_collect: boolean;
  collect_frequency_hours?: number;
  total_companies: number;
  last_collected_at?: string;
  created_at: string;
  updated_at: string;
}

// === 通知 ===

export interface Notification {
  id: string;
  tenant_id: string;
  user_id: string;
  title: string;
  content?: string;
  category: NotificationCategory;
  entity_type?: string;
  entity_id?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

// === AI 模型 ===

export interface AiModel {
  id: string;
  provider: string;
  model_id: string;
  display_name: string;
  model_type: AiModelType;
  input_price: number;
  output_price: number;
  is_active: boolean;
  config?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
