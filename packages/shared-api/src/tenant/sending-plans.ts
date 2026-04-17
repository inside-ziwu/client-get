import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse, PlanFilters } from '@shared/types';

export interface SendingPlanStep {
  id: string;
  step_order: number;
  template_id: string;
  delay_days: number;
  condition_type: string;
  subject_override?: string;
}

export interface SendingPlanRecipient {
  id: string;
  prospect_id: string;
  prospect_name?: string;
  prospect_email?: string;
  enrollment_status: string;
  current_step: number;
}

export interface SendingPlan {
  id: string;
  name: string;
  status: string;
  description?: string;
  scheduled_at?: string;
  sender_email?: string;
  daily_limit?: number;
  steps: SendingPlanStep[];
  recipient_count: number;
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
      client.put<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}`, data),
    delete: (id: string) =>
      client.delete(`/api/v1/sending-plans/${id}`),

    // Steps
    listSteps: (planId: string) =>
      client.get<ApiResponse<SendingPlanStep[]>>(`/api/v1/sending-plans/${planId}/steps`),
    createStep: (planId: string, data: Partial<SendingPlanStep>) =>
      client.post<ApiResponse<SendingPlanStep>>(`/api/v1/sending-plans/${planId}/steps`, data),
    updateStep: (planId: string, stepId: string, data: Partial<SendingPlanStep>) =>
      client.put<ApiResponse<SendingPlanStep>>(`/api/v1/sending-plans/${planId}/steps/${stepId}`, data),
    deleteStep: (planId: string, stepId: string) =>
      client.delete(`/api/v1/sending-plans/${planId}/steps/${stepId}`),

    // Recipients
    listRecipients: (planId: string) =>
      client.get<PaginatedResponse<SendingPlanRecipient>>(`/api/v1/sending-plans/${planId}/recipients`),
    addRecipients: (planId: string, data: { group_id?: string; prospect_ids?: string[] }) =>
      client.post<ApiResponse<void>>(`/api/v1/sending-plans/${planId}/recipients`, data),
    removeRecipients: (planId: string, recipientIds: string[]) =>
      client.post<ApiResponse<void>>(`/api/v1/sending-plans/${planId}/recipients/remove`, { ids: recipientIds }),

    // Execution
    execute: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/execute`),
    pause: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/pause`),
    resume: (id: string) =>
      client.post<ApiResponse<SendingPlan>>(`/api/v1/sending-plans/${id}/resume`),
  };
}
