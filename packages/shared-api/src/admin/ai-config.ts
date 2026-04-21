import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface AiModel {
  id: string;
  display_name: string;
  provider: string;
  model_id: string;
  model_type: string;
  input_price: number;
  output_price: number;
  is_active: boolean;
  config: Record<string, unknown>;
}

export interface AiPricing {
  model_id: string;
  input_price: number;
  output_price: number;
}

export interface AiSceneDefault {
  id?: string;
  scene: string;
  model_id: string;
  model_display_name?: string;
  fallback_model_ids?: string[];
  config?: Record<string, unknown>;
}

export interface AiPricingResponse {
  models: AiModel[];
  scene_defaults: AiSceneDefault[];
}

export function aiConfigApi(client: AxiosInstance) {
  return {
    getModels: () =>
      client.get<PaginatedResponse<AiModel>>('/api/v1/ai-config/models'),
    createModel: (data: Partial<AiModel>) =>
      client.post<ApiResponse<AiModel>>('/api/v1/ai-config/models', data),
    updateModel: (id: string, data: Partial<AiModel>) =>
      client.patch<ApiResponse<AiModel>>(`/api/v1/ai-config/models/${id}`, data),
    deleteModel: (id: string) =>
      client.delete(`/api/v1/ai-config/models/${id}`),
    getPricing: () =>
      client.get<ApiResponse<AiPricingResponse>>('/api/v1/ai-config/pricing'),
    updatePricing: (data: AiPricing[]) =>
      client.put<ApiResponse<AiPricingResponse>>('/api/v1/ai-config/pricing', { items: data }),
    getSceneDefaults: () =>
      client.get<PaginatedResponse<AiSceneDefault>>('/api/v1/ai-config/scene-defaults'),
    updateSceneDefaults: (data: AiSceneDefault[]) =>
      client.put<ApiResponse<AiSceneDefault[]>>('/api/v1/ai-config/scene-defaults', { items: data }),
  };
}
