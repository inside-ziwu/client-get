'use client';

import { useQuery } from '@tanstack/react-query';
import { Bot, Building2, Mail, Send } from 'lucide-react';
import { Badge, Card, CardContent, CardHeader, CardTitle, Progress, StatCard } from '@shared/ui';
import { tenantApi } from '@/lib/api';

export default function DashboardPage() {
  const overviewQuery = useQuery({
    queryKey: ['tenant', 'dashboard', 'overview'],
    queryFn: async () => (await tenantApi.dashboard.overview()).data.data,
  });
  const funnelQuery = useQuery({
    queryKey: ['tenant', 'dashboard', 'funnel'],
    queryFn: async () => (await tenantApi.dashboard.funnel()).data.data,
  });
  const aiQuery = useQuery({
    queryKey: ['tenant', 'dashboard', 'ai-capabilities'],
    queryFn: async () => (await tenantApi.dashboard.aiCapabilities()).data.data,
  });
  const overview = overviewQuery.data;
  const funnel = funnelQuery.data;
  const maxStage = Math.max(...(funnel?.stages ?? []).map((stage) => stage.count), 1);

  return (
    <div className="tenant-page">
      <div className="tenant-page-header">
        <div>
          <h1 className="tenant-page-title">仪表盘</h1>
          <p className="tenant-page-description">客户、计划、邮件和 AI 能力概览</p>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="公司总数" value={overview?.total_companies ?? '-'} helper="已入库客户" icon={<Building2 className="h-4 w-4" />} />
        <StatCard label="优选客户" value={overview?.total_prospects ?? overview?.scored_companies ?? '-'} helper="已评分或已筛选" icon={<Building2 className="h-4 w-4" />} />
        <StatCard label="活跃计划" value={overview?.active_plans ?? overview?.running_plans ?? '-'} helper="正在执行" icon={<Send className="h-4 w-4" />} />
        <StatCard label="本月发送" value={overview?.emails_sent_this_month ?? '-'} helper={`回复率 ${overview?.reply_rate ?? 0}%`} icon={<Mail className="h-4 w-4" />} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>客户漏斗</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {(funnel?.stages ?? []).map((stage) => (
              <div key={stage.status} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>{stage.status}</span>
                  <span className="font-medium">{stage.count}</span>
                </div>
                <Progress value={(stage.count / maxStage) * 100} />
              </div>
            ))}
            {!funnel?.stages?.length ? <div className="text-sm text-muted-foreground">暂无漏斗数据</div> : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-4 w-4" />
              AI 能力状态
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-md border border-border p-3">
              <span className="text-sm">OpenRouter</span>
              <Badge variant={aiQuery.data?.provider.is_configured ? 'default' : 'secondary'}>
                {aiQuery.data?.provider.is_configured ? '已配置' : '未配置'}
              </Badge>
            </div>
            {(aiQuery.data?.features ?? []).map((feature) => (
              <div key={feature.feature} className="flex items-center justify-between rounded-md border border-border p-3">
                <span className="text-sm">{feature.feature}</span>
                <Badge variant={feature.available ? 'default' : 'secondary'}>{feature.available ? '可用' : '不可用'}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
