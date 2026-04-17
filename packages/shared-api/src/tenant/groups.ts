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
      client.put<ApiResponse<Group>>(`/api/v1/groups/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/groups/${id}`),
    batchAddMembers: (id: string, prospectIds: string[]) =>
      client.post<ApiResponse<BatchOperationResult>>(`/api/v1/groups/${id}/members/batch-add`, { prospect_ids: prospectIds }),
    batchRemoveMembers: (id: string, prospectIds: string[]) =>
      client.post<ApiResponse<BatchOperationResult>>(`/api/v1/groups/${id}/members/batch-remove`, { prospect_ids: prospectIds }),
  };
}
