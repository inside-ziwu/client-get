import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { TendataArchivePage } from './client-page';

const PAGE_SIZE = 20;
const EMPTY_FILTERS = { keyword: '', country: '' };

export default createPrefetchPage<PaginatedResponse<unknown>>({
  queryKey: ['admin', 'collection', 'tendata', 1, EMPTY_FILTERS],
  fetchFn: (token) => serverApi.get('/api/v1/collection/raw/tendata', {
    token,
    params: { page: 1, page_size: PAGE_SIZE },
  }),
  Component: TendataArchivePage,
});
