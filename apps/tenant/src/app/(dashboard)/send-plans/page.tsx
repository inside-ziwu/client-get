'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Button, Progress, StatusTag } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function SendPlansPage() {
  const plansQuery = useQuery({
    queryKey: ['tenant', 'send-plans'],
    queryFn: async () => (await tenantApi.sendingPlans.list({ limit: 50 })).data.data,
  });

  return (
    <div className="tenant-page">
      <PageHeader title="发送计划" description="管理邮件触达计划" action={<Button asChild><Link href="/send-plans/new">新建计划</Link></Button>} />
      <DataTable
        rows={plansQuery.data}
        columns={[
          { key: 'name', title: '计划', render: (row) => <Link className="font-medium text-primary" href={`/send-plans/${row.id}`}>{row.name}</Link> },
          { key: 'status', title: '状态', render: (row) => <StatusTag status={row.status as never} /> },
          { key: 'recipients', title: '收件人', render: (row) => row.total_recipients ?? '-' },
          { key: 'progress', title: '进度', render: (row) => <div className="min-w-32"><Progress value={row.total_recipients ? ((row.sent_count ?? 0) / row.total_recipients) * 100 : 0} /></div> },
          { key: 'created', title: '创建时间', render: (row) => row.created_at?.slice(0, 10) ?? '-' },
        ]}
      />
    </div>
  );
}
