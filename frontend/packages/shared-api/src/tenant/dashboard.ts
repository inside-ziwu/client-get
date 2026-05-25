import type { AxiosInstance } from 'axios';
import type {
  AiCapabilityState,
  ApiResponse,
  DashboardOverview,
  DashboardFunnel,
  EmailStatsResponse,
  PlanOverviewResponse,
  DailyQuotaResponse,
  LlmBalanceResponse,
} from '@shared/types';

export function dashboardApi(client: AxiosInstance) {
  return {
    overview: () =>
      client.get<ApiResponse<DashboardOverview>>('/api/v1/dashboard/overview'),
    funnel: () =>
      client.get<ApiResponse<DashboardFunnel>>('/api/v1/dashboard/funnel'),
    aiCapabilities: () =>
      client.get<ApiResponse<AiCapabilityState>>('/api/v1/ai-capabilities'),
    emailStats: (params?: { start_date?: string; end_date?: string }) =>
      client.get<ApiResponse<EmailStatsResponse>>('/api/v1/dashboard/email-stats', { params }),
    planOverview: (params?: { plan_id?: string }) =>
      client.get<ApiResponse<PlanOverviewResponse>>('/api/v1/dashboard/plan-overview', { params }),
    dailyQuota: () =>
      client.get<ApiResponse<DailyQuotaResponse>>('/api/v1/dashboard/daily-quota'),
    llmBalance: () =>
      client.get<ApiResponse<LlmBalanceResponse>>('/api/v1/dashboard/llm-balance'),
  };
}
