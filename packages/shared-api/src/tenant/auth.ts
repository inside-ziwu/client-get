import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  TenantLoginRequest,
  LoginResponse,
  ChangePasswordRequest,
  CurrentUser,
} from '@shared/types';

export function authApi(client: AxiosInstance) {
  return {
    login: (data: TenantLoginRequest) =>
      client.post<ApiResponse<LoginResponse>>('/api/v1/auth/login', data),
    changePassword: (data: ChangePasswordRequest) =>
      client.post<ApiResponse<void>>('/api/v1/auth/change-password', data),
    me: () =>
      client.get<ApiResponse<CurrentUser>>('/api/v1/auth/me'),
  };
}
