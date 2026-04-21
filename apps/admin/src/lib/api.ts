import { createAdminApi, createApiClient } from '@shared/api';

const client = createApiClient('admin');

export const adminApi = createAdminApi(client);
