import type { Tenant } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { TenantsPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<Tenant>>({
  queryKey: ['admin', 'tenants', ''],
  fetchFn: (token) => serverApi.get('/api/v1/tenants', { token }),
  Component: TenantsPage,
});
