'use client';

import { RefreshCw } from 'lucide-react';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Progress } from '@shared/ui';
import type { DailyQuotaResponse, LlmBalanceResponse } from '@shared/types';

interface QuotaBalanceProps {
  quota: { data: DailyQuotaResponse | undefined; isLoading: boolean; isError: boolean; refetch: () => void };
  balance: { data: LlmBalanceResponse | undefined; isLoading: boolean; isError: boolean; refetch: () => void };
}

function SkeletonBlock() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 w-24 rounded bg-muted" />
      <div className="h-6 w-32 rounded bg-muted" />
      <div className="h-2 w-full rounded bg-muted" />
    </div>
  );
}

function quotaColor(used: number, limit: number): string {
  if (limit === 0) return 'bg-muted';
  const ratio = used / limit;
  if (ratio > 0.95) return '[&>div]:bg-red-500';
  if (ratio > 0.8) return '[&>div]:bg-orange-500';
  return '';
}

function balanceStatusLabel(status: string): { label: string; variant: 'default' | 'secondary' | 'destructive' } {
  switch (status) {
    case 'available': return { label: '正常', variant: 'default' };
    case 'insufficient_balance': return { label: '余额不足', variant: 'destructive' };
    case 'invalid_api_key': return { label: 'Key 无效', variant: 'destructive' };
    default: return { label: '未知', variant: 'secondary' };
  }
}

export function QuotaBalance({ quota, balance }: QuotaBalanceProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* 每日发送配额 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">每日发送配额</CardTitle>
        </CardHeader>
        <CardContent>
          {quota.isLoading ? (
            <SkeletonBlock />
          ) : quota.isError ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              查询失败
              <Button variant="outline" size="sm" onClick={quota.refetch}>
                <RefreshCw className="mr-1 h-3 w-3" />
                重试
              </Button>
            </div>
          ) : !quota.data || quota.data.limit === 0 ? (
            <div className="text-sm text-muted-foreground">未配置域名</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-semibold">{quota.data.remaining.toLocaleString()}</span>
                <span className="text-sm text-muted-foreground">
                  {quota.data.used.toLocaleString()} / {quota.data.limit.toLocaleString()}
                </span>
              </div>
              <Progress
                value={(quota.data.used / quota.data.limit) * 100}
                className={quotaColor(quota.data.used, quota.data.limit)}
              />
              <p className="text-xs text-muted-foreground">剩余可发送量</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* LLM 余额 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">LLM 余额</CardTitle>
        </CardHeader>
        <CardContent>
          {balance.isLoading ? (
            <SkeletonBlock />
          ) : balance.isError ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              查询失败
              <Button variant="outline" size="sm" onClick={balance.refetch}>
                <RefreshCw className="mr-1 h-3 w-3" />
                重试
              </Button>
            </div>
          ) : !balance.data?.is_configured ? (
            <div className="text-sm text-muted-foreground">未配置 OpenRouter</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-semibold">
                  ${balance.data.balance_remaining?.toFixed(2) ?? '—'}
                </span>
                <Badge variant={balanceStatusLabel(balance.data.balance_status).variant}>
                  {balanceStatusLabel(balance.data.balance_status).label}
                </Badge>
              </div>
              {balance.data.usage !== null && balance.data.usage !== undefined && (
                <p className="text-xs text-muted-foreground">
                  已用 ${balance.data.usage.toFixed(2)}
                  {balance.data.limit ? ` / 限额 $${balance.data.limit.toFixed(2)}` : ''}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
