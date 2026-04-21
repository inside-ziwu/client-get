import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse, PaginationParams, BatchOperationResult } from '@shared/types';

export interface Group {
  id: string;
  name: string;
  description?: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export function groupsApi(client: AxiosInstance) {
  return {
    list: (params?: PaginationParams) =>
      client.get<PaginatedResponse<Group>>('/api/v1/groups', { params }),
    detail: (id: string) =>
      client.get<ApiResponse<Group>>(`/api/v1/groups/${id}`),
    create: (data: { name: string; description?: string }) =>
      client.post<ApiResponse<Group>>('/api/v1/groups', data),
    update: (id: string, data: { name?: string; description?: string }) =>
      client.patch<ApiResponse<Group>>(`/api/v1/groups/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/groups/${id}`),
    listMembers: (id: string) =>
      client.get<PaginatedResponse<Record<string, unknown>>>(`/api/v1/groups/${id}/members`),
    batchAddMembers: (id: string, tenantCompanyIds: string[]) =>
      client.post<ApiResponse<BatchOperationResult>>(`/api/v1/groups/${id}/members/batch-add`, { tenant_company_ids: tenantCompanyIds }),
    batchRemoveMembers: (id: string, memberIds: string[]) =>
      client.post<ApiResponse<BatchOperationResult>>(`/api/v1/groups/${id}/members/batch-remove`, { member_ids: memberIds }),
  };
}
