'use client';

import { useQuery } from '@tanstack/react-query';
import { MailCheck, MousePointerClick, Reply, Send } from 'lucide-react';
import { StatCard } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function EmailMonitorPage() {
  const statsQuery = useQuery({
    queryKey: ['tenant', 'emails', 'stats'],
    queryFn: async () => (await tenantApi.emails.stats()).data.data,
  });
  const trendQuery = useQuery({
    queryKey: ['tenant', 'emails', 'trend'],
    queryFn: async () => (await tenantApi.emails.trend()).data.data,
  });
  const stats = statsQuery.data;

  return (
    <div className="tenant-page">
      <PageHeader title="邮件监控" description="跟踪发送、打开、点击和回复表现" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="发送" value={stats?.sent ?? stats?.total_sent ?? '-'} icon={<Send className="h-4 w-4" />} />
        <StatCard label="打开率" value={`${stats?.open_rate ?? 0}%`} icon={<MailCheck className="h-4 w-4" />} />
        <StatCard label="点击率" value={`${stats?.click_rate ?? 0}%`} icon={<MousePointerClick className="h-4 w-4" />} />
        <StatCard label="回复率" value={`${stats?.reply_rate ?? 0}%`} icon={<Reply className="h-4 w-4" />} />
      </div>
      <DataTable
        title="趋势"
        rows={trendQuery.data}
        columns={[
          { key: 'date', title: '日期', render: (row) => row.date },
          { key: 'sent', title: '发送', render: (row) => row.sent ?? row.total ?? '-' },
          { key: 'opened', title: '打开', render: (row) => row.opened ?? '-' },
          { key: 'clicked', title: '点击', render: (row) => row.clicked ?? '-' },
          { key: 'replied', title: '回复', render: (row) => row.replied ?? '-' },
        ]}
      />
    </div>
  );
}
