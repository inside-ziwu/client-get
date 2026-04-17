import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  CompanyFilters,
  ImportResult,
  BatchOperationResult,
} from '@shared/types';

export interface Company {
  id: string;
  name: string;
  domain?: string;
  industry?: string;
  country?: string;
  grade?: string;
  score?: number;
  status: string;
  employee_count?: number;
  website?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export function companiesApi(client: AxiosInstance) {
  return {
    list: (filters?: CompanyFilters) =>
      client.get<PaginatedResponse<Company>>('/api/v1/companies', { params: filters }),
    detail: (id: string) =>
      client.get<ApiResponse<Company>>(`/api/v1/companies/${id}`),
    batchImport: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return client.post<ApiResponse<ImportResult>>('/api/v1/companies/batch-import', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    blacklist: (ids: string[]) =>
      client.post<ApiResponse<BatchOperationResult>>('/api/v1/companies/blacklist', { ids }),
  };
}
