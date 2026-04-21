import { createApiClient, createTenantApi } from '@shared/api';

const client = createApiClient('tenant');

export const tenantApi = createTenantApi(client);
