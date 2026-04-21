import { useState } from 'react';
import {
  Alert,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Form,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  Button,
} from 'antd';
import { RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@shared/api';
import { AIBalanceGuard } from '@shared/ui';
import type { AiAnalysisResult, BillingBalance, EmailStats, EmailTrend, MonitorFilters, SendingPlan } from '@shared/types';
import { tenantApi } from '../../lib/api';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface MonitorFormValues {
  plan_id?: string;
  date_range?: [any, any];
  status?: string;
}

type RecordRow = Record<string, unknown>;

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return '请求失败，请稍后重试';
}

function toNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function toPercent(numerator: number, denominator: number) {
  if (!denominator) {
    return '0%';
  }
  return `${Math.round((numerator / denominator) * 1000) / 10}%`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  });
}

function formatFullDate(value?: string) {
  if (!value) {
    return '—';
  }
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function readText(row: RecordRow, keys: string[]) {
  for (const key of keys) {
    const value = row[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }
  return '—';
}

function readNumber(row: RecordRow, keys: string[]) {
  for (const key of keys) {
    const value = row[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
  }
  return 0;
}

function trendBarHeight(value: number, max: number) {
  if (!max) {
    return 6;
  }
  return Math.max(6, Math.round((value / max) * 100));
}

function buildMonitorFilters(values: MonitorFormValues): MonitorFilters {
  const [from, to] = values.date_range ?? [];
  return {
    plan_id: values.plan_id || undefined,
    status: values.status || undefined,
    date_from: from?.format?.('YYYY-MM-DD'),
    date_to: to?.format?.('YYYY-MM-DD'),
  };
}

export function Component() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<MonitorFormValues>();
  const [appliedFilters, setAppliedFilters] = useState<MonitorFilters>({});
  const [aiResult, setAiResult] = useState<AiAnalysisResult | null>(null);

  const [
    balanceQuery,
    plansQuery,
    statsQuery,
    trendQuery,
    byPlanQuery,
    byTemplateQuery,
    byGradeQuery,
    byStepQuery,
  ] = useQueries({
    queries: [
      {
        queryKey: queryKeys.billing.balance(),
        queryFn: async () => (await tenantApi.billing.balance()).data.data as BillingBalance,
      },
      {
        queryKey: queryKeys.sendingPlans.list(),
        queryFn: async () => (await tenantApi.sendingPlans.list()).data.data as SendingPlan[],
      },
      {
        queryKey: queryKeys.emails.stats(appliedFilters as Record<string, unknown>),
        queryFn: async () => (await tenantApi.emails.stats(appliedFilters)).data.data as EmailStats,
      },
      {
        queryKey: queryKeys.emails.trend(appliedFilters as Record<string, unknown>),
        queryFn: async () => (await tenantApi.emails.trend(appliedFilters)).data.data as EmailTrend[],
      },
      {
        queryKey: [...queryKeys.emails.all(), 'by-plan'],
        queryFn: async () => (await tenantApi.emails.statsByPlan()).data.data as RecordRow[],
      },
      {
        queryKey: [...queryKeys.emails.all(), 'by-template'],
        queryFn: async () => (await tenantApi.emails.statsByTemplate()).data.data as RecordRow[],
      },
      {
        queryKey: [...queryKeys.emails.all(), 'by-grade'],
        queryFn: async () => (await tenantApi.emails.statsByGrade()).data.data as RecordRow[],
      },
      {
        queryKey: [...queryKeys.emails.all(), 'by-step'],
        queryFn: async () => (await tenantApi.emails.statsByStep()).data.data as RecordRow[],
      },
    ],
  });

  const aiMutation = useMutation({
    mutationFn: async (filters: MonitorFilters) => (await tenantApi.emails.aiAnalysis(filters)).data.data as AiAnalysisResult,
    onSuccess: (result) => {
      setAiResult(result);
    },
    onError: (error) => {
      setAiResult(null);
      setAiError(getErrorMessage(error));
    },
  });

  const balance = balanceQuery.data;
  const plans = plansQuery.data ?? [];
  const stats = statsQuery.data;
  const trend = [...(trendQuery.data ?? [])].reverse();
  const byPlan = byPlanQuery.data ?? [];
  const byTemplate = byTemplateQuery.data ?? [];
  const byGrade = byGradeQuery.data ?? [];
  const byStep = byStepQuery.data ?? [];
  const totalSent = stats?.sent ?? stats?.total ?? 0;
  const balanceAmount = balance?.balance ?? balance?.amount ?? 0;
  const trendMax = Math.max(...trend.map((item) => toNumber(item.total)), 0);
  const [aiError, setAiError] = useState<string | null>(null);

  const applyFilters = () => {
    const values = form.getFieldsValue();
    const nextFilters = buildMonitorFilters(values);
    setAppliedFilters(nextFilters);
    setAiResult(null);
    setAiError(null);
    void queryClient.invalidateQueries({ queryKey: queryKeys.emails.all() });
  };

  const resetFilters = () => {
    form.resetFields();
    setAppliedFilters({});
    setAiResult(null);
    setAiError(null);
    void queryClient.invalidateQueries({ queryKey: queryKeys.emails.all() });
  };

  const triggerAiAnalysis = () => {
    setAiError(null);
    aiMutation.mutate(appliedFilters);
  };

  const trendColumns: ColumnsType<EmailTrend> = [
    {
      title: '日期',
      dataIndex: 'date',
      width: 120,
      render: (value: string) => <Text type="secondary">{formatFullDate(value)}</Text>,
    },
    {
      title: '总量',
      dataIndex: 'total',
      width: 100,
    },
    {
      title: '回复',
      dataIndex: 'replied',
      width: 100,
    },
    {
      title: '退信',
      dataIndex: 'bounced',
      width: 100,
    },
    {
      title: '回复率',
      width: 100,
      render: (_, record) => <Text>{toPercent(toNumber(record.replied), toNumber(record.total))}</Text>,
    },
    {
      title: '退信率',
      width: 100,
      render: (_, record) => <Text>{toPercent(toNumber(record.bounced), toNumber(record.total))}</Text>,
    },
  ];

  const byPlanColumns: ColumnsType<RecordRow> = [
    {
      title: '发送计划',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{readText(record, ['name', 'plan_name'])}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{readText(record, ['plan_id', 'id'])}</Text>
        </Space>
      ),
    },
    { title: '总量', dataIndex: 'total', width: 90, render: (_, record) => readNumber(record, ['total']) },
    { title: '回复', dataIndex: 'replied', width: 90, render: (_, record) => readNumber(record, ['replied']) },
    { title: '退信', dataIndex: 'bounced', width: 90, render: (_, record) => readNumber(record, ['bounced']) },
    {
      title: '回复率',
      width: 100,
      render: (_, record) => toPercent(readNumber(record, ['replied']), readNumber(record, ['total'])),
    },
  ];

  const byTemplateColumns: ColumnsType<RecordRow> = [
    {
      title: '模板',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{readText(record, ['name', 'template_name'])}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{readText(record, ['template_id', 'id'])}</Text>
        </Space>
      ),
    },
    { title: '总量', width: 90, render: (_, record) => readNumber(record, ['total']) },
  ];

  const byGradeColumns: ColumnsType<RecordRow> = [
    {
      title: '评级',
      render: (_, record) => <Tag>{readText(record, ['grade'])}</Tag>,
    },
    { title: '总量', width: 90, render: (_, record) => readNumber(record, ['total']) },
  ];

  const byStepColumns: ColumnsType<RecordRow> = [
    {
      title: '步骤',
      render: (_, record) => <Text strong>第 {readNumber(record, ['step_number', 'step'])} 封</Text>,
    },
    { title: '总量', width: 90, render: (_, record) => readNumber(record, ['total']) },
  ];

  const planOptions = plans.map((plan) => (
    <Option key={plan.id} value={plan.id}>
      {plan.name}
    </Option>
  ));

  const distributionTabs = [
    {
      key: 'plan',
      label: '按计划',
      children: (
        <Table
          rowKey={(record, index) => `${readText(record, ['plan_id', 'id'])}-${index}`}
          columns={byPlanColumns}
          dataSource={byPlan}
          size="small"
          pagination={{ pageSize: 5 }}
          loading={byPlanQuery.isLoading}
          locale={{ emptyText: '暂无计划分布数据' }}
        />
      ),
    },
    {
      key: 'template',
      label: '按模板',
      children: (
        <Table
          rowKey={(record, index) => `${readText(record, ['template_id', 'id'])}-${index}`}
          columns={byTemplateColumns}
          dataSource={byTemplate}
          size="small"
          pagination={{ pageSize: 5 }}
          loading={byTemplateQuery.isLoading}
          locale={{ emptyText: '暂无模板分布数据' }}
        />
      ),
    },
    {
      key: 'grade',
      label: '按评级',
      children: (
        <Table
          rowKey={(record, index) => `${readText(record, ['grade'])}-${index}`}
          columns={byGradeColumns}
          dataSource={byGrade}
          size="small"
          pagination={false}
          loading={byGradeQuery.isLoading}
          locale={{ emptyText: '暂无评级分布数据' }}
        />
      ),
    },
    {
      key: 'step',
      label: '按步骤',
      children: (
        <Table
          rowKey={(record, index) => `${readText(record, ['step_number', 'step'])}-${index}`}
          columns={byStepColumns}
          dataSource={byStep}
          size="small"
          pagination={false}
          loading={byStepQuery.isLoading}
          locale={{ emptyText: '暂无步骤分布数据' }}
        />
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Title level={5} style={{ marginBottom: 0 }}>邮件监控</Title>

      {(balanceQuery.isError || statsQuery.isError || trendQuery.isError) && (
        <Alert
          type="error"
          showIcon
          message="监控数据加载失败"
          description={getErrorMessage(balanceQuery.error ?? statsQuery.error ?? trendQuery.error)}
        />
      )}

      <Row gutter={[12, 12]}>
        <Col span={6}>
          <Card size="small" loading={balanceQuery.isLoading}>
            <Statistic title="AI 余额" value={balanceAmount} suffix={balance?.currency ?? 'token'} prefix={<RobotOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={statsQuery.isLoading}>
            <Statistic title="总邮件" value={stats?.total ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={statsQuery.isLoading}>
            <Statistic title="送达率" value={toPercent(stats?.delivered ?? 0, totalSent)} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" loading={statsQuery.isLoading}>
            <Statistic title="回复率" value={toPercent(stats?.replied ?? 0, totalSent)} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
      </Row>

      <Card size="small">
        <Form form={form} layout="inline" style={{ rowGap: 8 }}>
          <Form.Item label="发送计划" name="plan_id">
            <Select placeholder="全部" style={{ width: 220 }} allowClear showSearch optionFilterProp="children">
              {planOptions}
            </Select>
          </Form.Item>
          <Form.Item label="时间范围" name="date_range">
            <RangePicker style={{ width: 260 }} />
          </Form.Item>
          <Form.Item label="邮件状态" name="status">
            <Select placeholder="全部" style={{ width: 160 }} allowClear>
              <Option value="sent">已发送</Option>
              <Option value="delivered">已送达</Option>
              <Option value="opened">已打开</Option>
              <Option value="clicked">已点击</Option>
              <Option value="replied">已回复</Option>
              <Option value="bounced">已退信</Option>
              <Option value="unsubscribed">已退订</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" icon={<ReloadOutlined />} onClick={applyFilters}>
                刷新
              </Button>
              <Button onClick={resetFilters}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="发送趋势" size="small" loading={trendQuery.isLoading}>
            {trendQuery.isError ? (
              <Alert type="error" showIcon message="趋势加载失败" description={getErrorMessage(trendQuery.error)} />
            ) : trend.length === 0 ? (
              <Empty description="暂无趋势数据" />
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, minHeight: 180 }}>
                  {trend.slice(-14).map((item) => {
                    const total = toNumber(item.total);
                    return (
                      <div key={item.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                        <div
                          title={`${item.date}: ${total}`}
                          style={{
                            width: '100%',
                            minHeight: 6,
                            height: trendBarHeight(total, trendMax),
                            borderRadius: 4,
                            background: '#1677ff',
                            marginTop: 'auto',
                          }}
                        />
                        <Text style={{ fontSize: 11 }}>{formatDate(item.date)}</Text>
                        <Text type="secondary" style={{ fontSize: 11 }}>{total}</Text>
                      </div>
                    );
                  })}
                </div>
                <Table
                  rowKey={(record, index) => `${record.date}-${index}`}
                  columns={trendColumns}
                  dataSource={trend}
                  size="small"
                  pagination={{ pageSize: 6 }}
                  loading={trendQuery.isLoading}
                />
              </Space>
            )}
          </Card>
        </Col>

        <Col span={12}>
          <Card title="AI 智能分析" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                <Text type="secondary">
                  基于当前筛选条件调用后端分析，返回真实摘要和建议。
                </Text>
                <AIBalanceGuard balance={balanceAmount}>
                  <Button
                    type="primary"
                    icon={<RobotOutlined />}
                    loading={aiMutation.isPending}
                    onClick={triggerAiAnalysis}
                  >
                    AI 分析
                  </Button>
                </AIBalanceGuard>
              </Space>

              {aiError && <Alert type="error" showIcon message="AI 分析失败" description={aiError} />}

              {aiMutation.isPending && (
                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                  <Spin />
                  <div style={{ marginTop: 12 }}>
                    <Text type="secondary">AI 正在分析邮件数据，请稍候…</Text>
                  </div>
                </div>
              )}

              {!aiMutation.isPending && !aiResult && !aiError && (
                <Empty description="点击 AI 分析获取当前邮件监控洞察" />
              )}

              {aiResult && (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Alert type="info" showIcon message={aiResult.summary} />
                  {Array.isArray(aiResult.insights) && aiResult.insights.length > 0 && (
                    <Card size="small" type="inner" title="洞察">
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        {aiResult.insights.map((item, index) => (
                          <Alert key={index} type="info" showIcon message={item} />
                        ))}
                      </Space>
                    </Card>
                  )}
                  {Array.isArray(aiResult.recommendations) && aiResult.recommendations.length > 0 && (
                    <Card size="small" type="inner" title="建议">
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        {aiResult.recommendations.map((item, index) => (
                          <Alert key={index} type="success" showIcon message={item} />
                        ))}
                      </Space>
                    </Card>
                  )}
                  {aiResult.stats && (
                    <Descriptions bordered size="small" column={2} title={<Text strong>分析结果</Text>}>
                      {Object.entries(aiResult.stats).map(([key, value]) => (
                        <Descriptions.Item key={key} label={key}>
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  )}
                </Space>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="分布表" size="small">
        {(byPlanQuery.isError || byTemplateQuery.isError || byGradeQuery.isError || byStepQuery.isError) && (
          <Alert
            style={{ marginBottom: 16 }}
            type="warning"
            showIcon
            message="部分分布数据加载失败"
            description={getErrorMessage(
              byPlanQuery.error ?? byTemplateQuery.error ?? byGradeQuery.error ?? byStepQuery.error,
            )}
          />
        )}
        <Tabs items={distributionTabs} />
      </Card>
    </Space>
  );
}

Component.displayName = 'EmailMonitorPage';
