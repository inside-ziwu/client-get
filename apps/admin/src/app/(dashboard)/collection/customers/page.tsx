import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { CustomerArchivePage } from './client-page';

const PAGE_SIZE = 20;

export default createPrefetchPage<PaginatedResponse<unknown>>({
  queryKey: ['admin', 'collection', 'clean-companies', 1, ''],
  fetchFn: (token) => serverApi.get('/api/v1/collection/clean-companies', {
    token,
    params: { page: 1, page_size: PAGE_SIZE },
  }),
  Component: CustomerArchivePage,
});
