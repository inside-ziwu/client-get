import type { WaimaotongRawCompanyRow } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { WaimaotongArchivePage } from './client-page';

const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
  q: '',
  country: '',
  source_keyword: '',
  source_competitor: '',
  industry: '',
  size: '',
  year_min: '',
  year_max: '',
  has_contacts: false,
};

export default createPrefetchPage<PaginatedResponse<WaimaotongRawCompanyRow>>({
  queryKey: ['admin', 'waimaotong', 'raw-companies', 1, PAGE_SIZE, EMPTY_FILTERS],
  fetchFn: (token) => serverApi.get('/api/v1/raw/waimaotong/companies', {
    token,
    params: { page: 1, page_size: PAGE_SIZE },
  }),
  Component: WaimaotongArchivePage,
});
