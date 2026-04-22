import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Modal,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import type { AiProviderConfig, AiUsageSummary, AiUsageTrend } from '@shared/types';
import { createApiClient, createTenantApi, queryKeys } from '@shared/api';

const { Title, Paragraph } = Typography;

const api = createTenantApi(createApiClient('tenant'));
type UsageItem = NonNullable<AiUsageSummary['items']>[number];

const STATUS_TAGS: Record<string, { color: string; label: string }> = {
  available: { color: 'green', label: '可用' },
  insufficient_balance: { color: 'orange', label: '余额不足' },
  unknown: { color: 'gold', label: '余额未知' },
  invalid_api_key: { color: 'red', label: 'Key 无效' },
  provider_error: { color: 'red', label: '服务异常' },
  not_configured: { color: 'default', label: '未配置' },
};

function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function statusAlert(config?: AiProviderConfig) {
  const status = config?.balance.status ?? 'not_configured';
  if (status === 'available') {
    return {
      type: 'success' as const,
      message: `OpenRouter 可用，当前可判定余额 ${config?.balance.amount ?? 0} ${config?.balance.currency ?? 'USD'}`,
    };
  }
  if (status === 'not_configured') {
    return {
      type: 'info' as const,
      message: '当前租户尚未配置 OpenRouter API key，AI 功能默认禁用。',
    };
  }
  return {
    type: 'warning' as const,
    message: config?.balance.message ?? '当前 OpenRouter 状态异常，AI 功能可能不可用。',
  };
}

export function Component() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<{ api_key: string }>();

  const [configQuery, summaryQuery, trendQuery] = useQueries({
    queries: [
      {
        queryKey: queryKeys.aiProvider.openrouter(),
        queryFn: async () => (await api.aiProvider.getOpenRouter()).data.data as AiProviderConfig,
      },
      {
        queryKey: queryKeys.aiProvider.usageSummary('month'),
        queryFn: async () => (await api.aiProvider.usageSummary('month')).data.data as AiUsageSummary,
      },
      {
        queryKey: queryKeys.aiProvider.usageTrend({ period: 'month' }),
        queryFn: async () => (await api.aiProvider.usageTrend()).data.data as AiUsageTrend[],
      },
    ],
  });

  const refreshAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.aiProvider.openrouter() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.aiProvider.usageSummary('month') }),
      queryClient.invalidateQueries({ queryKey: queryKeys.aiProvider.usageTrend({ period: 'month' }) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.aiCapabilities() }),
    ]);
  };

  const upsertMutation = useMutation({
    mutationFn: (values: { api_key: string }) => api.aiProvider.updateOpenRouter(values),
    onSuccess: async () => {
      message.success('OpenRouter API key 已更新');
      setModalOpen(false);
      form.resetFields();
      await refreshAll();
    },
    onError: () => message.error('OpenRouter API key 保存失败'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.aiProvider.deleteOpenRouter(),
    onSuccess: async () => {
      message.success('OpenRouter 配置已清空');
      await refreshAll();
    },
    onError: () => message.error('OpenRouter 配置清空失败'),
  });

  const refreshMutation = useMutation({
    mutationFn: () => api.aiProvider.refreshOpenRouterBalance(),
    onSuccess: async () => {
      message.success('余额状态已刷新');
      await refreshAll();
    },
    onError: () => message.error('余额刷新失败'),
  });

  const config = configQuery.data;
  const summary = summaryQuery.data;
  const trend = trendQuery.data ?? [];
  const alert = statusAlert(config);
  const summaryItems = summary?.items ?? [];
  const totalCalls = summaryItems.reduce((acc, item) => acc + (item.total_calls ?? 0), 0);
  const statusTag =
    STATUS_TAGS[config?.balance.status ?? 'not_configured'] ??
    { color: 'default', label: '未配置' };

  const trendColumns: ColumnsType<AiUsageTrend> = useMemo(
    () => [
      {
        title: '日期',
        dataIndex: 'usage_date',
        width: 160,
        render: (value: string | undefined, record) => value ?? record.date ?? '—',
      },
      {
        title: '场景',
        dataIndex: 'usage_type',
        width: 180,
        render: (value?: string) => <Tag>{value ?? 'unknown'}</Tag>,
      },
      {
        title: '调用次数',
        dataIndex: 'total_calls',
        width: 120,
        render: (value?: number) => value ?? 0,
      },
      {
        title: '费用',
        dataIndex: 'total_cost',
        width: 120,
        render: (value: number | undefined, record) => value ?? record.cost ?? 0,
      },
    ],
    [],
  );

  const usageColumns: ColumnsType<UsageItem> = useMemo(
    () => [
      {
        title: '场景',
        dataIndex: 'usage_type',
        render: (value?: string) => <Tag color="blue">{value ?? 'unknown'}</Tag>,
      },
      {
        title: '调用次数',
        dataIndex: 'total_calls',
        width: 140,
      },
      {
        title: '总费用',
        dataIndex: 'total_cost',
        width: 140,
      },
      {
        title: '总 tokens',
        dataIndex: 'total_tokens',
        width: 160,
      },
    ],
    [],
  );

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <div>
          <Title level={5} style={{ marginBottom: 0 }}>OpenRouter</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            每个租户单独维护自己的 OpenRouter API key，页面仅展示掩码、状态与用量。
          </Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} loading={refreshMutation.isPending} onClick={() => refreshMutation.mutate()}>
            刷新余额
          </Button>
          <Button type="primary" icon={<SafetyCertificateOutlined />} onClick={() => setModalOpen(true)}>
            {config?.is_configured ? '覆盖更新 Key' : '配置 Key'}
          </Button>
          <Button
            danger
            icon={<DeleteOutlined />}
            disabled={!config?.is_configured}
            loading={deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            清空配置
          </Button>
        </Space>
      </Space>

      <Alert type={alert.type} showIcon message={alert.message} />

      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card size="small" loading={configQuery.isLoading}>
            <Statistic
              title="余额状态"
              value={statusTag.label}
              valueStyle={{ color: statusTag.color === 'default' ? undefined : undefined }}
            />
            <div style={{ marginTop: 12 }}>
              <Tag color={statusTag.color}>{statusTag.label}</Tag>
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" loading={configQuery.isLoading}>
            <Statistic title="当前余额" value={config?.balance.amount ?? 0} suffix={config?.balance.currency ?? 'USD'} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" loading={summaryQuery.isLoading}>
            <Statistic title="本月调用次数" value={totalCalls} />
          </Card>
        </Col>
      </Row>

      <Card title="配置状态" size="small" loading={configQuery.isLoading}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="Provider">OpenRouter</Descriptions.Item>
          <Descriptions.Item label="是否已配置">{config?.is_configured ? '已配置' : '未配置'}</Descriptions.Item>
          <Descriptions.Item label="Key 掩码">{config?.secret_masked ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="最近刷新">{formatDate(config?.balance.checked_at)}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{formatDate(config?.updated_at)}</Descriptions.Item>
          <Descriptions.Item label="最近轮换">{formatDate(config?.last_rotated_at)}</Descriptions.Item>
          <Descriptions.Item label="最后修改人">
            {config?.configured_by ? `${config.configured_by.name ?? '未知'} (${config.configured_by.email ?? '—'})` : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="余额来源">{config?.balance.source ?? '—'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="额度细节" size="small" loading={configQuery.isLoading}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="可判定余额">{config?.balance.amount ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="币种">{config?.balance.currency ?? 'USD'}</Descriptions.Item>
          <Descriptions.Item label="Total Credits">{config?.balance.total_credits ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Total Usage">{config?.balance.total_usage ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Key Limit">{config?.balance.key_limit ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="Key Limit Remaining">{config?.balance.key_limit_remaining ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="状态消息" span={2}>
            {config?.balance.message ?? '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="本月用量汇总" size="small" loading={summaryQuery.isLoading}>
        <Table
          rowKey={(record) => record.usage_type}
          columns={usageColumns}
          dataSource={summaryItems}
          pagination={false}
          locale={{ emptyText: '暂无 AI 用量数据' }}
        />
      </Card>

      <Card title="用量趋势" size="small" loading={trendQuery.isLoading}>
        <Table
          rowKey={(record, index) => `${record.usage_date ?? record.date}-${record.usage_type}-${index}`}
          columns={trendColumns}
          dataSource={trend}
          pagination={{ pageSize: 7, size: 'small' }}
          locale={{ emptyText: '暂无趋势数据' }}
        />
      </Card>

      <Modal
        title={config?.is_configured ? '覆盖更新 OpenRouter API key' : '配置 OpenRouter API key'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async () => upsertMutation.mutate(await form.validateFields())}
        confirmLoading={upsertMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="api_key"
            label="OpenRouter API key"
            rules={[{ required: true, message: '请输入 OpenRouter API key' }]}
          >
            <Input.Password placeholder="sk-or-v1-..." autoComplete="off" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'AIProviderSettingsPage';
