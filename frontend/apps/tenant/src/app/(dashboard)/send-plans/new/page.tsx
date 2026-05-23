'use client';

import { PageHeader } from '@/components/pages/page-kit';
import SendPlanWizard from '../send-plan-wizard';

export default function NewSendPlanPage() {
  return (
    <div className="tenant-page">
      <PageHeader title="新建发送计划" description="四步完成计划创建" />
      <SendPlanWizard mode="create" />
    </div>
  );
}
