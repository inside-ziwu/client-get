import type { ApiResponse, IndustryNewsSource } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { IndustryNewsSourcesPage } from './client-page';

export default createPrefetchPage<ApiResponse<IndustryNewsSource[]>>({
  queryKey: ['admin', 'industry-news-sources'],
  fetchFn: (token) => serverApi.get('/api/v1/industry-news-sources', { token }),
  Component: IndustryNewsSourcesPage,
});
