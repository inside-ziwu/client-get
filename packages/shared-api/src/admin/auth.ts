import type { AxiosInstance } from 'axios';
import type { ApiResponse, LoginRequest, LoginResponse } from '@shared/types';

export interface AdminCurrentUser {
  id: string;
  email: string;
  name: string;
  roles: string[];
}

export function authApi(client: AxiosInstance) {
  return {
    login: (data: LoginRequest) =>
      client.post<ApiResponse<LoginResponse>>('/api/v1/auth/login', data),
    me: () =>
      client.get<ApiResponse<AdminCurrentUser>>('/api/v1/auth/me'),
  };
}
