import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  TenantFilters,
  AiProviderConfig,
} from '@shared/types';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  industry?: string;
  status: 'active' | 'suspended' | 'archived';
  needs_onboarding?: boolean;
  contact_name?: string;
  contact_phone?: string;
  contact_email?: string;
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
  roles: string[];
  must_change_pwd?: boolean;
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
      client.patch<ApiResponse<Tenant>>(`/api/v1/tenants/${id}`, data),
    suspend: (id: string) =>
      client.post<ApiResponse<Tenant>>(`/api/v1/tenants/${id}/suspend`),
    activate: (id: string) =>
      client.post<ApiResponse<Tenant>>(`/api/v1/tenants/${id}/activate`),

    // Domains
    listDomains: (tenantId: string) =>
      client.get<PaginatedResponse<TenantDomain>>(`/api/v1/tenants/${tenantId}/domains`),
    createDomain: (tenantId: string, data: { domain: string }) =>
      client.post<ApiResponse<TenantDomain>>(`/api/v1/tenants/${tenantId}/domains`, data),
    verifyDomain: (tenantId: string, domainId: string) =>
      client.post<ApiResponse<TenantDomain>>(`/api/v1/tenants/${tenantId}/domains/${domainId}/verify`),
    getDomain: (tenantId: string, domainId: string) =>
      client.get<ApiResponse<TenantDomain>>(`/api/v1/tenants/${tenantId}/domains/${domainId}`),

    // Team
    listTeam: (tenantId: string) =>
      client.get<PaginatedResponse<TenantTeamUser>>(`/api/v1/tenants/${tenantId}/users`),
    createTeamUser: (tenantId: string, data: Partial<TenantTeamUser>) =>
      client.post<ApiResponse<TenantTeamUser>>(`/api/v1/tenants/${tenantId}/users`, data),
    updateTeamUser: (tenantId: string, userId: string, data: Partial<TenantTeamUser>) =>
      client.patch<ApiResponse<TenantTeamUser>>(`/api/v1/tenants/${tenantId}/users/${userId}`, data),
    deleteTeamUser: (tenantId: string, userId: string) =>
      client.delete(`/api/v1/tenants/${tenantId}/users/${userId}`),

    // AI provider
    getOpenRouter: (tenantId: string) =>
      client.get<ApiResponse<AiProviderConfig>>(`/api/v1/tenants/${tenantId}/ai-provider/openrouter`),
    updateOpenRouter: (tenantId: string, data: { api_key: string }) =>
      client.put<ApiResponse<AiProviderConfig>>(`/api/v1/tenants/${tenantId}/ai-provider/openrouter`, data),
    deleteOpenRouter: (tenantId: string) =>
      client.delete<ApiResponse<{ deleted: boolean }>>(`/api/v1/tenants/${tenantId}/ai-provider/openrouter`),
    refreshOpenRouterBalance: (tenantId: string) =>
      client.post<ApiResponse<AiProviderConfig>>(`/api/v1/tenants/${tenantId}/ai-provider/openrouter/balance/refresh`),
  };
}
