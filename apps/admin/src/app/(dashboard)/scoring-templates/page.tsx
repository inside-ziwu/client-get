import type { ScoringTemplate } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { ScoringTemplatesPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<ScoringTemplate>>({
  queryKey: ['admin', 'scoring-templates', ''],
  fetchFn: (token) => serverApi.get('/api/v1/scoring-templates', { token, params: { industry: undefined } }),
  Component: ScoringTemplatesPage,
});
