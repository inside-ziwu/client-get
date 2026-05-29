'use client';

import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  Button,
  Card,
  CardContent,
  DescriptionList,
  StatusTag,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@shared/ui';
import type { SendingPlanStatus } from '@shared/types';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

const CONDITION_LABELS: Record<string, string> = {
  always: '始终发送',
  no_reply: '未回复',
  opened: '已打开',
  clicked: '已点击',
};

const ENROLLMENT_STATUS_LABELS: Record<string, string> = {
  active: '进行中',
  paused: '已暂停',
  cancelled: '已取消',
  completed: '已完成',
};

const EMAIL_STATUS_LABELS: Record<string, string> = {
  sent: '已发送',
  delivered: '已送达',
  opened: '已打开',
  clicked: '已点击',
  replied: '已回复',
  bounced: '已退信',
  unsubscribed: '已退订',
};

type ActionDef = { label: string; action: 'start' | 'pause' | 'resume' | 'cancel'; variant: 'default' | 'outline' | 'destructive' };

const ACTION_MAP: Record<string, ActionDef[]> = {
  draft: [{ label: '开始发送', action: 'start', variant: 'default' }],
  scheduled: [
    { label: '立即开始', action: 'start', variant: 'default' },
    { label: '取消计划', action: 'cancel', variant: 'destructive' },
  ],
  running: [
    { label: '暂停', action: 'pause', variant: 'outline' },
    { label: '取消', action: 'cancel', variant: 'destructive' },
  ],
  paused: [
    { label: '恢复', action: 'resume', variant: 'default' },
    { label: '取消', action: 'cancel', variant: 'destructive' },
  ],
  completed: [],
  cancelled: [],
};

export default function SendPlanDetailPage() {
  const params = useParams<{ id: string }>();
  const planId = params.id;
  const queryClient = useQueryClient();
  const [cancelOpen, setCancelOpen] = useState(false);

  const planQuery = useQuery({
    queryKey: ['tenant', 'sendingPlans', planId],
    queryFn: async () => (await tenantApi.sendingPlans.detail(planId)).data.data,
  });

  const stepsQuery = useQuery({
    queryKey: ['tenant', 'sendingPlans', planId, 'steps'],
    queryFn: async () => (await tenantApi.sendingPlans.listSteps(planId)).data.data,
  });

  const recipientsQuery = useQuery({
    queryKey: ['tenant', 'sendingPlans', planId, 'recipients'],
    queryFn: async () => (await tenantApi.sendingPlans.listRecipients(planId)).data.data,
  });

  const emailsQuery = useQuery({
    queryKey: ['tenant', 'emails', { plan_id: planId }],
    queryFn: async () => (await tenantApi.emails.list({ plan_id: planId })).data.data,
  });

  const plan = planQuery.data;
  const steps = stepsQuery.data ?? [];
  const emails = emailsQuery.data ?? [];

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans', planId] });
    queryClient.invalidateQueries({ queryKey: ['tenant', 'emails', { plan_id: planId }] });
  };

  const executeMutation = useMutation({
    mutationFn: async (action: 'start' | 'pause' | 'resume' | 'cancel') => {
      const api = tenantApi.sendingPlans;
      const fn = { start: api.start, pause: api.pause, resume: api.resume, cancel: api.cancel }[action];
      return (await fn(planId)).data.data;
    },
    onSuccess: (_, action) => {
      const labels: Record<string, string> = { start: '已开始', pause: '已暂停', resume: '已恢复', cancel: '已取消' };
      toast.success(labels[action]);
      invalidateAll();
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      toast.error(axiosErr.response?.data?.message || '操作失败');
    },
  });

  const handleAction = (action: ActionDef['action']) => {
    if (action === 'cancel') {
      setCancelOpen(true);
    } else {
      executeMutation.mutate(action);
    }
  };

  const actions = plan ? ACTION_MAP[plan.status] ?? [] : [];

  return (
    <div className="tenant-page space-y-6">
      <PageHeader
        title={plan?.name ?? '发送计划详情'}
        description="计划配置、收件人和执行监控"
        action={
          actions.length > 0 ? (
            <div className="flex gap-2">
              {plan && <StatusTag status={plan.status as SendingPlanStatus} />}
              {actions.map((a) => (
                <Button
                  key={a.action}
                  variant={a.variant}
                  size="sm"
                  onClick={() => handleAction(a.action)}
                  disabled={executeMutation.isPending}
                >
                  {a.label}
                </Button>
              ))}
            </div>
          ) : plan ? (
            <StatusTag status={plan.status as SendingPlanStatus} />
          ) : undefined
        }
      />

      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">计划信息</TabsTrigger>
          <TabsTrigger value="steps">发送步骤</TabsTrigger>
          <TabsTrigger value="recipients">收件人</TabsTrigger>
          <TabsTrigger value="logs">发送日志</TabsTrigger>
        </TabsList>

        <TabsContent value="info">
          {plan && (
            <Card>
              <CardContent className="pt-6">
                <DescriptionList
                  items={[
                    { label: '状态', value: <StatusTag status={plan.status as SendingPlanStatus} /> },
                    { label: '发件人名称', value: plan.sender_name },
                    { label: '发件邮箱', value: plan.sender_email },
                    { label: '收件人数', value: plan.total_recipients },
                    { label: '已发送', value: plan.sent_count },
                    { label: '创建时间', value: plan.created_at?.slice(0, 10) },
                    { label: '描述', value: plan.description },
                  ]}
                />
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="steps">
          <Card>
            <CardContent className="p-0">
              {stepsQuery.isLoading ? (
                <p className="p-4 text-sm text-muted-foreground">加载中...</p>
              ) : steps.length === 0 ? (
                <p className="p-4 text-sm text-muted-foreground">暂无步骤</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">#</TableHead>
                      <TableHead>模板名称</TableHead>
                      <TableHead>延迟</TableHead>
                      <TableHead>触发条件</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {steps.map((s) => (
                      <TableRow key={s.id}>
                        <TableCell>{s.step_order ?? s.step_number}</TableCell>
                        <TableCell>{s.template_name ?? '-'}</TableCell>
                        <TableCell>{s.delay_days === 0 ? '立即' : `${s.delay_days} 天`}</TableCell>
                        <TableCell>{CONDITION_LABELS[s.condition_type ?? ''] ?? s.condition_type ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recipients">
          <DataTable
            rows={recipientsQuery.data}
            columns={[
              { key: 'email', title: '邮箱', render: (row) => row.contact_email ?? '-' },
              { key: 'company', title: '公司', render: (row) => row.company_name ?? '-' },
              { key: 'status', title: '状态', render: (row) => ENROLLMENT_STATUS_LABELS[row.enrollment_status ?? ''] ?? row.enrollment_status ?? '-' },
              { key: 'step', title: '当前步骤', render: (row) => row.current_step ?? '-' },
            ]}
          />
        </TabsContent>

        <TabsContent value="logs">
          <DataTable
            rows={emails}
            columns={[
              { key: 'to', title: '收件人', render: (row) => (row.to_email as string) ?? '-' },
              { key: 'subject', title: '主题', render: (row) => (row.subject as string) ?? '-' },
              { key: 'status', title: '状态', render: (row) => { const s = row.status as string | undefined; return s ? (EMAIL_STATUS_LABELS[s] ?? s) : '-'; }},
              { key: 'sent_at', title: '发送时间', render: (row) => {
                const t = row.sent_at as string | undefined;
                return t ? t.slice(0, 16).replace('T', ' ') : '-';
              }},
            ]}
            emptyText={plan?.status === 'draft' ? '计划尚未开始发送' : '暂无发送记录'}
          />
        </TabsContent>
      </Tabs>

      <AlertDialog open={cancelOpen} onOpenChange={setCancelOpen}>
        <AlertDialogContent>
          <AlertDialogTitle>确定取消此发送计划？</AlertDialogTitle>
          <AlertDialogDescription>
            已发送的邮件不受影响。此操作不可撤销。
          </AlertDialogDescription>
          <div className="flex justify-end gap-2 pt-2">
            <AlertDialogCancel>返回</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={(e) => {
                e.preventDefault();
                executeMutation.mutate('cancel');
                setCancelOpen(false);
              }}
            >
              确定取消
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
