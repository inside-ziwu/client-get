'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { Button, Card, CardContent, Input, Label } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function KeywordsPage() {
  const queryClient = useQueryClient();
  const [keyword, setKeyword] = useState('');
  const keywordsQuery = useQuery({
    queryKey: ['tenant', 'keywords'],
    queryFn: async () => (await tenantApi.keywords.list()).data.data,
  });
  const createMutation = useMutation({
    mutationFn: async () => tenantApi.keywords.create({ keyword }),
    onSuccess: async () => {
      toast.success('关键词已创建');
      setKeyword('');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'keywords'] });
    },
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate();
  };

  return (
    <div className="tenant-page">
      <PageHeader title="关键词" description="管理采集和评分关键词" />
      <Card>
        <CardContent className="p-5">
          <form className="flex gap-2" onSubmit={onSubmit}>
            <div className="flex-1 space-y-2">
              <Label htmlFor="keyword">关键词</Label>
              <Input id="keyword" value={keyword} onChange={(event) => setKeyword(event.target.value)} required />
            </div>
            <div className="flex items-end">
              <Button type="submit">新增</Button>
            </div>
          </form>
        </CardContent>
      </Card>
      <DataTable
        rows={keywordsQuery.data}
        columns={[
          { key: 'keyword', title: '关键词', render: (row) => <span className="font-medium">{row.keyword}</span> },
          { key: 'countries', title: '国家', render: (row) => row.countries?.join(', ') || '-' },
          { key: 'sources', title: '来源', render: (row) => row.source_types?.join(', ') || '-' },
          { key: 'status', title: '状态', render: (row) => row.status ?? '-' },
          { key: 'created', title: '创建时间', render: (row) => row.created_at?.slice(0, 10) ?? '-' },
        ]}
      />
    </div>
  );
}
