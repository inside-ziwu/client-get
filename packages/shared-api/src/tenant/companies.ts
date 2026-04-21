import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  CompanyFilters,
} from '@shared/types';

export interface Company {
  id: string;
  name: string;
  name_en?: string;
  domain?: string;
  industry?: string;
  country?: string;
  business_status?: string;
  data_status?: string;
  grade?: string;
  total_score?: number;
  is_precise_customer?: boolean;
  website?: string;
  notes?: string;
  tags?: string[];
  created_at: string;
  updated_at: string;
}

export function companiesApi(client: AxiosInstance) {
  return {
    list: (filters?: CompanyFilters) =>
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
