import type { IntelligenceSource } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { IntelligenceSourcesPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<IntelligenceSource>>({
  queryKey: ['admin', 'intelligence-sources'],
  fetchFn: (token) => serverApi.get('/api/v1/intelligence-sources', { token }),
  Component: IntelligenceSourcesPage,
});
