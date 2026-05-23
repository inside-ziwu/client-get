'use client';

import { useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  DescriptionList,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@shared/ui';
import type { EmailTemplate, Group } from '@shared/api';
import type { WizardFormData } from '../send-plan-wizard';

const CONDITION_LABELS: Record<string, string> = {
  always: '始终发送',
  no_reply: '未回复',
  opened: '已打开',
  clicked: '已点击',
};

interface Props {
  formData: WizardFormData;
}

export default function StepConfirmation({ formData }: Props) {
  const queryClient = useQueryClient();

  const templates = queryClient.getQueryData<EmailTemplate[]>(['tenant', 'emailTemplates']) ?? [];
  const groups = queryClient.getQueryData<Group[]>(['tenant', 'groups']) ?? [];

  const templateMap = new Map(templates.map((t) => [t.id, t.name]));
  const selectedGroup = groups.find((g) => g.id === formData.plan.recipient_config.group_id);

  return (
    <div className="max-w-2xl space-y-6">
      {/* 基本信息 */}
      <div>
        <h3 className="mb-3 text-sm font-medium">基本信息</h3>
        <DescriptionList
          items={[
            { label: '计划名称', value: formData.plan.name },
            { label: '发件人名称', value: formData.plan.sender_name },
            { label: '发件邮箱', value: formData.plan.sender_email },
            { label: '描述', value: formData.plan.description || '无' },
          ]}
        />
      </div>

      {/* 发送步骤 */}
      <div>
        <h3 className="mb-3 text-sm font-medium">发送步骤（{formData.steps.length} 步）</h3>
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">#</TableHead>
                  <TableHead>模板名称</TableHead>
                  <TableHead>延迟</TableHead>
                  <TableHead>触发条件</TableHead>
                  <TableHead>AI 个性化</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {formData.steps.map((step) => (
                  <TableRow key={step.step_number}>
                    <TableCell>{step.step_number}</TableCell>
                    <TableCell>{templateMap.get(step.template_id) ?? '-'}</TableCell>
                    <TableCell>{step.delay_days === 0 ? '立即' : `${step.delay_days} 天`}</TableCell>
                    <TableCell>{CONDITION_LABELS[step.condition_type] ?? step.condition_type}</TableCell>
                    <TableCell>{step.use_ai_personalization ? '是' : '否'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* 收件人 */}
      <div>
        <h3 className="mb-3 text-sm font-medium">收件人</h3>
        <DescriptionList
          items={[
            { label: '来源', value: `群组 — "${selectedGroup?.name ?? '-'}"` },
            { label: '锁定收件人', value: formData.lock_recipients ? '是' : '否' },
            { label: '预估收件人数', value: selectedGroup ? `${selectedGroup.member_count} 人` : '-' },
          ]}
        />
      </div>
    </div>
  );
}
