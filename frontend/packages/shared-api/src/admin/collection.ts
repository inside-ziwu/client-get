import type { AxiosInstance } from 'axios';
import type { ApiResponse, PaginatedResponse } from '@shared/types';

export interface LixiaoyunRawCompanyRow {
  id: string;
  pid: string | null;
  keyword_master_id: string | null;
  keyword: string | null;
  entname: string | null;
  entname_eng: string | null;
  esdate: string | null;
  reg_cap: string | null;
  official_website: string | null;
  regccap: string | null;
  scale: string | null;
  annual_turnover: string | null;
  legalperson: string | null;
  geo_address: string | null;
  dom: string | null;
  collected_at: string | null;
}

export interface LixiaoyunApiCompanyDetail extends LixiaoyunRawCompanyRow {
  provider?: string;
  entstatus?: string | null;
  enttype?: string | null;
  opscope?: string | null;
  industryphy_desc?: string | null;
  secindustry_desc?: string[] | string | null;
  industry_l3_desc?: string | null;
  industry_l4_desc?: string | null;
  uncid?: string | null;
  ent_introduction?: string | null;
  opfrom?: string | null;
  opto?: string | null;
  regorg?: string | null;
  apprdate?: string | null;
  oploc?: string | null;
}

export interface WaimaotongRawCompanyRow {
  id: string;
  company_name: string | null;
  country: string | null;
  domain: string | null;
  industry: string | null;
  employee_size: string | null;
  founded_year: number | null;
  full_address: string | null;
  source_keyword: string | null;
  source_competitor: string | null;
  source_type: string | null;
  contacts_count: number | null;
  email_count: number | null;
  has_detail: boolean | null;
  has_contacts: boolean | null;
  id_verified: boolean | null;
  website: string | null;
  api_company_id: string | null;
  created_at: string;
}

export interface WaimaotongRawContactRow {
  id: string;
  raw_company_id: string;
  source_contact_id: string | null;
  name: string | null;
  position: string | null;
  department: string | null;
  email: string | null;
  email_status: string | null;
  phone: string | null;
  linkedin: string | null;
  source: string | null;
  confidence: number | null;
  created_at: string;
}

export interface WmtCleanCompanyRow {
  id: string;
  source_id: string | null;
  name: string | null;
  company_name: string | null;
  english_name: string | null;
  country: string | null;
  country_iso3: string | null;
  domain: string | null;
  industry: string | null;
  sub_industry: string | null;
  phone: string | null;
  employee_size: string | null;
  company_size: string | null;
  founded_year: number | null;
  website: string | null;
  full_address: string | null;
  description: string | null;
  grade: string | null;
  score: number | null;
  email_priority: string | null;
  company_type_analysis: string | null;
  product_tags: string[];
  data_source_tags: string[];
  collection_type: 'manual' | 'keyword' | 'reverse' | 'unknown';
  has_trade_data: boolean | null;
  trade_amount_3y_usd: number | null;
  trade_count: number | null;
  contacts_count: number | null;
  detail_status: string | null;
  contacts_status: string | null;
  trade_status: string | null;
  sys_company_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface WmtCleanCompanyDetail extends WmtCleanCompanyRow {
  score_details: unknown[] | null;
  match_reasons: unknown[] | null;
  potential_needs: unknown[] | null;
  recommended_products: unknown[] | null;
  risk_factors: unknown[] | null;
  main_business: unknown[] | null;
  trade_summary: Record<string, unknown> | null;
  sales_approach: string | null;
}

export interface WmtCleanContactRow {
  id: string;
  name: string | null;
  position: string | null;
  department: string | null;
  email: string | null;
  email_status: string | null;
  phone: string | null;
  mobile: string | null;
  linkedin: string | null;
  whatsapp: string | null;
  source: string | null;
  confidence: number | null;
  created_at: string | null;
}

export interface LixiaoyunCleanCompanyKeyword {
  keyword_master_id: string;
  keyword: string;
  keyword_normalized: string;
}

export interface LixiaoyunCleanCompanyRow {
  id: string;
  pid: string | null;
  entname: string | null;
  entname_eng: string | null;
  esdate: string | null;
  reg_cap: string | null;
  official_website: string | null;
  regccap: string | null;
  scale: string | null;
  annual_turnover: string | null;
  legalperson: string | null;
  geo_address: string | null;
  dom: string | null;
  industry_tag: string | null;
  keyword_master: LixiaoyunCleanCompanyKeyword[];
  created_at: string | null;
}

export interface LixiaoyunCleanCompanyDetail extends LixiaoyunCleanCompanyRow {
  uncid: string | null;
  enttype: string | null;
  enttype_code: string | null;
  entstatus: string | null;
  entstatus_code: number | null;
  regno: string | null;
  organizational_code: string | null;
  opfrom: number | null;
  opto: number | null;
  regorg: string | null;
  apprdate: number | null;
  revokedate: number | null;
  province: number | null;
  city: number | null;
  district: number | null;
  reg_province: number | null;
  reg_city: number | null;
  reg_district: number | null;
  oploc: string | null;
  industryphy: string | null;
  industryphy_desc: string | null;
  opscope: string | null;
  secindustry: unknown;
  secindustry_desc: unknown;
  industry_l3: string | null;
  industry_l3_desc: string | null;
  industry_l4: string | null;
  industry_l4_desc: string | null;
  historyname_list: unknown;
  legalperson_desc: string | null;
  location_code: string | null;
  updated_at: string | null;
}

export function collectionApi(client: AxiosInstance) {
  return {
    listLixiaoyunRawCompanies: (params: {
      page?: number;
      page_size?: number;
      keyword?: string;
      keyword_filter?: string;
      found_date_start?: string;
      found_date_end?: string;
      reg_capital?: string;
      employee_scale?: string;
      has_name_en?: boolean;
      has_domain?: boolean;
    }) =>
      client.get<PaginatedResponse<LixiaoyunRawCompanyRow>>(
        '/api/v1/raw/lixiaoyun/companies',
        { params },
      ),
    getLixiaoyunRawCompanyDebug: (rawCompanyId: string) =>
      client.get<ApiResponse<LixiaoyunApiCompanyDetail>>(
        `/api/v1/raw/lixiaoyun/companies/${encodeURIComponent(rawCompanyId)}/debug`,
      ),
    listWaimaotongRawCompanies: (params: {
      page?: number;
      page_size?: number;
      q?: string;
      country?: string;
      source_keyword?: string;
      source_competitor?: string;
      industry?: string;
      size?: string;
      year_min?: number;
      year_max?: number;
      has_contacts?: boolean;
    }) =>
      client.get<PaginatedResponse<WaimaotongRawCompanyRow>>(
        '/api/v1/raw/waimaotong/companies',
        { params },
      ),
    getWaimaotongRawCompanyDebug: (rawCompanyId: string) =>
      client.get<ApiResponse<Record<string, unknown>>>(
        `/api/v1/raw/waimaotong/companies/${encodeURIComponent(rawCompanyId)}/debug`,
      ),
    listWaimaotongRawCompanyContacts: (rawCompanyId: string) =>
      client.get<PaginatedResponse<WaimaotongRawContactRow>>(
        `/api/v1/raw/waimaotong/companies/${encodeURIComponent(rawCompanyId)}/contacts`,
      ),
    listLixiaoyunCleanCompanies: (params: {
      page?: number;
      page_size?: number;
      keyword?: string;
      keyword_filter?: string;
      industry_tag?: string;
      found_date_start?: string;
      found_date_end?: string;
      reg_capital?: string;
      employee_scale?: string;
      has_name_en?: boolean;
      has_domain?: boolean;
    }) =>
      client.get<PaginatedResponse<LixiaoyunCleanCompanyRow>>(
        '/api/v1/collection/lixiaoyun-clean-companies',
        { params },
      ),
    getLixiaoyunCleanCompanyDetail: (id: number) =>
      client.get<ApiResponse<LixiaoyunCleanCompanyDetail>>(
        `/api/v1/collection/lixiaoyun-clean-companies/${id}`,
      ),
    listWmtCleanCompanies: (params: {
      page?: number;
      page_size?: number;
      q?: string;
      country?: string;
      industry?: string;
      size?: string;
      year_min?: number;
      year_max?: number;
      has_contacts?: boolean;
      grade?: string;
      collection_type?: string;
    }) =>
      client.get<PaginatedResponse<WmtCleanCompanyRow>>(
        '/api/v1/collection/wmt-clean-companies',
        { params },
      ),
    getWmtCleanCompany: (companyId: number) =>
      client.get<ApiResponse<WmtCleanCompanyDetail>>(
        `/api/v1/collection/wmt-clean-companies/${companyId}`,
      ),
    listWmtCleanCompanyContacts: (companyId: number) =>
      client.get<PaginatedResponse<WmtCleanContactRow>>(
        `/api/v1/collection/wmt-clean-companies/${companyId}/contacts`,
      ),
  };
}
