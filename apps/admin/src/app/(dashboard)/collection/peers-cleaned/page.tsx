import type { PeerCompanyRow } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { PeersCleanedPage } from './client-page';

const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
  name: '',
  keyword_filter: '',
  found_date_start: '',
  found_date_end: '',
  reg_capital: '',
  employee_scale: '',
  contacts_count: '',
  has_name_en: false,
  has_domain: false,
};

export default createPrefetchPage<PaginatedResponse<PeerCompanyRow>>({
  queryKey: ['admin', 'peer-companies', 1, PAGE_SIZE, EMPTY_FILTERS],
  fetchFn: (token) => serverApi.get('/api/v1/collection/peer-companies', {
    token,
    params: { page: 1, page_size: PAGE_SIZE },
  }),
  Component: PeersCleanedPage,
});
