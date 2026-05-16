import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface Notification {
  id: string;
  category: string;
  title: string;
  content?: string;
  is_read: boolean;
  created_at: string;
}

export function notificationsApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<Notification>>('/api/v1/notifications'),
    markRead: (id: string) =>
      client.post<ApiResponse<void>>(`/api/v1/notifications/${id}/read`),
    markAllRead: () =>
      client.post<ApiResponse<void>>('/api/v1/notifications/mark-all-read'),
  };
}
