import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface ScoringTemplate {
  id: string;
  name: string;
  description?: string;
  dimensions: Array<{
    name: string;
    weight: number;
    criteria: string;
  }>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export function scoringTemplatesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<ScoringTemplate>>('/api/v1/scoring-templates'),
    detail: (id: string) =>
      client.get<ApiResponse<ScoringTemplate>>(`/api/v1/scoring-templates/${id}`),
    create: (data: Partial<ScoringTemplate>) =>
      client.post<ApiResponse<ScoringTemplate>>('/api/v1/scoring-templates', data),
    update: (id: string, data: Partial<ScoringTemplate>) =>
      client.put<ApiResponse<ScoringTemplate>>(`/api/v1/scoring-templates/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/scoring-templates/${id}`),
  };
}
