import { createApiClient, createTenantApi } from '@shared/api';

const tenantBaseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
const client = createApiClient('tenant', { baseURL: tenantBaseURL });

export const tenantApi = createTenantApi(client);
