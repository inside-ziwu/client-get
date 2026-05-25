'use client';

import { useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@shared/ui';
import { queryKeys } from '@shared/api';
import { tenantApi } from '@/lib/api';
import { DateRangePicker, getPresetRange } from '@/components/pages/dashboard/date-range-picker';
import { StatsSection } from '@/components/pages/dashboard/stats-section';
import { EmailTrendChart } from '@/components/pages/dashboard/email-trend-chart';
import { PlanOverview } from '@/components/pages/dashboard/plan-overview';
import { QuotaBalance } from '@/components/pages/dashboard/quota-balance';

export default function DashboardPage() {
  // 日期范围状态
  const [dateRange, setDateRange] = useState(() => getPresetRange('last30'));

  // 计划选择状态
  const [selectedPlanId, setSelectedPlanId] = useState<string | undefined>();

  // 邮件统计查询（日期联动）
  const emailStatsQuery = useQuery({
    queryKey: queryKeys.dashboard.emailStats(dateRange as unknown as Record<string, unknown>),
    queryFn: async () => (await tenantApi.dashboard.emailStats(dateRange)).data.data,
    placeholderData: keepPreviousData,
  });

  // 计划概览查询（计划选择联动）
  const planOverviewQuery = useQuery({
    queryKey: queryKeys.dashboard.planOverview({ plan_id: selectedPlanId }),
    queryFn: async () => (await tenantApi.dashboard.planOverview({ plan_id: selectedPlanId })).data.data,
  });

  // 每日配额查询（页面加载）
  const dailyQuotaQuery = useQuery({
    queryKey: queryKeys.dashboard.dailyQuota(),
    queryFn: async () => (await tenantApi.dashboard.dailyQuota()).data.data,
  });

  // LLM 余额查询（页面加载）
  const llmBalanceQuery = useQuery({
    queryKey: queryKeys.dashboard.llmBalance(),
    queryFn: async () => (await tenantApi.dashboard.llmBalance()).data.data,
  });

  const isFetchingStats = emailStatsQuery.isFetching && emailStatsQuery.data !== undefined;

  return (
    <div className="tenant-page">
      {/* 顶部 loading 条 */}
      {isFetchingStats && (
        <div className="fixed inset-x-0 top-0 z-50 h-0.5">
          <div className="h-full animate-pulse bg-primary" />
        </div>
      )}

      {/* 标题 + 日期选择器 */}
      <div className="tenant-page-header">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="tenant-page-title">仪表盘</h1>
            <p className="tenant-page-description">邮件运营数据总览</p>
          </div>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </div>
      </div>

      {/* 发送统计 + 追踪统计 */}
      <StatsSection
        data={emailStatsQuery.data?.summary}
        isLoading={emailStatsQuery.isLoading}
        isError={emailStatsQuery.isError}
        refetch={emailStatsQuery.refetch}
      />

      {/* 趋势图 */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">发送趋势</CardTitle>
        </CardHeader>
        <CardContent>
          {emailStatsQuery.isLoading ? (
            <div className="h-[300px] animate-pulse rounded bg-muted" />
          ) : emailStatsQuery.isError ? (
            <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
              加载失败，点击重试
            </div>
          ) : (
            <EmailTrendChart data={emailStatsQuery.data?.daily ?? []} />
          )}
        </CardContent>
      </Card>

      {/* 底部：计划概览 + 配额余额 */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <PlanOverview
          data={planOverviewQuery.data}
          isLoading={planOverviewQuery.isLoading}
          isError={planOverviewQuery.isError}
          refetch={planOverviewQuery.refetch}
          selectedPlanId={selectedPlanId}
          onPlanChange={setSelectedPlanId}
        />
        <QuotaBalance
          quota={{
            data: dailyQuotaQuery.data,
            isLoading: dailyQuotaQuery.isLoading,
            isError: dailyQuotaQuery.isError,
            refetch: dailyQuotaQuery.refetch,
          }}
          balance={{
            data: llmBalanceQuery.data,
            isLoading: llmBalanceQuery.isLoading,
            isError: llmBalanceQuery.isError,
            refetch: llmBalanceQuery.refetch,
          }}
        />
      </div>
    </div>
  );
}
