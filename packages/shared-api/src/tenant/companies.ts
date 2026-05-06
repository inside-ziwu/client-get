import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
} from '@shared/types';

export interface Company {
  id: string;
  name: string;
  name_en?: string;
  domain?: string;
  industry?: string;
  country?: string;
  employee_scale?: string;
  contacts_count?: number;
  product_tags?: string[];
  business_status?: string;
  data_status?: string;
  grade?: string;
  total_score?: number;
  /** C4：人工调分，范围 -20 ~ +20 */
  score_adjustment?: number;
  score_adjusted_at?: string;
  score_adjusted_by?: string;
  score_adjust_reason?: string;
  is_precise_customer?: boolean;
  website?: string;
  notes?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

/** C5：10 项筛选参数 */
export interface CompanyListFilters {
  keyword?: string;
  grade?: string;
  'countries[]'?: string[];
  'sub_industries[]'?: string[];
  'product_tags[]'?: string[];
  'sources[]'?: string[];
  contact_count_range?: string;
  founded_year_from?: number;
  founded_year_to?: number;
  'employee_scale[]'?: string[];
  min_score?: number;
  max_score?: number;
  limit?: number;
  cursor?: string;
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
  };
}
