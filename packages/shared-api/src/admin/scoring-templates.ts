import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface ScoringTemplate {
  id: string;
  industry?: string;
  name: string;
  description?: string;
  dimensions: Array<Record<string, unknown>>;
  grade_thresholds?: Record<string, number>;
  version?: number;
  is_active?: boolean;
  created_at: string;
  updated_at: string;
}

export function scoringTemplatesApi(client: AxiosInstance) {
  return {
    list: (industry?: string) =>
      client.get<PaginatedResponse<ScoringTemplate>>('/api/v1/scoring-templates', { params: { industry } }),
    detail: (id: string) =>
      client.get<ApiResponse<ScoringTemplate>>(`/api/v1/scoring-templates/${id}`),
    create: (data: Partial<ScoringTemplate>) =>
      client.post<ApiResponse<ScoringTemplate>>('/api/v1/scoring-templates', data),
    update: (id: string, data: Partial<ScoringTemplate>) =>
      client.put<ApiResponse<ScoringTemplate>>(`/api/v1/scoring-templates/${id}`, data),
    versions: (id: string) =>
      client.get<PaginatedResponse<ScoringTemplate>>(`/api/v1/scoring-templates/${id}/versions`),
  };
}
