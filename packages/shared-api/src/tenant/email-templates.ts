import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  AiGenerateTemplateRequest,
  AiGenerateTemplateResult,
} from '@shared/types';

export interface EmailTemplate {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  source_type: 'custom' | 'platform_copy';
  category?: string;
  variables: Array<{ name: string; label: string }>;
  created_at: string;
  updated_at: string;
}

export function emailTemplatesApi(client: AxiosInstance) {
  return {
    listOfficial: () =>
      client.get<PaginatedResponse<EmailTemplate>>('/api/v1/email-templates/official'),
    listCustom: () =>
      client.get<PaginatedResponse<EmailTemplate>>('/api/v1/email-templates/custom'),
    create: (data: Partial<EmailTemplate>) =>
      client.post<ApiResponse<EmailTemplate>>('/api/v1/email-templates', data),
    update: (id: string, data: Partial<EmailTemplate>) =>
      client.put<ApiResponse<EmailTemplate>>(`/api/v1/email-templates/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/email-templates/${id}`),
    aiGenerate: (data: AiGenerateTemplateRequest) =>
      client.post<ApiResponse<AiGenerateTemplateResult>>('/api/v1/email-templates/ai-generate', data),
  };
}
