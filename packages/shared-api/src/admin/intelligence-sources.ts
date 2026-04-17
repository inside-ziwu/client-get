import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse, ImportResult } from '@shared/types';

export interface IntelligenceSource {
  id: string;
  name: string;
  type: 'rss' | 'website' | 'manual';
  url?: string;
  config: Record<string, unknown>;
  is_active: boolean;
  last_fetched_at?: string;
  created_at: string;
  updated_at: string;
}

export function intelligenceSourcesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<IntelligenceSource>>('/api/v1/intelligence-sources'),
    detail: (id: string) =>
      client.get<ApiResponse<IntelligenceSource>>(`/api/v1/intelligence-sources/${id}`),
    create: (data: Partial<IntelligenceSource>) =>
      client.post<ApiResponse<IntelligenceSource>>('/api/v1/intelligence-sources', data),
    update: (id: string, data: Partial<IntelligenceSource>) =>
      client.put<ApiResponse<IntelligenceSource>>(`/api/v1/intelligence-sources/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/intelligence-sources/${id}`),
    batchImport: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return client.post<ApiResponse<ImportResult>>('/api/v1/intelligence-sources/batch-import', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
  };
}
