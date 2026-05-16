'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Badge } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function IntelligencePage() {
  const queryClient = useQueryClient();
  const articlesQuery = useQuery({
    queryKey: ['tenant', 'intelligence'],
    queryFn: async () => (await tenantApi.intelligence.list({ limit: 50 })).data.data,
  });
  const markReadMutation = useMutation({
    mutationFn: async (id: string) => tenantApi.intelligence.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tenant', 'intelligence'] }),
  });

  return (
    <div className="tenant-page">
      <PageHeader title="情报中心" description="行业资讯、订阅和 AI 摘要" />
      <DataTable
        rows={articlesQuery.data}
        columns={[
          { key: 'title', title: '标题', render: (row) => <div className="max-w-xl"><div className="font-medium">{row.title}</div><div className="line-clamp-2 text-xs text-muted-foreground">{row.content_summary}</div></div> },
          { key: 'category', title: '分类', render: (row) => row.ai_category ? <Badge variant="secondary">{row.ai_category}</Badge> : '-' },
          { key: 'score', title: '相关度', render: (row) => row.ai_relevance_score ?? '-' },
          { key: 'published', title: '发布时间', render: (row) => row.published_at?.slice(0, 10) ?? '-' },
          { key: 'action', title: '操作', render: (row) => <Button size="sm" variant="outline" onClick={() => markReadMutation.mutate(row.article_id)}>标记已读</Button> },
        ]}
      />
    </div>
  );
}
