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
  account_no: string;
  username: string;
  secret_masked?: string;
  raw_config?: Record<string, unknown>;
  rotation_order: number;
  daily_quota?: number;
  current_day_used: number;
  is_active: boolean;
  created_at: string;
}

export interface DataSourceCredentialPayload {
  account_no: string;
  username: string;
  secret?: string;
  raw_config?: Record<string, unknown>;
  rotation_order?: number;
  daily_quota?: number;
  is_active?: boolean;
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
    createCredential: (type: string, data: DataSourceCredentialPayload) =>
      client.post<ApiResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials`, data),
    updateCredential: (type: string, id: string, data: Partial<DataSourceCredentialPayload>) =>
      client.patch<ApiResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials/${id}`, data),
    deleteCredential: (type: string, id: string) =>
      client.delete(`/api/v1/data-sources/${type}/credentials/${id}`),
  };
}
