'use client';

import { BarChart3, Eye, RefreshCw } from 'lucide-react';
import { Button, StatCard } from '@shared/ui';
import type { EmailStatsSummary } from '@shared/types';

interface StatsSectionProps {
  data: EmailStatsSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg border bg-card p-4">
      <div className="h-3 w-16 rounded bg-muted" />
      <div className="mt-3 h-7 w-20 rounded bg-muted" />
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="col-span-full flex items-center justify-center gap-2 rounded-lg border border-dashed p-8 text-sm text-muted-foreground">
      加载失败
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="mr-1 h-3 w-3" />
        重试
      </Button>
    </div>
  );
}

function fmt(n: number | undefined): string {
  if (n === undefined) return '0';
  return n.toLocaleString();
}

function pct(n: number | undefined): string {
  if (n === undefined) return '0%';
  return `${n}%`;
}

export function StatsSection({ data, isLoading, isError, refetch }: StatsSectionProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <ErrorState onRetry={refetch} />
      </div>
    );
  }

  const sendStats = [
    { label: '目标数', value: fmt(data?.targets), color: 'text-blue-600' },
    { label: '已发送', value: fmt(data?.sent), color: 'text-blue-600' },
    { label: '已送达', value: `${fmt(data?.delivered)} (${pct(data?.delivered_percent)})`, color: 'text-green-600' },
    { label: '无效邮箱', value: fmt(data?.invalid_email), color: 'text-orange-500' },
    { label: '软退信', value: fmt(data?.soft_bounce), color: 'text-purple-600' },
    { label: '计费数', value: fmt(data?.billing), color: 'text-blue-600' },
  ];

  const trackStats = [
    { label: '打开次数', value: fmt(data?.total_opens), color: 'text-blue-600' },
    { label: '打开次数率', value: pct(data?.total_open_percent), color: 'text-green-600' },
    { label: '独立打开数', value: fmt(data?.opens), color: 'text-blue-600' },
    { label: '独立打开率', value: pct(data?.open_percent), color: 'text-green-600' },
    { label: '举报垃圾邮件', value: fmt(data?.report_spam), color: 'text-red-600' },
    { label: '退订', value: fmt(data?.unsubscribe), color: 'text-red-600' },
  ];

  return (
    <div className="space-y-6">
      {/* 发送统计 */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <BarChart3 className="h-4 w-4" />
          发送统计
        </h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {sendStats.map((s) => (
            <StatCard
              key={s.label}
              label={s.label}
              value={<span className={s.color}>{s.value}</span>}
            />
          ))}
        </div>
      </div>

      {/* 追踪统计 */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Eye className="h-4 w-4" />
          追踪统计
        </h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {trackStats.map((s) => (
            <StatCard
              key={s.label}
              label={s.label}
              value={<span className={s.color}>{s.value}</span>}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
