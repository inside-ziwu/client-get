import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  AiGenerateTemplateRequest,
} from '@shared/types';

export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  body_text?: string;
  source_type: string;
  category?: string;
  variables: Array<string | { name: string; label?: string }>;
  is_ai_generated?: boolean;
  created_at: string;
  updated_at: string;
}

export function emailTemplatesApi(client: AxiosInstance) {
  return {
    list: () =>
      client.get<PaginatedResponse<EmailTemplate>>('/api/v1/email-templates'),
    detail: (id: string) =>
      client.get<ApiResponse<EmailTemplate>>(`/api/v1/email-templates/${id}`),
    create: (data: Partial<EmailTemplate>) =>
      client.post<ApiResponse<EmailTemplate>>('/api/v1/email-templates', data),
    update: (id: string, data: Partial<EmailTemplate>) =>
      client.put<ApiResponse<EmailTemplate>>(`/api/v1/email-templates/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/email-templates/${id}`),
    clone: (id: string) =>
      client.post<ApiResponse<EmailTemplate>>(`/api/v1/email-templates/${id}/clone`),
    preview: (id: string) =>
      client.get<ApiResponse<Pick<EmailTemplate, 'id' | 'subject' | 'body_html' | 'body_text'>>>(`/api/v1/email-templates/${id}/preview`),
    aiGenerate: (data: AiGenerateTemplateRequest) =>
      client.post<ApiResponse<EmailTemplate>>('/api/v1/email-templates/ai-generate', data),
  };
}
