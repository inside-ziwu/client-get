import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse, CustomerFilters } from '@shared/types';

export interface Prospect {
  id: string;
  name: string;
  country?: string;
  grade?: string;
  business_status?: string;
  data_status?: string;
  total_score?: number;
  is_precise_customer?: boolean;
  created_at: string;
}

export function prospectsApi(client: AxiosInstance) {
  return {
    list: (filters?: CustomerFilters & { group_id?: string }) =>
      client.get<PaginatedResponse<Prospect>>('/api/v1/prospects', { params: filters }),
    detail: (id: string) =>
      client.get<ApiResponse<Prospect>>(`/api/v1/prospects/${id}`),
    update: (id: string, data: Record<string, unknown>) =>
      client.patch<ApiResponse<Prospect>>(`/api/v1/prospects/${id}`, data),
    select: (id: string) =>
      client.post<ApiResponse<Prospect>>(`/api/v1/prospects/${id}/select`),
    exclude: (id: string) =>
      client.post<ApiResponse<Prospect>>(`/api/v1/prospects/${id}/exclude`),
    blacklist: (id: string, reason?: string) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/prospects/${id}/blacklist`, { reason }),
  };
}
