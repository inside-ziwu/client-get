import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  MonitorFilters,
  EmailStats,
  EmailTrend,
  AiAnalysisRequest,
  AiAnalysisResult,
} from '@shared/types';

export interface EmailLog {
  id: string;
  created_at: string;
  plan_id: string | null;
  step_id: string | null;
  step_number: number | null;
  template_id: string | null;
  enrollment_id: string | null;
  tenant_contact_id: string;
  from_email: string;
  to_email: string;
  subject: string;
  status: string;
  plan_name?: string | null;
  template_name?: string | null;
  country_iso3?: string | null;
  timezone?: string | null;
  sent_at?: string | null;
  opened_at?: string | null;
  clicked_at?: string | null;
  replied_at?: string | null;
  bounced_at?: string | null;
}

export function emailsApi(client: AxiosInstance) {
  return {
    stats: (filters?: MonitorFilters) =>
      client.get<ApiResponse<EmailStats>>('/api/v1/emails/stats', { params: filters }),
    statsByPlan: () =>
      client.get<PaginatedResponse<Record<string, unknown>>>('/api/v1/emails/stats/by-plan'),
    statsByTemplate: () =>
      client.get<PaginatedResponse<Record<string, unknown>>>('/api/v1/emails/stats/by-template'),
    statsByGrade: () =>
      client.get<PaginatedResponse<Record<string, unknown>>>('/api/v1/emails/stats/by-grade'),
    statsByStep: () =>
      client.get<PaginatedResponse<Record<string, unknown>>>('/api/v1/emails/stats/by-step'),
    trend: (filters?: MonitorFilters) =>
      client.get<PaginatedResponse<EmailTrend>>('/api/v1/emails/stats/trend', { params: filters }),
    list: (params?: { cursor?: string; limit?: number; plan_id?: string }) =>
      client.get<PaginatedResponse<EmailLog>>('/api/v1/emails', { params }),
    aiAnalysis: (data: AiAnalysisRequest) =>
      client.post<ApiResponse<AiAnalysisResult>>('/api/v1/emails/ai-analysis', data),
  };
}
