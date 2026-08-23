import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  IndustryNewsItem,
  IndustryNewsFilterOptions,
  IndustryNewsFilters,
} from '@shared/types';

export function industryNewsApi(client: AxiosInstance) {
  return {
    list: (filters?: IndustryNewsFilters) =>
      client.get<PaginatedResponse<IndustryNewsItem>>('/api/v1/industry-news/items', { params: filters }),
    filters: () =>
      client.get<ApiResponse<IndustryNewsFilterOptions>>('/api/v1/industry-news/filters'),
    markRead: (id: string) =>
      client.post<ApiResponse<{ item_id: string; is_read: true }>>(`/api/v1/industry-news/items/${id}/read`),
  };
}
