import type { LixiaoyunRawCompanyRow } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { PeersDataPage } from './client-page';

const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
  name: '',
  keyword_filter: '',
  found_from: '',
  found_to: '',
  reg_capital: '',
  employee_scale: '',
  has_name_en: false,
  has_domain: false,
};

export default createPrefetchPage<PaginatedResponse<LixiaoyunRawCompanyRow>>({
  queryKey: ['admin', 'peers', 'raw-lixiaoyun', 1, PAGE_SIZE, EMPTY_FILTERS],
  fetchFn: (token) => serverApi.get('/api/v1/raw/lixiaoyun/companies', {
    token,
    params: { page: 1, page_size: PAGE_SIZE },
  }),
  Component: PeersDataPage,
});
