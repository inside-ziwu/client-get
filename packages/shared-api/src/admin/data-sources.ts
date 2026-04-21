import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface DataSource {
  id: string;
  source_type: string;
  name: string;
  alias_code?: string;
  purpose?: string;
  config?: Record<string, unknown>;
  landing_rules?: Record<string, unknown>;
}

export interface DataSourceCredential {
  id: string;
  source_type: string;
  account_label?: string;
  encrypted_payload_masked?: Record<string, unknown>;
  quotas?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export function dataSourcesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<DataSource>>('/api/v1/data-sources'),
    create: (data: Partial<DataSource>) =>
      client.post<ApiResponse<DataSource>>('/api/v1/data-sources', data),
    update: (type: string, data: Partial<DataSource>) =>
      client.patch<ApiResponse<DataSource>>(`/api/v1/data-sources/${type}`, data),
    patchConfig: (type: string, data: Record<string, unknown>) =>
      client.patch<ApiResponse<DataSource>>(`/api/v1/data-sources/${type}/config`, data),
    getCredentials: (type: string) =>
      client.get<PaginatedResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials`),
    createCredential: (type: string, data: Partial<DataSourceCredential>) =>
      client.post<ApiResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials`, data),
    updateCredential: (type: string, id: string, data: Partial<DataSourceCredential>) =>
      client.patch<ApiResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials/${id}`, data),
    deleteCredential: (type: string, id: string) =>
      client.delete(`/api/v1/data-sources/${type}/credentials/${id}`),
  };
}
