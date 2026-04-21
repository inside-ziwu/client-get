import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Spin,
  Steps,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ArrowLeftOutlined, ArrowRightOutlined, CheckCircleOutlined, SaveOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys, type TenantDomainInfo } from '@shared/api';
import { tenantApi } from '../../lib/api';

const { Title } = Typography;

type WizardFormValues = {
  name: string;
  description?: string;
  group_id: string;
  first_template_id: string;
  domain_id: string;
  sender_name: string;
  sender_email: string;
};

type DraftStep = {
  id: string;
  step_number: number;
  template_id: string;
  delay_days: number;
  condition_type: string;
};

const STEP_TITLES = ['基本信息', '收件人', '首封模板', '发送域名', '序列', '确认'];

function localId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatDomain(record: TenantDomainInfo) {
  return `${record.domain} / ${record.verification_status} / 日限 ${record.daily_limit ?? 0}`;
}

export function Component() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [current, setCurrent] = useState(0);
  const [form] = Form.useForm<WizardFormValues>();
  const [sequence, setSequence] = useState<DraftStep[]>([]);
  const [submittingMode, setSubmittingMode] = useState<'draft' | 'lock' | null>(null);

  const groupsQuery = useQuery({
    queryKey: ['tenant', 'groups', 'list', 'send-plan-new'],
    queryFn: async () => (await tenantApi.groups.list({ limit: 100 })).data.data,
  });

  const templatesQuery = useQuery({
    queryKey: ['tenant', 'templates', 'list', 'send-plan-new'],
    queryFn: async () => (await tenantApi.emailTemplates.list()).data.data,
  });

  const domainsQuery = useQuery({
    queryKey: ['tenant', 'domains', 'list', 'send-plan-new'],
    queryFn: async () => (await tenantApi.domains.list()).data.data,
  });

  const groups = groupsQuery.data ?? [];
  const templates = templatesQuery.data ?? [];
  const domains = domainsQuery.data ?? [];
  const verifiedDomains = useMemo(
    () => domains.filter((item) => item.verification_status === 'verified'),
    [domains],
  );

  const addStep = () => {
    setSequence((prev) => [
      ...prev,
      {
        id: localId(),
        step_number: prev.length + 2,
        template_id: '',
        delay_days: 3,
        condition_type: 'no_reply',
      },
    ]);
  };

  const updateStep = (id: string, payload: Partial<DraftStep>) => {
    setSequence((prev) => prev.map((item) => (item.id === id ? { ...item, ...payload } : item)));
  };

  const removeStep = (id: string) => {
    setSequence((prev) =>
      prev
        .filter((item) => item.id !== id)
        .map((item, index) => ({ ...item, step_number: index + 2 })),
    );
  };

  const submitMutation = useMutation({
    mutationFn: async (mode: 'draft' | 'lock') => {
      const values = await form.validateFields();
      const created = await tenantApi.sendingPlans.create({
        name: values.name.trim(),
        description: values.description?.trim() || undefined,
        recipient_source: 'group',
        recipient_config: { group_id: values.group_id },
        send_strategy: {
          timezone_aware: true,
          preferred_hours: [9, 17],
        },
        sender_name: values.sender_name.trim(),
        sender_email: values.sender_email.trim(),
        domain_id: values.domain_id,
      });

      const plan = created.data.data;
      await tenantApi.sendingPlans.createStep(plan.id, {
        step_number: 1,
        template_id: values.first_template_id,
        delay_days: 0,
        condition_type: 'always',
      });

      for (const item of sequence) {
        await tenantApi.sendingPlans.createStep(plan.id, {
          step_number: item.step_number,
          template_id: item.template_id,
          delay_days: item.delay_days,
          condition_type: item.condition_type,
        });
      }

      if (mode === 'lock') {
        await tenantApi.sendingPlans.previewRecipients(plan.id);
        await tenantApi.sendingPlans.lockRecipients(plan.id);
      }

      return { planId: plan.id, mode };
    },
    onSuccess: async ({ planId, mode }) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.sendingPlans.all() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all() }),
      ]);
      message.success(mode === 'lock' ? '发送计划已创建并锁定收件人' : '发送计划草稿已创建');
      navigate(`/send-plans/${planId}`, { replace: true });
    },
    onError: () => message.error('发送计划创建失败，请检查配置与接口状态'),
    onSettled: () => setSubmittingMode(null),
  });

  const firstTemplateId = Form.useWatch('first_template_id', form);
  const selectedGroupId = Form.useWatch('group_id', form);
  const selectedDomainId = Form.useWatch('domain_id', form);

  const selectedGroup = groups.find((item) => item.id === selectedGroupId);
  const selectedTemplate = templates.find((item) => item.id === firstTemplateId);
  const selectedDomain = domains.find((item) => item.id === selectedDomainId);

  const sequenceColumns: ColumnsType<DraftStep> = [
    {
      title: '序列',
      dataIndex: 'step_number',
      width: 80,
      render: (value) => <Tag color="blue">第 {value} 封</Tag>,
    },
    {
      title: '模板',
      dataIndex: 'template_id',
      render: (value, record) => (
        <Select
          value={value || undefined}
          placeholder="选择模板"
          style={{ width: '100%' }}
          onChange={(next) => updateStep(record.id, { template_id: next })}
          options={templates.map((item) => ({
            label: `${item.name} / ${item.category ?? 'uncategorized'}`,
            value: item.id,
          }))}
        />
      ),
    },
    {
      title: '触发条件',
      dataIndex: 'condition_type',
      width: 180,
      render: (value, record) => (
        <Select
          value={value}
          style={{ width: '100%' }}
          onChange={(next) => updateStep(record.id, { condition_type: next })}
          options={[
            { label: '未回复', value: 'no_reply' },
            { label: '未打开', value: 'not_opened' },
            { label: '已打开', value: 'opened' },
          ]}
        />
      ),
    },
    {
      title: '延迟天数',
      dataIndex: 'delay_days',
      width: 120,
      render: (value, record) => (
        <InputNumber
          min={1}
          value={value}
          onChange={(next) => updateStep(record.id, { delay_days: next ?? 3 })}
          style={{ width: '100%' }}
        />
      ),
    },
    {
      title: '操作',
      width: 100,
      render: (_, record) => (
        <Button type="link" danger size="small" onClick={() => removeStep(record.id)}>
          删除
        </Button>
      ),
    },
  ];

  const stepViews = [
    <Card key="basic" size="small">
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="计划名称" rules={[{ required: true, message: '请输入计划名称' }]}>
          <Input placeholder="例如：德国 PCB 首轮开发" />
        </Form.Item>
        <Form.Item name="description" label="计划说明">
          <Input.TextArea rows={4} placeholder="用于团队协作说明，可选" />
        </Form.Item>
      </Form>
    </Card>,

    <Card key="recipients" size="small">
      <Form form={form} layout="vertical">
        <Form.Item name="group_id" label="收件人群组" rules={[{ required: true, message: '请选择群组' }]}>
          <Select
            loading={groupsQuery.isLoading}
            placeholder="选择一个群组"
            options={groups.map((item) => ({
              label: `${item.name} (${item.member_count})`,
              value: item.id,
            }))}
          />
        </Form.Item>
      </Form>
      <Alert
        type="info"
        showIcon
        style={{ marginTop: 16 }}
        message={selectedGroup ? `当前群组成员数：${selectedGroup.member_count}` : '请选择群组后继续'}
      />
    </Card>,

    <Card key="template" size="small">
      <Form form={form} layout="vertical">
        <Form.Item name="first_template_id" label="第 1 封模板" rules={[{ required: true, message: '请选择模板' }]}>
          <Select
            loading={templatesQuery.isLoading}
            placeholder="选择首封模板"
            options={templates.map((item) => ({
              label: `${item.name} / ${item.category ?? item.source_type}`,
              value: item.id,
            }))}
          />
        </Form.Item>
      </Form>
      {selectedTemplate ? (
        <Descriptions size="small" bordered column={1} style={{ marginTop: 16 }}>
          <Descriptions.Item label="模板名称">{selectedTemplate.name}</Descriptions.Item>
          <Descriptions.Item label="来源">{selectedTemplate.source_type}</Descriptions.Item>
          <Descriptions.Item label="主题">{selectedTemplate.subject}</Descriptions.Item>
        </Descriptions>
      ) : (
        <Empty description="请选择一个模板" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
    </Card>,

    <Card key="domain" size="small">
      <Form form={form} layout="vertical">
        <Form.Item name="domain_id" label="发送域名" rules={[{ required: true, message: '请选择发送域名' }]}>
          <Select
            loading={domainsQuery.isLoading}
            placeholder="仅展示已验证域名"
            options={verifiedDomains.map((item) => ({
              label: formatDomain(item),
              value: item.id,
            }))}
          />
        </Form.Item>
        <Form.Item name="sender_name" label="发件人名称" rules={[{ required: true, message: '请输入发件人名称' }]}>
          <Input placeholder="ClientGet Demo" />
        </Form.Item>
        <Form.Item name="sender_email" label="发件邮箱" rules={[{ required: true, message: '请输入发件邮箱' }]}>
          <Input placeholder="hello@mail.example.com" />
        </Form.Item>
      </Form>
      {selectedDomain && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          showIcon
          message={`当前域名 ${selectedDomain.domain}，预热阶段 ${selectedDomain.warmup_level ?? 0}，日上限 ${selectedDomain.daily_limit ?? 0}`}
        />
      )}
    </Card>,

    <Card
      key="sequence"
      size="small"
      title="后续序列"
      extra={
        <Button onClick={addStep}>
          添加后续序列
        </Button>
      }
    >
      {sequence.length === 0 ? (
        <Empty description="当前只发送首封邮件，如需后续跟进可在这里补充序列。" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Table rowKey="id" columns={sequenceColumns} dataSource={sequence} pagination={false} />
      )}
    </Card>,

    <Card key="confirm" size="small">
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="计划名称">{form.getFieldValue('name') || '—'}</Descriptions.Item>
        <Descriptions.Item label="说明">{form.getFieldValue('description') || '—'}</Descriptions.Item>
        <Descriptions.Item label="群组">{selectedGroup ? `${selectedGroup.name} (${selectedGroup.member_count})` : '—'}</Descriptions.Item>
        <Descriptions.Item label="首封模板">{selectedTemplate?.name ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="发送域名">{selectedDomain?.domain ?? '—'}</Descriptions.Item>
        <Descriptions.Item label="发件设置">
          {form.getFieldValue('sender_name') || '—'} / {form.getFieldValue('sender_email') || '—'}
        </Descriptions.Item>
        <Descriptions.Item label="后续序列数">{sequence.length}</Descriptions.Item>
      </Descriptions>
      <Alert
        style={{ marginTop: 16 }}
        type="warning"
        showIcon
        message="保存草稿只会创建计划和步骤。创建并锁定会额外调用 previewRecipients + lockRecipients，之后可直接在详情页启动。"
      />
    </Card>,
  ];

  const nextStep = async () => {
    if (current < STEP_TITLES.length - 1) {
      if (current <= 3) {
        await form.validateFields();
      }
      setCurrent((prev) => prev + 1);
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/send-plans')}>
          返回列表
        </Button>
        <Title level={4} style={{ margin: 0 }}>
          新建发送计划
        </Title>
      </Space>

      <Steps current={current} items={STEP_TITLES.map((title) => ({ title }))} />

      {(groupsQuery.isLoading || templatesQuery.isLoading || domainsQuery.isLoading) && current > 0 ? (
        <Card size="small">
          <Spin />
        </Card>
      ) : (
        stepViews[current]
      )}

      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Button disabled={current === 0} onClick={() => setCurrent((prev) => prev - 1)}>
          上一步
        </Button>
        <Space>
          {current < STEP_TITLES.length - 1 ? (
            <Button type="primary" icon={<ArrowRightOutlined />} onClick={() => void nextStep()}>
              下一步
            </Button>
          ) : (
            <>
              <Button
                icon={<SaveOutlined />}
                loading={submittingMode === 'draft' && submitMutation.isPending}
                onClick={() => {
                  setSubmittingMode('draft');
                  submitMutation.mutate('draft');
                }}
              >
                保存草稿
              </Button>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                loading={submittingMode === 'lock' && submitMutation.isPending}
                onClick={() => {
                  setSubmittingMode('lock');
                  submitMutation.mutate('lock');
                }}
              >
                创建并锁定收件人
              </Button>
            </>
          )}
        </Space>
      </Space>
    </Space>
  );
}

Component.displayName = 'SendPlanWizardPage';
