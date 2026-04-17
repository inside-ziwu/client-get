import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface DataSourceCredential {
  id: string;
  type: string;
  name: string;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export function dataSourcesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<ApiResponse<Record<string, { enabled: boolean; credential_count: number }>>>('/api/v1/data-sources'),
    getCredentials: (type: string) =>
      client.get<ApiResponse<DataSourceCredential[]>>(`/api/v1/data-sources/${type}/credentials`),
    createCredential: (type: string, data: Partial<DataSourceCredential>) =>
      client.post<ApiResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials`, data),
    updateCredential: (type: string, id: string, data: Partial<DataSourceCredential>) =>
      client.patch<ApiResponse<DataSourceCredential>>(`/api/v1/data-sources/${type}/credentials/${id}`, data),
    deleteCredential: (type: string, id: string) =>
      client.delete(`/api/v1/data-sources/${type}/credentials/${id}`),
  };
}
