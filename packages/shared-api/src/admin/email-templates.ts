import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface PlatformEmailTemplate {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  category: string;
  variables: Array<{ name: string; label: string }>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export function emailTemplatesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<PlatformEmailTemplate>>('/api/v1/email-templates'),
    detail: (id: string) =>
      client.get<ApiResponse<PlatformEmailTemplate>>(`/api/v1/email-templates/${id}`),
    create: (data: Partial<PlatformEmailTemplate>) =>
      client.post<ApiResponse<PlatformEmailTemplate>>('/api/v1/email-templates', data),
    update: (id: string, data: Partial<PlatformEmailTemplate>) =>
      client.put<ApiResponse<PlatformEmailTemplate>>(`/api/v1/email-templates/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/email-templates/${id}`),
  };
}
