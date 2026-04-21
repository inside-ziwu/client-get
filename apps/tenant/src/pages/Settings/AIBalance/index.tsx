import {
  Alert,
  Card,
  Col,
  Descriptions,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQueries } from '@tanstack/react-query';
import { createApiClient, createTenantApi, queryKeys } from '@shared/api';
import type { BillingBalance, UsageSummary, UsageTrend } from '@shared/types';

const { Text, Title } = Typography;

interface BalanceTransaction {
  id: string;
  type: string;
  amount: number;
  balance_after: number;
  description?: string;
  created_at: string;
}

const api = createTenantApi(createApiClient('tenant'));

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function Component() {
  const [balanceQuery, transactionsQuery, summaryQuery, trendQuery] = useQueries({
    queries: [
      {
        queryKey: queryKeys.billing.balance(),
        queryFn: async () => (await api.billing.balance()).data.data as BillingBalance,
      },
      {
        queryKey: queryKeys.billing.transactions({ limit: 20 }),
        queryFn: async () => (await api.billing.transactions({ limit: 20 })).data.data as BalanceTransaction[],
      },
      {
        queryKey: queryKeys.billing.usageSummary('month'),
        queryFn: async () => (await api.billing.usageSummary('month')).data.data as UsageSummary,
      },
      {
        queryKey: queryKeys.billing.usageTrend({ period: 'month' }),
        queryFn: async () => (await api.billing.usageTrend()).data.data as UsageTrend[],
      },
    ],
  });

  const balance = balanceQuery.data;
  const transactions = transactionsQuery.data ?? [];
  const summary = summaryQuery.data;
  const trend = trendQuery.data ?? [];
  const currentBalance = balance?.balance ?? balance?.amount ?? 0;
  const balanceUnit = balance?.currency ?? 'credits';
  const summaryItems = summary?.items ?? [];
  const totalCost = summary?.total_cost ?? summaryItems.reduce((acc, item) => acc + item.total_cost, 0);

  const usageColumns: ColumnsType<BalanceTransaction> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: (value: string) => <Text type="secondary">{formatDate(value)}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      width: 120,
      render: (value: string) => <Tag>{value}</Tag>,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      width: 120,
      render: (value: number) => <Text strong>{value.toLocaleString()}</Text>,
    },
    {
      title: '余额',
      dataIndex: 'balance_after',
      width: 120,
      render: (value: number) => <Text>{value.toLocaleString()}</Text>,
    },
    {
      title: '说明',
      dataIndex: 'description',
      render: (value?: string) => <Text type="secondary">{value ?? '—'}</Text>,
    },
  ];

  const trendColumns: ColumnsType<UsageTrend> = [
    {
      title: '日期',
      dataIndex: 'usage_date',
      width: 120,
      render: (value: string, record) => <Text type="secondary">{value ?? record.date ?? '—'}</Text>,
    },
    {
      title: '场景',
      dataIndex: 'usage_type',
      width: 160,
      render: (value: string) => <Tag color="blue">{value ?? 'all'}</Tag>,
    },
    {
      title: '费用',
      dataIndex: 'total_cost',
      width: 120,
      render: (value: number, record) => <Text strong>{(value ?? record.cost ?? 0).toLocaleString()}</Text>,
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Title level={5} style={{ marginBottom: 0 }}>AI 额度</Title>

      {currentBalance < 200 && (
        <Alert
          type="warning"
          showIcon
          message="AI 额度不足 200，部分 AI 功能可能受限。"
        />
      )}

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card size="small" loading={balanceQuery.isLoading}>
            <Statistic
              title="当前余额"
              value={currentBalance}
              suffix={balanceUnit}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={summaryQuery.isLoading}>
            <Statistic
              title="本期总费用"
              value={totalCost}
              suffix={balanceUnit}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={transactionsQuery.isLoading}>
            <Statistic
              title="最近流水"
              value={transactions.length}
              suffix="条"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={trendQuery.isLoading}>
            <Statistic
              title="趋势记录"
              value={trend.length}
              suffix="条"
            />
          </Card>
        </Col>
      </Row>

      <Card title="费用构成" size="small" loading={summaryQuery.isLoading}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          {summaryItems.map((item) => {
            const percent = totalCost ? Math.round((item.total_cost / totalCost) * 100) : 0;
            return (
              <div key={item.usage_type} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Text style={{ width: 140, flexShrink: 0 }}>{item.usage_type}</Text>
                <Progress percent={percent} style={{ flex: 1, marginBottom: 0 }} />
                <Text style={{ width: 120, textAlign: 'right', flexShrink: 0 }}>
                  {item.total_calls} 次 / {item.total_cost.toLocaleString()}
                </Text>
              </div>
            );
          })}
          {summaryItems.length === 0 && (
            <Text type="secondary">暂无费用构成数据</Text>
          )}
        </Space>
      </Card>

      <Card title="近期交易" size="small">
        <Table<BalanceTransaction>
          rowKey="id"
          columns={usageColumns}
          dataSource={transactions}
          loading={transactionsQuery.isLoading}
          size="small"
          pagination={{ pageSize: 5, size: 'small' }}
          locale={{ emptyText: '暂无交易记录' }}
        />
      </Card>

      <Card title="费用趋势" size="small">
        <Table<UsageTrend>
          rowKey={(record, index) => `${record.usage_date ?? record.date}-${record.usage_type ?? 'all'}-${index}`}
          columns={trendColumns}
          dataSource={trend}
          loading={trendQuery.isLoading}
          size="small"
          pagination={{ pageSize: 7, size: 'small' }}
          locale={{ emptyText: '暂无趋势数据' }}
        />
      </Card>

      <Card size="small">
        <Descriptions column={2} size="small" title={<Text strong style={{ fontSize: 13 }}>额度说明</Text>}>
          <Descriptions.Item label="当前余额更新时间">{balance ? '实时查询' : '—'}</Descriptions.Item>
          <Descriptions.Item label="数据来源">/api/v1/billing/*</Descriptions.Item>
          <Descriptions.Item label="账单口径">本页仅展示后端返回结果，不做本地汇总。</Descriptions.Item>
          <Descriptions.Item label="提示">额度不足时请联系平台管理员。</Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
}

Component.displayName = 'AIBalanceSettingsPage';
