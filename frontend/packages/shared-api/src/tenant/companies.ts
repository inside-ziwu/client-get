import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
} from '@shared/types';

export interface Company {
  id: string;
  tc_id: string;
  name: string;
  name_en?: string;
  domain?: string;
  country_iso3?: string;
  website?: string;
  founded_year?: number;
  employee_num?: string;
  industry_desc?: string;
  sub_industry?: string;
  industry_tags?: string[];
  product_tags?: string[];
  grade?: string;
  wmt_score?: number;
  score?: number;
  model_score?: number;
  system_grade?: string;
  system_score?: number;
  score_adjustment?: number;
  phone?: string;
  company_size?: string;
  trade_amount_3y_usd?: number;
  trade_count?: number;
  contacts_count?: number;
  description?: string;
  data_source_tags?: string[];
  collection_type: 'manual' | 'keyword' | 'reverse' | 'unknown';
  sources?: string[];
  full_address?: string;
  matched_keywords?: string[];
  business_status?: string;
  data_status?: string;
  note?: string;
  tags?: string[];
  score_details?: unknown;
  company_type_analysis?: string;
  email_priority?: string;
  sales_approach?: string;
  match_reasons?: unknown;
  potential_needs?: unknown;
  recommended_products?: unknown;
  risk_factors?: unknown;
  main_business?: string;
  trade_summary?: string;
  source_competitor?: string;
  source_competitor_cn?: string;
  created_at?: string;
  updated_at?: string;
  tenant_created_at?: string;
  tenant_updated_at?: string;
}

export interface CompanyListFilters {
  keyword?: string;
  grade?: string;
  'grades[]'?: string[];
  'system_grades[]'?: string[];
  'countries[]'?: string[];
  'sub_industries[]'?: string[];
  'product_tags[]'?: string[];
  'sources[]'?: string[];
  trade_amount_min?: number;
  trade_amount_max?: number;
  trade_count_min?: number;
  trade_count_max?: number;
  contact_count_min?: number;
  contact_count_max?: number;
  founded_year_from?: number;
  founded_year_to?: number;
  min_score?: number;
  max_score?: number;
  group_id?: string;
  collection_type?: string;
  business_status?: string;
  page?: number;
  page_size?: number;
}

export function companiesApi(client: AxiosInstance) {
  return {
    list: (filters?: CompanyListFilters) =>
      client.get<PaginatedResponse<Company>>('/api/v1/companies', { params: filters }),
    filters: () =>
      client.get<ApiResponse<Record<string, string[]>>>('/api/v1/companies/filters'),
    detail: (id: string) =>
      client.get<ApiResponse<Company>>(`/api/v1/companies/${id}`),
    contacts: (id: string) =>
      client.get<PaginatedResponse<Record<string, unknown>>>(`/api/v1/companies/${id}/contacts`),
    create: (data: Record<string, unknown>) =>
      client.post<ApiResponse<Company>>('/api/v1/companies', data),
    batchImport: (items: Array<Record<string, unknown>>) =>
      client.post<ApiResponse<Record<string, unknown>>>('/api/v1/companies/batch-import', { items }),
    blacklist: (id: string, reason?: string) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/companies/${id}/blacklist`, { reason }),
    patch: (tcId: string, data: Record<string, unknown>) =>
      client.patch<ApiResponse<Company>>(`/api/v1/prospects/${tcId}`, data),
  };
}
