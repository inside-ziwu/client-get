import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface Keyword {
  id: string;
  keyword: string;
  keyword_normalized?: string;
  countries?: string[];
  source_types?: string[];
  status?: string;
  created_at: string;
}

export function keywordsApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<Keyword>>('/api/v1/keywords'),
    create: (data: { keyword: string; countries?: string[]; source_types?: string[] }) =>
      client.post<ApiResponse<Keyword>>('/api/v1/keywords', data),
    update: (id: string, data: Partial<Keyword>) =>
      client.patch<ApiResponse<Keyword>>(`/api/v1/keywords/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/keywords/${id}`),
  };
}
