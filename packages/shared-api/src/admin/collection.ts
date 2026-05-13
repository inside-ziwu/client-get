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
  total_companies: number;
  total_contacts: number;
  last_run_date: string | null;
  error_msg: string | null;

  // 直采（外贸通）按页计
  direct: {
    current_page: number;
    total_pages: number;
    today_pages: number;
    daily_limit: number | null;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | null;
    last_run_date: string | null;
  };

  // 反推 stage1：励销云
  reverse_stage1: {
    today_count: number;
    total_count: number;
    daily_limit: number | null;
    status: string | null;
    last_run_date: string | null;
  };

  // 反推 stage2：腾道
  reverse_stage2: {
    today_count: number;
    total_count: number;
    daily_limit: number | null;
    status: string | null;
    last_run_date: string | null;
  };
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

export interface LixiaoyunRawCompanyRow {
  id: string;
  keyword_master_id: string | null;
  source_id: string | null;
  name: string | null;
  english_name: string | null;
  domain: string | null;
  esdate: string | null;
  legalperson: string | null;
  uncid: string | null;
  reg_capital: string | null;
  employee_scale: string | null;
  reg_address: string | null;
  contacts_count: number;
  keyword_normalized: string | null;
  created_at: string | null;
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

export interface PeerCompanyKeyword {
  keyword_master_id: string;
  keyword: string;
  keyword_normalized: string;
}

export interface PeerCompanyRow {
  id: string;
  name: string | null;
  english_name: string | null;
  has_english_name: boolean;
  domain: string | null;
  website_host: string | null;
  identity_type: 'website_host' | 'source_id';
  identity_value: string;
  identity_source: string;
  identity_confidence: number;
  identity_rule_version: string;
  merge_reason: string | null;
  conflict_count: number;
  keywords: PeerCompanyKeyword[];
  keyword_count: number;
  raw_count: number;
  source_ids: string[];
  source_id: string | null;
  esdate: string | null;
  legalperson: string | null;
  uncid: string | null;
  reg_capital: string | null;
  employee_scale: string | null;
  reg_address: string | null;
  contact_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  created_at: string | null;
}

export interface PeerCompanyHealthStats {
  raw_count: number;
  peer_count: number;
  dedup_rate: number;
  english_name_coverage: number;
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
    listLixiaoyunRawCompanies: (params: {
      page?: number;
      page_size?: number;
      keyword?: string;
      keyword_filter?: string;
      found_date_start?: string;
      found_date_end?: string;
      reg_capital?: string;
      employee_scale?: string;
      contacts_filter?: string;
      has_name_en?: boolean;
      has_domain?: boolean;
    }) =>
      client.get<PaginatedResponse<LixiaoyunRawCompanyRow>>(
        '/api/v1/raw/lixiaoyun/companies',
        { params },
      ),
    listCleanCompanies: (params: { page?: number; page_size?: number; keyword?: string }) =>
      client.get<PaginatedResponse<CleanCompanyRow>>(
        '/api/v1/collection/clean-companies',
        { params },
      ),
    listPeerCompanies: (params: {
      page?: number;
      page_size?: number;
      keyword?: string;
      keyword_filter?: string;
      found_date_start?: string;
      found_date_end?: string;
      reg_capital?: string;
      employee_scale?: string;
      contacts_count?: string;
      has_name_en?: boolean;
      has_domain?: boolean;
    }) =>
      client.get<PaginatedResponse<PeerCompanyRow>>(
        '/api/v1/collection/peer-companies',
        { params },
      ),
    getPeerCompany: (id: string) =>
      client.get<ApiResponse<PeerCompanyRow>>(
        `/api/v1/collection/peer-companies/${encodeURIComponent(id)}`,
      ),
    getPeerCompanyHealth: () =>
      client.get<ApiResponse<PeerCompanyHealthStats>>(
        '/api/v1/collection/peer-companies/health',
      ),
    getCleanupHealth: () =>
      client.get<ApiResponse<CleanupHealthStats>>(
        '/api/v1/collection/cleanup-health',
      ),
  };
}
