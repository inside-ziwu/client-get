import type { ClassificationLevel } from '@shared/api';
import type { PaginatedResponse } from '@shared/types';
import { createPrefetchPage } from '@/lib/create-prefetch-page';
import { serverApi } from '@/lib/server-api';
import { ContactClassificationPage } from './client-page';

export default createPrefetchPage<PaginatedResponse<ClassificationLevel>>({
  queryKey: ['admin', 'contact-classification'],
  fetchFn: (token) => serverApi.get('/api/v1/contact-classification/levels', { token }),
  Component: ContactClassificationPage,
});
