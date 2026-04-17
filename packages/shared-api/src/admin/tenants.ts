import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  TenantFilters,
  BillingBalance,
} from '@shared/types';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: 'active' | 'suspended' | 'archived';
  plan: string;
  company_limit: number;
  user_limit: number;
  created_at: string;
  updated_at: string;
}

export interface TenantDomain {
  id: string;
  domain: string;
  verification_status: 'pending' | 'verifying' | 'verified' | 'failed';
  dns_records: Array<{ type: string; name: string; value: string }>;
  created_at: string;
}

export interface TenantTeamUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  created_at: string;
}

export function tenantsApi(client: AxiosInstance) {
  return {
    list: (filters?: TenantFilters) =>
      client.get<PaginatedResponse<Tenant>>('/api/v1/tenants', { params: filters }),
    create: (data: Partial<Tenant>) =>
      client.post<ApiResponse<Tenant>>('/api/v1/tenants', data),
    detail: (id: string) =>
      client.get<ApiResponse<Tenant>>(`/api/v1/tenants/${id}`),
    update: (id: string, data: Partial<Tenant>) =>
      client.put<ApiResponse<Tenant>>(`/api/v1/tenants/${id}`, data),

    // Domains
    listDomains: (tenantId: string) =>
      client.get<ApiResponse<TenantDomain[]>>(`/api/v1/tenants/${tenantId}/domains`),
    createDomain: (tenantId: string, data: { domain: string }) =>
      client.post<ApiResponse<TenantDomain>>(`/api/v1/tenants/${tenantId}/domains`, data),
    deleteDomain: (tenantId: string, domainId: string) =>
      client.delete(`/api/v1/tenants/${tenantId}/domains/${domainId}`),
    verifyDomain: (tenantId: string, domainId: string) =>
      client.post<ApiResponse<TenantDomain>>(`/api/v1/tenants/${tenantId}/domains/${domainId}/verify`),

    // Team
    listTeam: (tenantId: string) =>
      client.get<ApiResponse<TenantTeamUser[]>>(`/api/v1/tenants/${tenantId}/team`),
    createTeamUser: (tenantId: string, data: Partial<TenantTeamUser>) =>
      client.post<ApiResponse<TenantTeamUser>>(`/api/v1/tenants/${tenantId}/team`, data),
    updateTeamUser: (tenantId: string, userId: string, data: Partial<TenantTeamUser>) =>
      client.put<ApiResponse<TenantTeamUser>>(`/api/v1/tenants/${tenantId}/team/${userId}`, data),
    deleteTeamUser: (tenantId: string, userId: string) =>
      client.delete(`/api/v1/tenants/${tenantId}/team/${userId}`),

    // Balance
    getBalance: (tenantId: string) =>
      client.get<ApiResponse<BillingBalance>>(`/api/v1/tenants/${tenantId}/balance`),
    adjustBalance: (tenantId: string, data: { amount: number; reason: string }) =>
      client.post<ApiResponse<BillingBalance>>(`/api/v1/tenants/${tenantId}/balance/adjust`, data),
  };
}
