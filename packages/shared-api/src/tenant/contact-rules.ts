import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface ContactRuleSet {
  max_emails_per_prospect_per_day: number;
  max_emails_per_prospect_per_week: number;
  min_interval_hours: number;
  respect_unsubscribe: boolean;
  bounce_threshold: number;
}

export interface ContactRules {
  id: string;
  name: string;
  is_active?: boolean;
  rules: ContactRuleSet;
  version?: number;
  updated_at: string;
}

export function contactRulesApi(client: AxiosInstance) {
  return {
    get: () =>
      client.get<PaginatedResponse<ContactRules>>('/api/v1/contact-rules'),
    update: (id: string, data: { name?: string; rules: ContactRuleSet }) =>
      client.put<ApiResponse<ContactRules>>(`/api/v1/contact-rules/${id}`, data),
  };
}
