import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export function onboardingApi(client: AxiosInstance) {
  return {
    complete: () =>
      client.post<ApiResponse<{ completed: boolean }>>('/api/v1/onboarding/complete'),
  };
}
