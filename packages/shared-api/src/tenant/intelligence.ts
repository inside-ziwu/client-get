import type { AxiosInstance } from 'axios';
import type { PaginatedResponse, IntelFilters } from '@shared/types';

export interface IntelligenceArticle {
  id: string;
  title: string;
  summary?: string;
  source_name: string;
  url?: string;
  category?: string;
  published_at?: string;
  status: string;
  created_at: string;
}

export function intelligenceApi(client: AxiosInstance) {
  return {
    list: (filters?: IntelFilters) =>
      client.get<PaginatedResponse<IntelligenceArticle>>('/api/v1/intelligence/articles', { params: filters }),
  };
}
