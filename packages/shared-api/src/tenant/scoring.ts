import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface TenantScoringTemplate {
  dimensions: Array<{
    name: string;
    weight: number;
    criteria: string;
  }>;
  updated_at: string;
}

export function scoringApi(client: AxiosInstance) {
  return {
    get: () =>
      client.get<ApiResponse<TenantScoringTemplate>>('/api/v1/scoring'),
    update: (data: TenantScoringTemplate) =>
      client.put<ApiResponse<TenantScoringTemplate>>('/api/v1/scoring', data),
  };
}
