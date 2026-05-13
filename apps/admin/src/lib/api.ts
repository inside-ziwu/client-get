import { createAdminApi, createApiClient } from '@shared/api';

const adminBaseURL = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL ?? '';
const client = createApiClient('admin', { baseURL: adminBaseURL });

export const adminApi = createAdminApi(client);
