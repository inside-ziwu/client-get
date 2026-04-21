import type { AxiosInstance } from 'axios';
import type {
  ApiResponse,
  PaginatedResponse,
  PaginationParams,
  BillingBalance,
  UsageSummary,
  UsageTrend,
} from '@shared/types';

export interface BalanceTransaction {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  description?: string;
  created_at: string;
}

export function billingApi(client: AxiosInstance) {
  return {
    balance: () =>
      client.get<ApiResponse<BillingBalance>>('/api/v1/billing/balance'),
    transactions: (params?: PaginationParams) =>
      client.get<PaginatedResponse<BalanceTransaction>>('/api/v1/billing/transactions', { params }),
    usageSummary: (period?: string) =>
      client.get<ApiResponse<UsageSummary>>('/api/v1/billing/usage-summary', { params: { period } }),
    usageTrend: (params?: { date_from?: string; date_to?: string }) =>
      client.get<PaginatedResponse<UsageTrend>>('/api/v1/billing/usage-trend', { params }),
  };
}
