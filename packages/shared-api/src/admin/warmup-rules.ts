import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface WarmupRules {
  daily_increase: number;
  max_daily_limit: number;
  warmup_duration_days: number;
  reply_rate_threshold: number;
  bounce_rate_threshold: number;
}

export function warmupRulesApi(client: AxiosInstance) {
  return {
    get: () =>
      client.get<ApiResponse<WarmupRules>>('/api/v1/warmup-rules'),
    update: (data: WarmupRules) =>
      client.put<ApiResponse<WarmupRules>>('/api/v1/warmup-rules', data),
  };
}
