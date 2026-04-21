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
      client.post<ApiResponse<LoginResponse>>(
        `${import.meta.env.VITE_API_BASE_URL}/t/${data.slug}/api/v1/auth/login`,
        data,
      ),
    changePassword: (data: ChangePasswordRequest | { old_password?: string; current_password?: string; new_password: string }) =>
      client.post<ApiResponse<void>>('/api/v1/auth/change-password', {
        current_password: 'current_password' in data ? data.current_password : data.old_password,
        new_password: data.new_password,
      }),
    me: () =>
      client.get<ApiResponse<CurrentUser>>('/api/v1/auth/me'),
  };
}
