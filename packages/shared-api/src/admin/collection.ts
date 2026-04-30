import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface CollectionTaskInfo {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface CollectionKeyword {
  keyword: string;
  keyword_normalized: string;
  tenants: Array<{ id: string; name: string }>;
  subscription_status:
    | 'not_started' | 'pending' | 'running'
    | 'paused' | 'error' | 'completed';
  // 直采（外贸通）
  stage1_current_page: number;
  stage1_total_pages: number | null;
  stage1_today_pages: number;
  stage1_status: CollectionTaskInfo['status'] | null;
  stage1_started_at: string | null;
  stage1_completed_at: string | null;
  // 反推（励销云 → 腾道）
  stage2_current_page: number;
  stage2_total_pages: number | null;
  stage2_today_pages: number;
  stage2_status: CollectionTaskInfo['status'] | null;
  stage2_started_at: string | null;
  stage2_completed_at: string | null;
  // 累计
  total_companies: number;
  total_contacts: number;
  last_run_date: string | null;
  daily_page_limit: number | null;
  error_msg: string | null;
}

export interface CollectionHistoryItem {
  task_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  error_message: string | null;
  result_summary: Record<string, unknown>;
  attempt_count: number;
}

export type ChannelKey = 'waimao_tong' | 'lixiaoyun';

export interface CollectionDashboardStats {
  today_companies: number;
  today_contacts: number;
  running_count: number;
  paused_count: number;
  error_count: number;
  keywords: CollectionKeyword[];
}

export interface RawCompanyRow {
  id: string;
  source_id?: string;
  tid?: string;
  name: string;
  country?: string;
  domain?: string | null;
  task_id?: string | null;
  created_at: string;
  raw_payload: Record<string, unknown>;
}

export interface CleanCompanyRow {
  id: string;
  name_normalized: string;
  name_display: string;
  country_iso3: string | null;
  domain: string | null;
  sources: string[];
  created_at: string;
}

export interface CleanupHealthStats {
  pending_count: number;
  oldest_pending_seconds: number | null;
  failed_exhausted_count: number;
  processed_per_minute: number;
  reconcile_a: Array<Record<string, unknown>>;
  reconcile_b: Array<Record<string, unknown>>;
  reconcile_c: Array<Record<string, unknown>>;
}

export function collectionApi(client: AxiosInstance) {
  return {
    listKeywords: () =>
      client.get<PaginatedResponse<CollectionKeyword>>(
        '/api/v1/collection-keywords',
      ),
    trigger: (data: { keyword_normalized: string; channel: ChannelKey }) =>
      client.post<ApiResponse<{ task_id: string; channel: string; keyword: string }>>(
        '/api/v1/collection-keywords/trigger',
        data,
      ),
    listHistory: (keywordNormalized: string, channel: ChannelKey) =>
      client.get<PaginatedResponse<CollectionHistoryItem>>(
        `/api/v1/collection-keywords/${encodeURIComponent(keywordNormalized)}/history`,
        { params: { channel } },
      ),
    stop: (keywordNormalized: string) =>
      client.post<ApiResponse<null>>(
        `/api/v1/collection-keywords/${encodeURIComponent(keywordNormalized)}/stop`,
      ),
    reset: (keywordNormalized: string) =>
      client.post<ApiResponse<null>>(
        `/api/v1/collection-keywords/${encodeURIComponent(keywordNormalized)}/reset`,
      ),
    retry: (keywordNormalized: string) =>
      client.post<ApiResponse<null>>(
        `/api/v1/collection-keywords/${encodeURIComponent(keywordNormalized)}/retry`,
      ),
    getDashboard: () =>
      client.get<ApiResponse<CollectionDashboardStats>>(
        '/api/v1/collection/dashboard',
      ),
    listRawCompanies: (
      table: 'waimaotong' | 'tendata' | 'lixiaoyun',
      params: { page?: number; page_size?: number; keyword?: string; country?: string },
    ) =>
      client.get<PaginatedResponse<RawCompanyRow>>(
        `/api/v1/collection/raw/${table}`,
        { params },
      ),
    listCleanCompanies: (params: { page?: number; page_size?: number; keyword?: string }) =>
      client.get<PaginatedResponse<CleanCompanyRow>>(
        '/api/v1/collection/clean-companies',
        { params },
      ),
    getCleanupHealth: () =>
      client.get<ApiResponse<CleanupHealthStats>>(
        '/api/v1/collection/cleanup-health',
      ),
  };
}
