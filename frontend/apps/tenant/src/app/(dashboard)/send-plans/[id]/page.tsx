'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { DescriptionList, StatusTag } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function SendPlanDetailPage() {
  const params = useParams<{ id: string }>();
  const planQuery = useQuery({
    queryKey: ['tenant', 'send-plan', params.id],
    queryFn: async () => (await tenantApi.sendingPlans.detail(params.id)).data.data,
  });
  const recipientsQuery = useQuery({
    queryKey: ['tenant', 'send-plan', params.id, 'recipients'],
    queryFn: async () => (await tenantApi.sendingPlans.listRecipients(params.id)).data.data,
  });
  const plan = planQuery.data;

  return (
    <div className="tenant-page">
      <PageHeader title={plan?.name ?? '发送计划详情'} description="计划配置、收件人和执行监控" />
      {plan ? (
        <DescriptionList
          items={[
            { label: '状态', value: <StatusTag status={plan.status as never} /> },
            { label: '发件人', value: plan.sender_email },
            { label: '收件人数', value: plan.total_recipients },
            { label: '已发送', value: plan.sent_count },
            { label: '创建时间', value: plan.created_at?.slice(0, 10) },
            { label: '描述', value: plan.description },
          ]}
        />
      ) : null}
      <DataTable
        title="收件人"
        rows={recipientsQuery.data}
        columns={[
          { key: 'company', title: '公司', render: (row) => row.company_name ?? '-' },
          { key: 'email', title: '邮箱', render: (row) => row.email ?? '-' },
          { key: 'status', title: '状态', render: (row) => row.enrollment_status ?? '-' },
          { key: 'step', title: '当前步骤', render: (row) => row.current_step ?? '-' },
        ]}
      />
    </div>
  );
}
