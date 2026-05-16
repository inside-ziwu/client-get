import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface TenantScoringTemplate {
  id: string;
  name?: string;
  is_active?: boolean;
  dimensions: Array<{
    name: string;
    weight: number;
    criteria?: string;
    [key: string]: unknown;
  }>;
  grade_thresholds?: Record<string, number>;
  version?: number;
  updated_at?: string;
}

export function scoringApi(client: AxiosInstance) {
  return {
    get: () =>
      client.get<PaginatedResponse<TenantScoringTemplate>>('/api/v1/scoring-templates'),
    update: (id: string, data: Partial<TenantScoringTemplate>) =>
      client.put<ApiResponse<TenantScoringTemplate>>(`/api/v1/scoring-templates/${id}`, data),
  };
}
