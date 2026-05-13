import type { PaginatedResponse } from '@shared/types';
import type { WarmupRules } from '@shared/api';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { WarmupRulesClientPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<WarmupRules>>({
  queryKey: ['admin', 'warmup-rules'],
  fetchFn: (token) => serverApi.get('/api/v1/warmup-rules', { token }),
  Component: WarmupRulesClientPage,
});
