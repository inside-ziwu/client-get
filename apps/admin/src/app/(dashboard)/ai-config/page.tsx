import type { ApiResponse } from '@shared/types';
import type { AiPricingResponse } from '@shared/api';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { AIConfigPage } from './client-page';

export default createPrefetchPage<ApiResponse<AiPricingResponse>>({
  queryKey: ['admin', 'ai-config'],
  fetchFn: (token) => serverApi.get('/api/v1/ai-config/pricing', { token }),
  Component: AIConfigPage,
});
