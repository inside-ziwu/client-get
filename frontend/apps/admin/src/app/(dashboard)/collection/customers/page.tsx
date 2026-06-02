import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { CustomerArchivePage } from './client-page';

const PAGE_SIZE = 20;

const EMPTY_FILTERS = {
  q: '',
  country: '',
  industry: '',
  size: '',
  year_min: '',
  year_max: '',
  has_contacts: false,
};

export default createPrefetchPage<PaginatedResponse<unknown>>({
  queryKey: ['admin', 'wmt-clean-companies', 1, PAGE_SIZE, EMPTY_FILTERS],
  fetchFn: (token) => serverApi.get('/api/v1/collection/wmt-clean-companies', {
    token,
    params: { page: 1, page_size: PAGE_SIZE },
  }),
  Component: CustomerArchivePage,
});
