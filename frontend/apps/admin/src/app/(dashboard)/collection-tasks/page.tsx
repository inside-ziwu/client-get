import type { CollectionKeyword } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { CollectionTasksPage } from './client-page';

export default createPrefetchPage<CollectionKeyword[]>({
  queryKey: ['admin', 'collection-keywords'],
  fetchFn: async (token) => {
    const res = await serverApi.get<PaginatedResponse<CollectionKeyword>>(
      '/api/v1/collection-keywords',
      { token },
    );
    return res.data;
  },
  Component: CollectionTasksPage,
});
