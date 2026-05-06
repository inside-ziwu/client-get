import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface ClassificationKeywordItem {
  id: string;
  keyword: string;
}

export interface ClassificationCategory {
  id: string;
  name: string;
  display_name: string;
  sort_order: number;
  keywords: string[] | null;
  keyword_ids: ClassificationKeywordItem[] | null;
}

export interface ClassificationLevel {
  id: string;
  name: string;
  display_name: string;
  sort_order: number;
  is_sendable: boolean;
  created_at: string;
  updated_at: string;
  categories: ClassificationCategory[] | null;
}

export function contactClassificationApi(client: AxiosInstance) {
  return {
    listLevels: () =>
      client.get<PaginatedResponse<ClassificationLevel>>('/api/v1/contact-classification/levels'),
    createLevel: (data: { name: string; display_name: string; sort_order?: number; is_sendable?: boolean }) =>
      client.post<ApiResponse<ClassificationLevel>>('/api/v1/contact-classification/levels', data),
    updateLevel: (id: string, data: Partial<{ name: string; display_name: string; sort_order: number; is_sendable: boolean }>) =>
      client.put<ApiResponse<ClassificationLevel>>(`/api/v1/contact-classification/levels/${id}`, data),
    deleteLevel: (id: string) =>
      client.delete<ApiResponse<{ deleted: boolean }>>(`/api/v1/contact-classification/levels/${id}`),
    createCategory: (data: { level_id: string; name: string; display_name: string; sort_order?: number }) =>
      client.post<ApiResponse<ClassificationCategory>>('/api/v1/contact-classification/categories', data),
    deleteCategory: (id: string) =>
      client.delete<ApiResponse<{ deleted: boolean }>>(`/api/v1/contact-classification/categories/${id}`),
    addKeywords: (data: { category_id: string; keywords: string[] }) =>
      client.post<PaginatedResponse<ClassificationKeywordItem>>('/api/v1/contact-classification/keywords', data),
    deleteKeyword: (id: string) =>
      client.delete<ApiResponse<{ deleted: boolean }>>(`/api/v1/contact-classification/keywords/${id}`),
  };
}
