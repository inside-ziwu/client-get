export interface ApiResponse<T> {
  data: T;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    cursor: string | null;
    has_more: boolean;
    total?: number;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, string[]>;
  };
}

// Common filter/param types
export interface PaginationParams {
  cursor?: string;
  limit?: number;
  include_total?: boolean;
}

export interface CompanyFilters extends PaginationParams {
  keyword?: string;
  grade?: string;
  status?: string;
  industry?: string;
  country?: string;
  min_score?: number;
  max_score?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface CustomerFilters extends PaginationParams {
  keyword?: string;
  grade?: string;
  status?: string;
  company_grade?: string;
}

export interface PlanFilters extends PaginationParams {
  status?: string;
  keyword?: string;
}

export interface MonitorFilters {
  plan_id?: string;
  date_from?: string;
  date_to?: string;
  status?: string;
}

export interface IntelFilters extends PaginationParams {
  keyword?: string;
  category?: string;
  source_id?: string;
  status?: string;
}

export interface TenantFilters extends PaginationParams {
  keyword?: string;
  status?: string;
}

// Dashboard types
export interface DashboardOverview {
  total_companies: number;
  scored_companies?: number;
  total_plans?: number;
  running_plans?: number;
  unread_notifications?: number;
  new_companies_this_week?: number;
  total_prospects?: number;
  active_plans?: number;
  emails_sent_this_month?: number;
  reply_rate?: number;
  is_admin?: boolean;
}

export interface DashboardFunnel {
  stages: Array<{
    status: string;
    count: number;
  }>;
  total: number;
}

// Email stats
export interface EmailStats {
  total?: number;
  sent?: number;
  delivered?: number;
  opened?: number;
  clicked?: number;
  replied?: number;
  bounced?: number;
  unsubscribed?: number;
  total_sent?: number;
  delivery_rate?: number;
  open_rate?: number;
  click_rate?: number;
  reply_rate?: number;
  bounce_rate?: number;
}

export interface EmailTrend {
  date: string;
  total?: number;
  sent?: number;
  delivered?: number;
  opened?: number;
  clicked?: number;
  replied?: number;
  bounced?: number;
}

// AI related
export interface AiAnalysisRequest {
  plan_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface AiAnalysisResult {
  summary: string;
  stats?: Record<string, unknown>;
  insights?: string[];
  recommendations?: string[];
  model_used?: string;
}

export interface AiGenerateTemplateRequest {
  company_name: string;
  prompt: string;
  category?: string;
  subject?: string;
  name?: string;
  estimated_cost?: number | string;
  industry?: string;
  purpose?: string;
  tone?: string;
  language?: string;
  additional_instructions?: string;
}

export interface AiGenerateTemplateResult {
  subject: string;
  body_html: string;
  variables: Array<{ name: string; label: string }>;
}

export type AiProviderBalanceStatus =
  | 'available'
  | 'insufficient_balance'
  | 'unknown'
  | 'invalid_api_key'
  | 'provider_error'
  | 'not_configured';

export type AiCapabilityReason =
  | 'insufficient_permission'
  | 'not_configured'
  | 'insufficient_balance'
  | 'balance_unknown'
  | 'invalid_api_key'
  | 'provider_error'
  | 'unavailable';

export interface AiProviderConfiguredBy {
  kind: 'platform_user' | 'tenant_user';
  id: string;
  name?: string | null;
  email?: string | null;
}

export interface AiProviderBalanceState {
  status: AiProviderBalanceStatus;
  source?: 'credits' | 'key' | null;
  amount?: number | null;
  currency: string;
  checked_at?: string | null;
  message?: string | null;
  total_credits?: number | null;
  total_usage?: number | null;
  key_limit?: number | null;
  key_limit_remaining?: number | null;
}

export interface AiProviderConfig {
  id?: string | null;
  tenant_id: string;
  provider: 'openrouter';
  is_configured: boolean;
  secret_masked?: string | null;
  configured_by?: AiProviderConfiguredBy | null;
  last_rotated_at?: string | null;
  updated_at?: string | null;
  balance: AiProviderBalanceState;
}

export interface AiCapabilityFeatureState {
  feature: string;
  available: boolean;
  reason?: AiCapabilityReason | null;
}

export interface AiCapabilityState {
  provider: {
    provider: 'openrouter';
    is_configured: boolean;
    balance_status: AiProviderBalanceStatus;
    balance_source?: 'credits' | 'key' | null;
    balance_amount?: number | null;
    checked_at?: string | null;
    message?: string | null;
  };
  features: AiCapabilityFeatureState[];
}

export interface AiUsageSummary {
  period?: string;
  total_cost?: number;
  breakdown?: Array<{
    usage_type: string;
    count: number;
    cost: number;
  }>;
  items?: Array<{
    usage_type: string;
    total_calls: number;
    total_cost: number;
    total_tokens: number;
  }>;
}

export interface AiUsageTrend {
  date?: string;
  cost?: number;
  usage_type?: string;
  usage_date?: string;
  total_calls?: number;
  total_cost?: number;
}

// Import results
export interface ImportResult {
  total: number;
  success: number;
  failed: number;
  errors?: Array<{
    row: number;
    message: string;
  }>;
}

// Batch operation
export interface BatchOperationResult {
  success_count: number;
  failed_count: number;
  errors?: Array<{
    id: string;
    message: string;
  }>;
}
