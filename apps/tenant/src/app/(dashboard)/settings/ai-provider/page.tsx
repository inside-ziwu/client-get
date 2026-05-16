'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { Badge, Button, Card, CardContent, Input, Label, StatCard } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';

export default function AiProviderPage() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState('');
  const providerQuery = useQuery({
    queryKey: ['tenant', 'ai-provider'],
    queryFn: async () => (await tenantApi.aiProvider.getOpenRouter()).data.data,
  });
  const summaryQuery = useQuery({
    queryKey: ['tenant', 'ai-usage-summary'],
    queryFn: async () => (await tenantApi.aiProvider.usageSummary('30d')).data.data,
  });
  const updateMutation = useMutation({
    mutationFn: async () => tenantApi.aiProvider.updateOpenRouter({ api_key: apiKey }),
    onSuccess: async () => {
      toast.success('OpenRouter 已更新');
      setApiKey('');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'ai-provider'] });
    },
  });
  const refreshMutation = useMutation({
    mutationFn: async () => tenantApi.aiProvider.refreshOpenRouterBalance(),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['tenant', 'ai-provider'] }),
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateMutation.mutate();
  };

  return (
    <div className="tenant-page">
      <PageHeader title="AI 提供商" description="配置 OpenRouter 和查看用量" />
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="配置状态" value={providerQuery.data?.is_configured ? '已配置' : '未配置'} helper={providerQuery.data?.secret_masked} />
        <StatCard label="余额状态" value={providerQuery.data?.balance.status ?? '-'} helper={providerQuery.data?.balance.message} />
        <StatCard label="30 天成本" value={summaryQuery.data?.total_cost ?? '-'} helper="OpenRouter 用量" />
      </div>
      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex items-center justify-between">
            <Badge variant={providerQuery.data?.is_configured ? 'default' : 'secondary'}>
              {providerQuery.data?.is_configured ? 'OpenRouter 已启用' : 'OpenRouter 未启用'}
            </Badge>
            <Button variant="outline" onClick={() => refreshMutation.mutate()}>刷新余额</Button>
          </div>
          <form className="flex gap-2" onSubmit={onSubmit}>
            <div className="flex-1 space-y-2">
              <Label htmlFor="api-key">API Key</Label>
              <Input id="api-key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} type="password" />
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={!apiKey || updateMutation.isPending}>保存</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
