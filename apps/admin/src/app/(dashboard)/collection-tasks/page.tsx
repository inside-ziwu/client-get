import type { CollectionKeyword } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { CollectionTasksPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<CollectionKeyword>>({
  queryKey: ['admin', 'collection-keywords'],
  fetchFn: (token) => serverApi.get('/api/v1/collection-keywords', { token }),
  Component: CollectionTasksPage,
});
