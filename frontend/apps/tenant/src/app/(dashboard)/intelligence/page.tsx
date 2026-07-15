'use client';

import type { DataTableColumn } from '@shared/ui';
import { Badge, Button, DataTable, ListPage } from '@shared/ui';
import type { IntelligenceArticle } from '@shared/api';
import { queryKeys } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

export default function IntelligencePage() {
  const queryClient = useQueryClient();
  const articlesQuery = useQuery({
    queryKey: queryKeys.intelligence.list({ limit: 50 }),
    queryFn: async () => (await tenantApi.intelligence.list({ limit: 50 })).data.data,
  });
  const markReadMutation = useMutation({
    mutationFn: async (id: string) => tenantApi.intelligence.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.intelligence.all() }),
  });

  const columns: DataTableColumn<IntelligenceArticle>[] = [
    {
      id: 'title',
      header: '标题',
      width: 'large',
      type: 'text',
      value: 'title',
      render: (row) => (
        <div className="min-w-0">
          <div className="truncate text-ui-body-strong">{row.title}</div>
          <div className="line-clamp-2 text-ui-caption text-ui-muted-foreground">{row.content_summary || '-'}</div>
        </div>
      ),
    },
    {
      id: 'category',
      header: '分类',
      width: 'small',
      align: 'center',
      type: 'text',
      value: 'ai_category',
      render: (row) => row.ai_category ? <Badge variant="secondary">{row.ai_category}</Badge> : '-',
    },
    {
      id: 'score',
      header: '相关度',
      width: 'small',
      align: 'center',
      type: 'number',
      value: 'ai_relevance_score',
    },
    {
      id: 'published',
      header: '发布时间',
      width: 'medium',
      align: 'center',
      type: 'date',
      value: 'published_at',
      format: (value) => formatDateTime(value as string | undefined, 'YYYY-MM-DD'),
    },
    {
      id: 'actions',
      header: '操作',
      width: 'medium',
      align: 'center',
      type: 'actions',
      render: (row) => (
        <div className="flex items-center justify-center">
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            disabled={markReadMutation.isPending && markReadMutation.variables === row.article_id}
            onClick={() => markReadMutation.mutate(row.article_id)}
          >
            标记已读
          </Button>
        </div>
      ),
    },
  ];

  const articles = articlesQuery.data ?? [];
  const tableState = articlesQuery.isLoading
    ? { kind: 'loading' as const }
    : articlesQuery.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void articlesQuery.refetch() }
      : articles.length === 0
        ? { kind: 'empty' as const }
        : undefined;

  return (
    <ListPage
      className="tenant-page"
      title="情报中心"
      description="行业资讯、订阅和 AI 摘要"
    >
      <DataTable
        columns={columns}
        data={articles}
        entityName="情报"
        getRowId={(row) => row.article_id}
        isRefreshing={articlesQuery.isFetching && !articlesQuery.isLoading}
        state={tableState}
      />
    </ListPage>
  );
}
