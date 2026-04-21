import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface TeamUser {
  id: string;
  email: string;
  name: string;
  roles?: string[];
  must_change_pwd?: boolean;
  status: string;
  created_at: string;
  last_login_at?: string;
}

export function teamApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<TeamUser>>('/api/v1/team/users'),
    create: (data: { email: string; name: string; roles?: string[]; password?: string; status?: string; must_change_pwd?: boolean }) =>
      client.post<ApiResponse<TeamUser>>('/api/v1/team/users', data),
    update: (id: string, data: Partial<Pick<TeamUser, 'name' | 'status'>> & { roles?: string[]; password?: string; must_change_pwd?: boolean }) =>
      client.patch<ApiResponse<TeamUser>>(`/api/v1/team/users/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/team/users/${id}`),
  };
}
