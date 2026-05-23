'use client';

import { useQuery } from '@tanstack/react-query';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';
import SendPlanWizard, { type WizardFormData } from '../send-plan-wizard';

export default function NewSendPlanPage() {
  const meQuery = useQuery({
    queryKey: ['tenant', 'auth', 'me'],
    queryFn: async () => (await tenantApi.auth.me()).data.data,
  });

  const domainsQuery = useQuery({
    queryKey: ['tenant', 'domains'],
    queryFn: async () => (await tenantApi.domains.list()).data.data,
  });

  if (meQuery.isLoading || domainsQuery.isLoading) {
    return (
      <div className="tenant-page">
        <PageHeader title="新建发送计划" description="加载中..." />
        <div className="flex items-center justify-center py-20 text-muted-foreground">加载中...</div>
      </div>
    );
  }

  const verifiedDomains = (domainsQuery.data ?? [])
    .filter((d) => d.verification_status === 'verified')
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

  const defaultDomain = verifiedDomains[0];

  const initialData: WizardFormData = {
    plan: {
      name: '',
      description: '',
      sender_name: meQuery.data?.tenant_name ?? '',
      sender_email: defaultDomain?.sender_email ?? '',
      domain_id: defaultDomain?.id ?? '',
      recipient_source: 'group',
      recipient_config: {},
    },
    steps: [
      {
        step_number: 1,
        template_id: '',
        delay_days: 0,
        condition_type: 'always',
        use_ai_personalization: false,
        ai_instructions: '',
      },
    ],
    lock_recipients: true,
  };

  return (
    <div className="tenant-page">
      <PageHeader title="新建发送计划" description="四步完成计划创建" />
      <SendPlanWizard mode="create" initialData={initialData} />
    </div>
  );
}
