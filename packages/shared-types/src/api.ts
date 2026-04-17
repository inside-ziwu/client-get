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
  new_companies_this_week: number;
  total_prospects: number;
  active_plans: number;
  emails_sent_this_month: number;
  reply_rate: number;
  ai_balance: number;
}

export interface DashboardFunnel {
  stages: Array<{
    name: string;
    count: number;
    percentage: number;
  }>;
}

// Email stats
export interface EmailStats {
  total_sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
  delivery_rate: number;
  open_rate: number;
  click_rate: number;
  reply_rate: number;
  bounce_rate: number;
}

export interface EmailTrend {
  date: string;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  replied: number;
  bounced: number;
}

// AI related
export interface AiAnalysisRequest {
  plan_id?: string;
  date_from?: string;
  date_to?: string;
}

export interface AiAnalysisResult {
  summary: string;
  insights: string[];
  recommendations: string[];
  model_used: string;
}

export interface AiGenerateTemplateRequest {
  industry: string;
  purpose: string;
  tone?: string;
  language?: string;
  additional_instructions?: string;
}

export interface AiGenerateTemplateResult {
  subject: string;
  body_html: string;
  variables: Array<{ name: string; label: string }>;
}

// Billing
export interface BillingBalance {
  amount: number;
  currency: string;
}

export interface UsageSummary {
  period: string;
  total_cost: number;
  breakdown: Array<{
    usage_type: string;
    count: number;
    cost: number;
  }>;
}

export interface UsageTrend {
  date: string;
  cost: number;
  usage_type: string;
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
