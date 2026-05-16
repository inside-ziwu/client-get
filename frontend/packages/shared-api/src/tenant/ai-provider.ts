import type { AxiosInstance } from 'axios';
import type {
  AiProviderConfig,
  AiUsageSummary,
  AiUsageTrend,
  ApiResponse,
  PaginatedResponse,
} from '@shared/types';

export function aiProviderApi(client: AxiosInstance) {
  return {
    getOpenRouter: () =>
      client.get<ApiResponse<AiProviderConfig>>('/api/v1/settings/ai-provider/openrouter'),
    updateOpenRouter: (data: { api_key: string }) =>
      client.put<ApiResponse<AiProviderConfig>>('/api/v1/settings/ai-provider/openrouter', data),
    deleteOpenRouter: () =>
      client.delete<ApiResponse<{ deleted: boolean }>>('/api/v1/settings/ai-provider/openrouter'),
    refreshOpenRouterBalance: () =>
      client.post<ApiResponse<AiProviderConfig>>('/api/v1/settings/ai-provider/openrouter/balance/refresh'),
    usageSummary: (period?: string) =>
      client.get<ApiResponse<AiUsageSummary>>('/api/v1/ai/usage-summary', { params: { period } }),
    usageTrend: (params?: { date_from?: string; date_to?: string }) =>
      client.get<PaginatedResponse<AiUsageTrend>>('/api/v1/ai/usage-trend', { params }),
  };
}
