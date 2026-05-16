import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse, PlanFilters } from '@shared/types';

export interface SendingPlanStep {
  id: string;
  step_order?: number;
  step_number?: number;
  template_id: string;
  delay_days: number;
  condition_type?: string;
  condition?: string;
  subject_override?: string;
}

export interface SendingPlanRecipient {
  id: string;
  tenant_company_id?: string;
  company_name?: string;
  email?: string;
  enrollment_status?: string;
  current_step: number;
}

export interface SendingPlan {
  id: string;
  name: string;
  status: string;
  description?: string;
  recipient_source?: string;
  recipient_config?: Record<string, unknown>;
  send_strategy?: Record<string, unknown>;
  sender_name?: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  sender_email?: string;
  domain_id?: string;
  total_recipients?: number;
  sent_count?: number;
  steps_count?: number;
  created_at: string;
  updated_at: string;
}

export function sendingPlansApi(client: AxiosInstance) {
  return {
    list: (filters?: PlanFilters) =>
      client.get<PaginatedResponse<SendingPlan>>('/api/v1/sending-plans', { params: filters }),
    detail: (id: string) =>
      client.get<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}`),
    create: (data: Partial<SendingPlan>) =>
      client.post<ApiResponse<SendingPlan>>('/api/v1/sending-plans', data),
    update: (id: string, data: Partial<SendingPlan>) =>
      client.patch<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/sending-plans/${id}`),

    // Steps
    listSteps: (planId: string) =>
      client.get<PaginatedResponse<SendingPlanStep>>(`/api/v1/sending-plans/${planId}/steps`),
    createStep: (planId: string, data: Partial<SendingPlanStep>) =>
      client.post<ApiResponse<SendingPlanStep>>(`/api/v1/sending-plans/${planId}/steps`, data),
    updateStep: (planId: string, stepId: string, data: Partial<SendingPlanStep>) =>
      client.put<ApiResponse<SendingPlanStep>>(`/api/v1/sending-plans/${planId}/steps/${stepId}`, data),
    deleteStep: (planId: string, stepId: string) =>
      client.delete(`/api/v1/sending-plans/${planId}/steps/${stepId}`),

    // Recipients
    listRecipients: (planId: string) =>
      client.get<PaginatedResponse<SendingPlanRecipient>>(`/api/v1/sending-plans/${planId}/recipients`),
    previewRecipients: (planId: string) =>
      client.get<PaginatedResponse<Record<string, unknown>>>(`/api/v1/sending-plans/${planId}/recipients/preview`),
    lockRecipients: (planId: string) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/sending-plans/${planId}/recipients/lock`),
    appendRecipients: (planId: string, data: Record<string, unknown>) =>
      client.post<ApiResponse<Record<string, unknown>>>(`/api/v1/sending-plans/${planId}/recipients/append`, data),

    // Execution
    schedule: (id: string, data: { scheduled_at?: string }) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/schedule`, data),
    start: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/start`),
    pause: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/pause`),
    resume: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/resume`),
    cancel: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/cancel`),
    preview: (id: string) =>
      client.get<ApiResponse<Record<string, unknown>>>(`/api/v1/sending-plans/${id}/preview`),
    sampleEmails: (id: string) =>
      client.get<PaginatedResponse<Record<string, unknown>>>(`/api/v1/sending-plans/${id}/sample-emails`),
  };
}
