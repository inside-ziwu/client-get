import type { AxiosInstance } from 'axios';
import type { ApiResponse, IndustryNewsSource } from '@shared/types';

export function industryNewsSourcesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<ApiResponse<IndustryNewsSource[]>>('/api/v1/industry-news-sources'),
    fetch: () =>
      client.post<ApiResponse<{ triggered: boolean; reason?: 'in_progress' | 'no_sources' }>>(
        '/api/v1/industry-news-sources/fetch',
      ),
    toggle: (id: string, is_active: boolean) =>
      client.patch<ApiResponse<IndustryNewsSource>>(`/api/v1/industry-news-sources/${id}`, { is_active }),
  };
}
