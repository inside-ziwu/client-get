'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';
import SendPlanWizard, { type WizardFormData } from '../../send-plan-wizard';

export default function EditSendPlanPage() {
  const params = useParams<{ id: string }>();
  const planId = params.id;

  const planQuery = useQuery({
    queryKey: ['tenant', 'sendingPlans', planId],
    queryFn: async () => (await tenantApi.sendingPlans.detail(planId)).data.data,
  });

  const stepsQuery = useQuery({
    queryKey: ['tenant', 'sendingPlans', planId, 'steps'],
    queryFn: async () => (await tenantApi.sendingPlans.listSteps(planId)).data.data,
  });

  if (planQuery.isLoading || stepsQuery.isLoading) {
    return (
      <div className="tenant-page">
        <PageHeader title="编辑发送计划" description="加载中..." />
        <div className="flex items-center justify-center py-20 text-muted-foreground">加载中...</div>
      </div>
    );
  }

  if (planQuery.isError || !planQuery.data) {
    return (
      <div className="tenant-page">
        <PageHeader title="编辑发送计划" description="" />
        <div className="py-20 text-center text-destructive">加载计划失败</div>
      </div>
    );
  }

  const plan = planQuery.data;
  const steps = stepsQuery.data ?? [];

  const initialData: WizardFormData = {
    plan: {
      name: plan.name ?? '',
      description: plan.description ?? '',
      sender_name: plan.sender_name ?? '',
      sender_email: plan.sender_email ?? '',
      domain_id: plan.domain_id ?? '',
      recipient_source: plan.recipient_source ?? 'group',
      recipient_config: (plan.recipient_config as Record<string, string>) ?? {},
    },
    steps: steps.length > 0
      ? steps.map((s) => ({
          step_number: s.step_number ?? s.step_order ?? 1,
          template_id: s.template_id,
          delay_days: s.delay_days,
          condition_type: s.condition_type ?? 'always',
          use_ai_personalization: false,
          ai_instructions: '',
        }))
      : [
          {
            step_number: 1,
            template_id: '',
            delay_days: 0,
            condition_type: 'always',
            use_ai_personalization: false,
            ai_instructions: '',
          },
        ],
    lock_recipients: false,
  };

  return (
    <div className="tenant-page">
      <PageHeader title="编辑发送计划" description="修改计划配置后保存" />
      <SendPlanWizard mode="edit" planId={planId} initialData={initialData} />
    </div>
  );
}
