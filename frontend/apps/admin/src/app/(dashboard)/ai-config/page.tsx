import type { ApiResponse } from '@shared/types';
import type { AiPricingResponse } from '@shared/api';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { AIConfigPage } from './client-page';

export default createPrefetchPage<AiPricingResponse>({
  queryKey: ['admin', 'ai-config'],
  fetchFn: async (token) => {
    const res = await serverApi.get<ApiResponse<AiPricingResponse>>(
      '/api/v1/ai-config/pricing',
      { token },
    );
    return res.data;
  },
  Component: AIConfigPage,
});
