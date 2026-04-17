import type { AxiosInstance } from 'axios';
import type { ApiResponse } from '@shared/types';

export interface AiModel {
  id: string;
  name: string;
  provider: string;
  model_type: string;
  is_active: boolean;
  config: Record<string, unknown>;
}

export interface AiPricing {
  model_id: string;
  input_price_per_1k: number;
  output_price_per_1k: number;
  currency: string;
}

export interface AiSceneDefault {
  scene: string;
  model_id: string;
  temperature: number;
  max_tokens: number;
}

export function aiConfigApi(client: AxiosInstance) {
  return {
    getModels: () =>
      client.get<ApiResponse<AiModel[]>>('/api/v1/ai-config/models'),
    updateModels: (data: AiModel[]) =>
      client.put<ApiResponse<AiModel[]>>('/api/v1/ai-config/models', data),
    getPricing: () =>
      client.get<ApiResponse<AiPricing[]>>('/api/v1/ai-config/pricing'),
    updatePricing: (data: AiPricing[]) =>
      client.put<ApiResponse<AiPricing[]>>('/api/v1/ai-config/pricing', data),
    getSceneDefaults: () =>
      client.get<ApiResponse<AiSceneDefault[]>>('/api/v1/ai-config/scene-defaults'),
    updateSceneDefaults: (data: AiSceneDefault[]) =>
      client.put<ApiResponse<AiSceneDefault[]>>('/api/v1/ai-config/scene-defaults', data),
  };
}
