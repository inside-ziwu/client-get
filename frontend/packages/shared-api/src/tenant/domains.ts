import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface TenantDomainInfo {
  id: string;
  domain: string;
  verification_status: string;
  warmup_level?: number | null;
  daily_limit?: number | null;
  total_sent?: number | null;
  bounce_rate?: number | null;
  complaint_rate?: number | null;
  open_rate?: number | null;
  created_at: string;
  updated_at: string;
}

export function domainsApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<TenantDomainInfo>>('/api/v1/domains'),
    detail: (id: string) =>
      client.get<ApiResponse<TenantDomainInfo>>(`/api/v1/domains/${id}`),
    history: (id: string) =>
      client.get<PaginatedResponse<Record<string, unknown>>>(`/api/v1/domains/${id}/history`),
  };
}
