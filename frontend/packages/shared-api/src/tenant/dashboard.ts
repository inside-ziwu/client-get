import type { AxiosInstance } from 'axios';
import type { AiCapabilityState, ApiResponse, DashboardOverview, DashboardFunnel } from '@shared/types';

export function dashboardApi(client: AxiosInstance) {
  return {
    overview: () =>
      client.get<ApiResponse<DashboardOverview>>('/api/v1/dashboard/overview'),
    funnel: () =>
      client.get<ApiResponse<DashboardFunnel>>('/api/v1/dashboard/funnel'),
    aiCapabilities: () =>
      client.get<ApiResponse<AiCapabilityState>>('/api/v1/ai-capabilities'),
  };
}
