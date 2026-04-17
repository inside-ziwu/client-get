import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface Notification {
  id: string;
  category: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export function notificationsApi(client: AxiosInstance) {
  return {
    listUnread: () =>
      client.get<ApiResponse<Notification[]>>('/api/v1/notifications/unread'),
    markRead: (ids: string[]) =>
      client.post<ApiResponse<void>>('/api/v1/notifications/mark-read', { ids }),
  };
}
