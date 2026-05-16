import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse, IntelFilters } from '@shared/types';

export interface IntelligenceArticle {
  publication_id: string;
  article_id: string;
  title: string;
  content_summary?: string;
  url?: string;
  ai_category?: string;
  ai_tags?: string[];
  ai_relevance_score?: number;
  has_summary?: boolean;
  published_at?: string;
  status: string;
  read_at?: string;
  article_created_at: string;
}

export interface IntelligenceSubscription {
  id: string;
  industry_tags: string[];
  min_relevance: number;
  notify_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export function intelligenceApi(client: AxiosInstance) {
  return {
    list: (filters?: IntelFilters) =>
      client.get<PaginatedResponse<IntelligenceArticle>>('/api/v1/intelligence/articles', { params: filters }),
    detail: (id: string) =>
      client.get<ApiResponse<IntelligenceArticle>>(`/api/v1/intelligence/articles/${id}`),
    markRead: (id: string) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/intelligence/articles/${id}/read`),
    star: (id: string) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/intelligence/articles/${id}/star`),
    archive: (id: string) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/intelligence/articles/${id}/archive`),
    getSubscriptions: () =>
      client.get<PaginatedResponse<IntelligenceSubscription>>('/api/v1/intelligence/subscriptions'),
    putSubscriptions: (data: Record<string, unknown>) =>
      client.put<PaginatedResponse<IntelligenceSubscription>>('/api/v1/intelligence/subscriptions', data),
  };
}
