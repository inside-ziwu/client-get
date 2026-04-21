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
    list: (params?: { cursor?: string; limit?: number }) =>
      client.get<PaginatedResponse<Record<string, unknown>>>('/api/v1/emails', { params }),
    aiAnalysis: (data: AiAnalysisRequest) =>
      client.post<ApiResponse<AiAnalysisResult>>('/api/v1/emails/ai-analysis', data),
  };
}
