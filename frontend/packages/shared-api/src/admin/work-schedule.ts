import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface TimeSegment {
  start: string;
  end: string;
}

export interface WorkRuleSet {
  id: string;
  name: string;
  work_days: number[];
  time_segments: TimeSegment[];
  is_default: boolean;
  country_count: number;
  countries?: Country[];
  created_at: string;
  updated_at: string;
}

export interface Country {
  iso3: string;
  name_zh: string;
  name_en: string;
  timezone: string;
  rule_set_id: string | null;
  rule_set_name: string | null;
  holiday_count: number;
  holidays?: Holiday[];
  created_at: string;
  updated_at: string;
}

export interface Holiday {
  id: string;
  country_iso3: string;
  date: string;
  name: string | null;
  source: 'manual' | 'seed' | string;
  created_at: string;
}

export interface CountryFilters {
  search?: string;
  has_rule_set?: boolean;
}

export function workScheduleApi(client: AxiosInstance) {
  return {
    listRuleSets: () =>
      client.get<PaginatedResponse<WorkRuleSet>>('/api/v1/work-schedule/rule-sets'),
    createRuleSet: (data: Pick<WorkRuleSet, 'name' | 'work_days' | 'time_segments'>) =>
      client.post<ApiResponse<WorkRuleSet>>('/api/v1/work-schedule/rule-sets', data),
    getRuleSet: (id: string) =>
      client.get<ApiResponse<WorkRuleSet>>(`/api/v1/work-schedule/rule-sets/${id}`),
    updateRuleSet: (id: string, data: Partial<Pick<WorkRuleSet, 'name' | 'work_days' | 'time_segments'>>) =>
      client.patch<ApiResponse<WorkRuleSet>>(`/api/v1/work-schedule/rule-sets/${id}`, data),
    deleteRuleSet: (id: string) =>
      client.delete<ApiResponse<{ deleted: boolean }>>(`/api/v1/work-schedule/rule-sets/${id}`),
    assignCountries: (id: string, countries: string[]) =>
      client.post<PaginatedResponse<Country>>(`/api/v1/work-schedule/rule-sets/${id}/countries`, { countries }),
    removeCountry: (id: string, iso3: string) =>
      client.delete<ApiResponse<Country>>(`/api/v1/work-schedule/rule-sets/${id}/countries/${iso3}`),
    listCountries: (params?: CountryFilters) =>
      client.get<PaginatedResponse<Country>>('/api/v1/work-schedule/countries', { params }),
    getCountry: (iso3: string) =>
      client.get<ApiResponse<Country>>(`/api/v1/work-schedule/countries/${iso3}`),
    updateCountry: (iso3: string, data: { timezone?: string; rule_set_id?: string | null }) =>
      client.patch<ApiResponse<Country>>(`/api/v1/work-schedule/countries/${iso3}`, data),
    listHolidays: (iso3: string, year?: number) =>
      client.get<PaginatedResponse<Holiday>>(`/api/v1/work-schedule/countries/${iso3}/holidays`, { params: { year } }),
    createHoliday: (iso3: string, data: { date: string; name?: string; source?: string }) =>
      client.post<ApiResponse<Holiday>>(`/api/v1/work-schedule/countries/${iso3}/holidays`, data),
    updateHoliday: (iso3: string, id: string, data: Partial<Pick<Holiday, 'date' | 'name' | 'source'>>) =>
      client.patch<ApiResponse<Holiday>>(`/api/v1/work-schedule/countries/${iso3}/holidays/${id}`, data),
    deleteHoliday: (iso3: string, id: string) =>
      client.delete<ApiResponse<{ deleted: boolean }>>(`/api/v1/work-schedule/countries/${iso3}/holidays/${id}`),
    getDefaultRule: () =>
      client.get<ApiResponse<WorkRuleSet>>('/api/v1/work-schedule/default-rule'),
    updateDefaultRule: (data: Partial<Pick<WorkRuleSet, 'name' | 'work_days' | 'time_segments'>>) =>
      client.patch<ApiResponse<WorkRuleSet>>('/api/v1/work-schedule/default-rule', data),
  };
}
