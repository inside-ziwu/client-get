import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface TeamUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export function teamApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<ApiResponse<TeamUser[]>>('/api/v1/team'),
    create: (data: { email: string; name: string; role: string }) =>
      client.post<ApiResponse<TeamUser>>('/api/v1/team', data),
    update: (id: string, data: Partial<Pick<TeamUser, 'name' | 'role' | 'status'>>) =>
      client.put<ApiResponse<TeamUser>>(`/api/v1/team/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/team/${id}`),
  };
}
