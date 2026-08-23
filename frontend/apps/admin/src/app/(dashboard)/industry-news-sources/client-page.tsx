'use client';

import type { IndustryNewsSource } from '@shared/types';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  Button,
  DataTable,
  type DataTableColumn,
  ListPage,
} from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const LANG_LABELS: Record<string, string> = {
  en: '英文',
  'zh-CN': '简体中文',
  'zh-TW': '繁体中文',
};

function langLabel(lang: string) {
  return LANG_LABELS[lang] ?? lang;
}

const STRATEGY_STATUS_MAP: Record<string, { label: string; tone: 'neutral' }> = {
  rss: { label: 'RSS', tone: 'neutral' },
  html: { label: 'HTML', tone: 'neutral' },
  jsonld: { label: 'JSON-LD', tone: 'neutral' },
};

export function IndustryNewsSourcesPage() {
  const queryClient = useQueryClient();
  const [updatingIds, setUpdatingIds] = useState<ReadonlySet<string>>(() => new Set());

  const query = useQuery({
    queryKey: ['admin', 'industry-news-sources'],
    queryFn: async () => (await adminApi.industryNewsSources.list()).data,
  });

  const invalidateList = () => queryClient.invalidateQueries({ queryKey: ['admin', 'industry-news-sources'] });

  // 「立即抓取」触发本实例一轮抓取（后台执行，不在请求内等待）；触发后 30 秒刷新一次列表
  const fetchMutation = useMutation({
    mutationFn: async () => (await adminApi.industryNewsSources.fetch()).data.data,
    onSuccess: (result) => {
      if (result.triggered) {
        toast.success('已开始抓取，稍后刷新查看');
        setTimeout(() => void invalidateList(), 30_000);
      } else if (result.reason === 'in_progress') {
        toast.info('一轮抓取正在进行');
      } else {
        toast.info('本实例没有可抓取的源');
      }
    },
    onError: () => toast.error('触发抓取失败，请稍后重试'),
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminApi.industryNewsSources.toggle(id, is_active),
    onMutate: ({ id }) => {
      setUpdatingIds((current) => new Set(current).add(id));
    },
    onSuccess: () => {
      toast.success('状态已更新');
      void invalidateList();
    },
    onError: () => toast.error('状态更新失败'),
    onSettled: (_data, _error, { id }) => {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    },
  });

  const columns: ReadonlyArray<DataTableColumn<IndustryNewsSource>> = [
    {
      id: 'name',
      header: '名称',
      width: 'medium',
      type: 'text',
      value: 'name',
      render: (item) => <span className="font-medium">{item.name}</span>,
    },
    { id: 'url', header: '地址', width: 'large', type: 'text', value: 'url' },
    { id: 'category', header: '类别', width: 'medium', type: 'text', value: 'category' },
    {
      id: 'lang',
      header: '语种',
      width: 'small',
      type: 'text',
      value: 'lang',
      format: (value) => langLabel(value as string),
    },
    {
      id: 'strategy',
      header: '策略',
      width: 'small',
      type: 'status',
      value: 'strategy',
      statusMap: STRATEGY_STATUS_MAP,
    },
    {
      id: 'active',
      header: '启用',
      width: 'small',
      type: 'boolean',
      value: 'is_active',
      booleanMode: 'interactive',
      getBooleanLabel: (item) => `${item.name}${item.is_active ? '已启用' : '已停用'}`,
      onBooleanChange: (item, checked) => toggleMutation.mutate({ id: item.id, is_active: checked }),
      isBooleanDisabled: (item) => updatingIds.has(item.id),
    },
    {
      id: 'lastSuccessAt',
      header: '上次成功',
      width: 'medium',
      type: 'date',
      value: 'last_success_at',
      format: (value) => (value ? formatDateTime(String(value)) : '从未'),
    },
    {
      id: 'errorCount',
      header: '错误计数',
      width: 'small',
      type: 'number',
      value: 'error_count',
      render: (item) =>
        item.error_count > 0 ? (
          <span className="text-ui-danger-foreground">{item.error_count}</span>
        ) : (
          <span>{item.error_count}</span>
        ),
    },
  ];

  const items = query.data?.data ?? [];
  // 本实例没有任何动态源时（如 Instance B）用说明块替换表格（TableState 空态文案不可定制）
  const noSources = !query.isLoading && !query.isError && items.length === 0;

  const tableState = query.isLoading
    ? { kind: 'loading' as const }
    : query.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void query.refetch() }
      : undefined;

  return (
    <ListPage
      className="admin-page"
      title="动态源管理"
      description="动态源由开发随种子维护；本页只读展示，支持启停与立即抓取"
      primaryAction={(
        <Button
          variant="outline"
          disabled={fetchMutation.isPending}
          onClick={() => fetchMutation.mutate()}
        >
          {fetchMutation.isPending ? '触发中…' : '立即抓取'}
        </Button>
      )}
    >
      {noSources ? (
        <div className="rounded-ui-md border border-ui-border bg-ui-surface-soft px-ui-md py-ui-sm text-ui-body text-ui-muted-foreground">
          本实例尚未配置动态源（由开发随种子导入）
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={items}
          entityName="动态源"
          getRowId={(item) => item.id}
          state={tableState}
          isRefreshing={query.isFetching && !query.isLoading}
        />
      )}
    </ListPage>
  );
}
