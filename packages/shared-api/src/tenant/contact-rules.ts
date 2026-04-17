import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface ContactRules {
  max_emails_per_prospect_per_day: number;
  max_emails_per_prospect_per_week: number;
  min_interval_hours: number;
  respect_unsubscribe: boolean;
  bounce_threshold: number;
  updated_at: string;
}

export function contactRulesApi(client: AxiosInstance) {
  return {
    get: () =>
      client.get<ApiResponse<ContactRules>>('/api/v1/contact-rules'),
    update: (data: ContactRules) =>
      client.put<ApiResponse<ContactRules>>('/api/v1/contact-rules', data),
  };
}
