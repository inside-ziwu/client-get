import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface Keyword {
  id: string;
  keyword: string;
  created_at: string;
}

export function keywordsApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<ApiResponse<Keyword[]>>('/api/v1/keywords'),
    create: (data: { keyword: string }) =>
      client.post<ApiResponse<Keyword>>('/api/v1/keywords', data),
    update: (id: string, data: { keyword: string }) =>
      client.put<ApiResponse<Keyword>>(`/api/v1/keywords/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/keywords/${id}`),
  };
}
