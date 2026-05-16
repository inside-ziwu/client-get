'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { Badge, Button, Card, CardContent, Input, Label, Textarea } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function TemplatesPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const templatesQuery = useQuery({
    queryKey: ['tenant', 'templates'],
    queryFn: async () => (await tenantApi.emailTemplates.list()).data.data,
  });
  const createMutation = useMutation({
    mutationFn: async () =>
      (await tenantApi.emailTemplates.create({ name, subject, body_html: body, source_type: 'custom', variables: [] })).data.data,
    onSuccess: async () => {
      toast.success('模板已创建');
      setName('');
      setSubject('');
      setBody('');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'templates'] });
    },
    onError: () => toast.error('创建失败'),
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate();
  };

  return (
    <div className="tenant-page">
      <PageHeader title="邮件模板" description="创建、预览和复用邮件内容" />
      <Card>
        <CardContent className="p-5">
          <form className="grid gap-3 lg:grid-cols-[1fr_1fr_auto]" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="template-name">名称</Label>
              <Input id="template-name" value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="template-subject">主题</Label>
              <Input id="template-subject" value={subject} onChange={(event) => setSubject(event.target.value)} required />
            </div>
            <div className="flex items-end">
              <Button type="submit" disabled={createMutation.isPending}>新增模板</Button>
            </div>
            <div className="space-y-2 lg:col-span-3">
              <Label htmlFor="template-body">正文 HTML</Label>
              <Textarea id="template-body" value={body} onChange={(event) => setBody(event.target.value)} required />
            </div>
          </form>
        </CardContent>
      </Card>
      <DataTable
        rows={templatesQuery.data}
        columns={[
          { key: 'name', title: '名称', render: (row) => <span className="font-medium">{row.name}</span> },
          { key: 'subject', title: '主题', render: (row) => row.subject },
          { key: 'source', title: '来源', render: (row) => <Badge variant="secondary">{row.source_type}</Badge> },
          { key: 'updated', title: '更新时间', render: (row) => row.updated_at?.slice(0, 10) ?? '-' },
        ]}
      />
    </div>
  );
}
