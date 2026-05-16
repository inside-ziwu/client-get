'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, RatingTag } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader, SearchBar } from '@/components/pages/page-kit';

export default function CuratedCustomersPage() {
  const [keyword, setKeyword] = useState('');
  const prospectsQuery = useQuery({
    queryKey: ['tenant', 'prospects', keyword],
    queryFn: async () => (await tenantApi.prospects.list({ keyword, limit: 50 })).data.data,
  });

  return (
    <div className="tenant-page">
      <PageHeader title="优选客户" description="查看已筛选出的重点客户" />
      <SearchBar value={keyword} onChange={setKeyword} placeholder="客户名、国家、评级" />
      <DataTable
        rows={prospectsQuery.data}
        columns={[
          { key: 'name', title: '客户', render: (row) => <span className="font-medium">{row.name}</span> },
          { key: 'country', title: '国家', render: (row) => row.country ?? '-' },
          { key: 'grade', title: '评级', render: (row) => (row.grade ? <RatingTag grade={row.grade} /> : '-') },
          { key: 'score', title: '分数', render: (row) => row.total_score ?? '-' },
          { key: 'status', title: '状态', render: (row) => row.business_status ?? row.data_status ?? '-' },
          { key: 'action', title: '操作', render: () => <Button size="sm" variant="outline">查看</Button> },
        ]}
      />
    </div>
  );
}
