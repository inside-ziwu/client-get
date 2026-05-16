import type { PlatformEmailTemplate } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { EmailTemplatesPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<PlatformEmailTemplate>>({
  queryKey: ['admin', 'email-templates'],
  fetchFn: (token) => serverApi.get('/api/v1/email-templates', { token }),
  Component: EmailTemplatesPage,
});
