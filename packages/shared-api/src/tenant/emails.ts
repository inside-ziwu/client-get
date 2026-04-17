import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
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
    trend: (filters?: MonitorFilters) =>
      client.get<ApiResponse<EmailTrend[]>>('/api/v1/emails/trend', { params: filters }),
    aiAnalysis: (data: AiAnalysisRequest) =>
      client.post<ApiResponse<AiAnalysisResult>>('/api/v1/emails/ai-analysis', data),
  };
}
