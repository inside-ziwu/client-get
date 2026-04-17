import type { AxiosInstance } from 'axios';
import type { ApiResponse, LoginRequest, LoginResponse } from '@shared/types';

export function authApi(client: AxiosInstance) {
  return {
    login: (data: LoginRequest) =>
      client.post<ApiResponse<LoginResponse>>('/api/v1/auth/login', data),
  };
}
