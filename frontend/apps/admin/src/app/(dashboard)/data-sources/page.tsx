import type { PaginatedResponse } from '@shared/types';
import type { DataSource } from '@shared/api';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { DataSourcesPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<DataSource>>({
  queryKey: ['admin', 'data-sources'],
  fetchFn: (token) => serverApi.get('/api/v1/data-sources', { token }),
  Component: DataSourcesPage,
});
