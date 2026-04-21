import { useParams, useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ArrowLeftOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import type { SendingPlan, SendingPlanRecipient, SendingPlanStep } from '@shared/api';
import { StatusTag } from '@shared/ui';
import { tenantApi } from '../../lib/api';

const { Text, Title } = Typography;

type PreviewRecipient = Record<string, unknown>;
type SampleEmail = Record<string, unknown>;

function formatDate(value?: string | null) {
  if (!value) {
    return '—';
  }
  return new Date(value).toLocaleString('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function Component() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [detailQuery, stepsQuery, recipientsQuery, previewQuery, samplesQuery] = useQueries({
    queries: [
      {
        queryKey: ['tenant', 'sendingPlans', 'detail', id],
        queryFn: async () => {
          if (!id) return null;
          return (await tenantApi.sendingPlans.detail(id)).data.data as SendingPlan;
        },
        enabled: Boolean(id),
      },
      {
        queryKey: ['tenant', 'sendingPlans', 'steps', id],
        queryFn: async () => {
          if (!id) return [] as SendingPlanStep[];
          return (await tenantApi.sendingPlans.listSteps(id)).data.data as SendingPlanStep[];
        },
        enabled: Boolean(id),
      },
      {
        queryKey: ['tenant', 'sendingPlans', 'recipients', id],
        queryFn: async () => {
          if (!id) return [] as SendingPlanRecipient[];
          return (await tenantApi.sendingPlans.listRecipients(id)).data.data as SendingPlanRecipient[];
        },
        enabled: Boolean(id),
      },
      {
        queryKey: ['tenant', 'sendingPlans', 'preview', id],
        queryFn: async () => {
          if (!id) return null;
          return (await tenantApi.sendingPlans.preview(id)).data.data as Record<string, unknown>;
        },
        enabled: Boolean(id),
      },
      {
        queryKey: ['tenant', 'sendingPlans', 'samples', id],
        queryFn: async () => {
          if (!id) return [] as SampleEmail[];
          return (await tenantApi.sendingPlans.sampleEmails(id)).data.data as SampleEmail[];
        },
        enabled: Boolean(id),
      },
    ],
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans', 'detail', id] }),
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans', 'steps', id] }),
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans', 'recipients', id] }),
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans', 'preview', id] }),
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans', 'samples', id] }),
      queryClient.invalidateQueries({ queryKey: ['tenant', 'unknown', 'sendingPlans'] }),
    ]);
  };

  const planActionMutation = useMutation({
    mutationFn: async (action: 'start' | 'pause' | 'resume' | 'cancel' | 'lock') => {
      if (!id) {
        throw new Error('missing id');
      }
      if (action === 'start') return tenantApi.sendingPlans.start(id);
      if (action === 'pause') return tenantApi.sendingPlans.pause(id);
      if (action === 'resume') return tenantApi.sendingPlans.resume(id);
      if (action === 'cancel') return tenantApi.sendingPlans.cancel(id);
      return tenantApi.sendingPlans.lockRecipients(id);
    },
    onSuccess: async (_, action) => {
      message.success(
        action === 'lock'
          ? '收件人已锁定'
          : action === 'start'
            ? '发送计划已启动'
            : action === 'pause'
              ? '发送计划已暂停'
              : action === 'resume'
                ? '发送计划已恢复'
                : '发送计划已取消',
      );
      await refresh();
    },
    onError: () => message.error('计划操作失败'),
  });

  const plan = detailQuery.data;
  const steps = stepsQuery.data ?? [];
  const recipients = recipientsQuery.data ?? [];
  const preview = previewQuery.data;
  const previewRecipients = Array.isArray(preview?.recipients_preview)
    ? (preview.recipients_preview as PreviewRecipient[])
    : [];
  const eligibleRecipients = typeof preview?.eligible_recipients === 'number' ? preview.eligible_recipients : 0;
  const samples = samplesQuery.data ?? [];

  const stepColumns: ColumnsType<SendingPlanStep> = [
    {
      title: '序列',
      dataIndex: 'step_number',
      width: 90,
      render: (value) => <Tag color="blue">第 {value ?? 0} 封</Tag>,
    },
    {
      title: '模板 ID',
      dataIndex: 'template_id',
      render: (value) => <Text code>{value}</Text>,
    },
    {
      title: '触发条件',
      dataIndex: 'condition_type',
      width: 160,
      render: (value) => value ?? 'always',
    },
    {
      title: '延迟天数',
      dataIndex: 'delay_days',
      width: 100,
      render: (value) => value ?? 0,
    },
  ];

  const recipientColumns: ColumnsType<SendingPlanRecipient> = [
    {
      title: '公司',
      dataIndex: 'company_name',
      render: (value) => value ?? '—',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      render: (value) => value ?? '—',
    },
    {
      title: '状态',
      dataIndex: 'enrollment_status',
      width: 140,
      render: (value) => value ?? '—',
    },
    {
      title: '当前序列',
      dataIndex: 'current_step',
      width: 100,
      render: (value) => value ?? 0,
    },
  ];

  const previewColumns: ColumnsType<PreviewRecipient> = [
    {
      title: '公司',
      render: (_, record) => String(record.company_name ?? '—'),
    },
    {
      title: '联系人',
      render: (_, record) => String(record.contact_name ?? '—'),
    },
    {
      title: '邮箱',
      render: (_, record) => String(record.contact_email ?? '—'),
    },
    {
      title: '排除原因',
      render: (_, record) => String(record.excluded_reason ?? '可发送'),
    },
  ];

  const sampleColumns: ColumnsType<SampleEmail> = [
    {
      title: '联系人',
      render: (_, record) => String(record.tenant_contact_id ?? '—'),
      width: 180,
    },
    {
      title: '主题',
      render: (_, record) => String(record.subject ?? '—'),
    },
    {
      title: '正文预览',
      render: (_, record) => (
        <Text type="secondary">
          {String(record.body_text ?? '—').slice(0, 120)}
        </Text>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/send-plans')}>
            返回列表
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            {plan?.name ?? '发送计划详情'}
          </Title>
          {plan && <StatusTag status={plan.status as never} />}
        </Space>
        {plan && (
          <Space>
            {plan.status === 'draft' && (
              <>
                <Button onClick={() => planActionMutation.mutate('lock')}>
                  锁定收件人
                </Button>
                <Button type="primary" onClick={() => planActionMutation.mutate('start')}>
                  启动
                </Button>
              </>
            )}
            {plan.status === 'running' && (
              <Button icon={<PauseCircleOutlined />} onClick={() => planActionMutation.mutate('pause')}>
                暂停
              </Button>
            )}
            {plan.status === 'paused' && (
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => planActionMutation.mutate('resume')}>
                恢复
              </Button>
            )}
            {!['completed', 'cancelled'].includes(plan.status) && (
              <Button danger onClick={() => planActionMutation.mutate('cancel')}>
                取消
              </Button>
            )}
          </Space>
        )}
      </Space>

      {plan ? (
        <Card size="small">
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="计划名称">{plan.name}</Descriptions.Item>
            <Descriptions.Item label="状态">{plan.status}</Descriptions.Item>
            <Descriptions.Item label="群组来源">
              {String((plan.recipient_config as Record<string, unknown> | undefined)?.group_id ?? '—')}
            </Descriptions.Item>
            <Descriptions.Item label="发送域名">{plan.domain_id ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="发件设置">
              {plan.sender_name ?? '—'} / {plan.sender_email ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label="人数">
              {plan.sent_count ?? 0} / {plan.total_recipients ?? 0}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDate(plan.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatDate(plan.updated_at)}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{plan.description ?? '—'}</Descriptions.Item>
          </Descriptions>
        </Card>
      ) : (
        <Card size="small">
          <Empty description={detailQuery.isLoading ? '正在加载详情' : '未找到该计划'} />
        </Card>
      )}

      <Card
        size="small"
        title="预览与锁定"
        extra={<Text type="secondary">可发送人数：{eligibleRecipients}</Text>}
      >
        {previewRecipients.length === 0 ? (
          <Empty description="暂无 preview 结果，可在 New 页创建后或点击锁定收件人后再查看。" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table rowKey={(_, index) => String(index)} columns={previewColumns} dataSource={previewRecipients} pagination={false} />
        )}
      </Card>

      <Card size="small" title="序列步骤">
        <Table rowKey="id" columns={stepColumns} dataSource={steps} loading={stepsQuery.isLoading} pagination={false} />
      </Card>

      <Card size="small" title="已锁定收件人">
        <Table rowKey="id" columns={recipientColumns} dataSource={recipients} loading={recipientsQuery.isLoading} pagination={false} />
      </Card>

      <Card size="small" title="样例邮件">
        {samples.length === 0 ? (
          <Alert type="info" showIcon message="当前还没有样例邮件，可先配置模板或锁定收件人。" />
        ) : (
          <Table rowKey={(_, index) => String(index)} columns={sampleColumns} dataSource={samples} pagination={false} />
        )}
      </Card>
    </Space>
  );
}

Component.displayName = 'SendPlanDetailPage';
