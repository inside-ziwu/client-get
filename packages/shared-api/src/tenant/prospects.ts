import type { AxiosInstance } from 'axios';
import type { PaginatedResponse, CustomerFilters } from '@shared/types';

export interface Prospect {
  id: string;
  company_id: string;
  company_name?: string;
  name: string;
  email: string;
  title?: string;
  seniority?: string;
  grade?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export function prospectsApi(client: AxiosInstance) {
  return {
    list: (filters?: CustomerFilters & { group_id?: string }) =>
      client.get<PaginatedResponse<Prospect>>('/api/v1/prospects', { params: filters }),
  };
}
