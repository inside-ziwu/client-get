import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface WarmupRuleLevel {
  level: number;
  daily_limit: number;
  min_stay_days: number;
  min_delivery_rate: number;
  max_bounce_rate: number;
  max_complaint_rate: number;
}

export interface WarmupRules {
  id?: string;
  name: string;
  is_active?: boolean;
  min_observation_emails?: number;
  bounce_alert_rate: number;
  config?: Record<string, unknown>;
  levels: WarmupRuleLevel[];
}

export function warmupRulesApi(client: AxiosInstance) {
  return {
    get: () =>
      client.get<PaginatedResponse<WarmupRules>>('/api/v1/warmup-rules'),
    update: (data: WarmupRules) =>
      client.put<ApiResponse<WarmupRules>>('/api/v1/warmup-rules', data),
  };
}
