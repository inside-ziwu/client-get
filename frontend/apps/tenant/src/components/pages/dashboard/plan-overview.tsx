'use client';

import { useRouter } from 'next/navigation';
import { RefreshCw } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, StatCard } from '@shared/ui';
import type { PlanOverviewResponse } from '@shared/types';

interface PlanOverviewProps {
  data: PlanOverviewResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
  selectedPlanId: string | undefined;
  onPlanChange: (planId: string | undefined) => void;
}

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg border bg-card p-4">
      <div className="h-3 w-16 rounded bg-muted" />
      <div className="mt-3 h-7 w-20 rounded bg-muted" />
    </div>
  );
}

export function PlanOverview({
  data,
  isLoading,
  isError,
  refetch,
  selectedPlanId,
  onPlanChange,
}: PlanOverviewProps) {
  const router = useRouter();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-base">计划概览</CardTitle>
        {data?.plans && data.plans.length > 0 && (
          <select
            className="h-8 rounded-md border border-input bg-background px-2 text-sm"
            value={selectedPlanId ?? ''}
            onChange={(e) => onPlanChange(e.target.value || undefined)}
          >
            <option value="">全部计划</option>
            {data.plans.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : isError ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
            加载失败
            <Button variant="outline" size="sm" onClick={refetch}>
              <RefreshCw className="mr-1 h-3 w-3" />
              重试
            </Button>
          </div>
        ) : !data?.plans?.length ? (
          <div className="flex flex-col items-center gap-3 py-8 text-sm text-muted-foreground">
            暂无计划
            <Button size="sm" onClick={() => router.push('/sending-plans/create')}>
              去创建
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <StatCard label="关键词" value={data.keyword_count.toLocaleString()} />
            <StatCard label="已采集公司" value={data.companies_collected.toLocaleString()} />
            <StatCard label="已评分公司" value={data.companies_scored.toLocaleString()} />
            <StatCard label="联系人总数" value={data.contacts_total.toLocaleString()} />
            <StatCard label="草稿数" value={data.emails_drafted.toLocaleString()} />
            <StatCard label="已发送" value={data.emails_sent.toLocaleString()} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
