import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Empty,
  Form,
  Input,
  message,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Typography,
} from 'antd';
import {
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { queryKeys, type SendingPlan } from '@shared/api';
import { StatusTag } from '@shared/ui';
import type { SendingPlanStatus } from '@shared/types';
import { tenantApi } from '../../lib/api';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text, Title } = Typography;

const STATUS_OPTIONS: SendingPlanStatus[] = ['draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled'];

interface PlanFiltersState {
  keyword?: string;
  status?: SendingPlanStatus[];
  created_at?: [any, any];
}

function formatDateTime(value?: string) {
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

function parseDateTime(value?: string) {
  if (!value) {
    return null;
  }
  const time = new Date(value).getTime();
  return Number.isNaN(time) ? null : time;
}

function normalizeText(value: unknown) {
  return typeof value === 'string' ? value.trim().toLowerCase() : '';
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return '请求失败，请稍后重试';
}

function getPlanProgress(plan: Pick<SendingPlan, 'sent_count' | 'total_recipients'>) {
  const total = plan.total_recipients ?? 0;
  const sent = plan.sent_count ?? 0;
  return total > 0 ? Math.round((sent / total) * 100) : 0;
}

export function Component() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filterForm] = Form.useForm<PlanFiltersState>();
  const [appliedFilters, setAppliedFilters] = useState<PlanFiltersState>({});

  const plansQuery = useQuery({
    queryKey: queryKeys.sendingPlans.list(),
    queryFn: async () => (await tenantApi.sendingPlans.list()).data.data,
  });

  const actionMutation = useMutation({
    mutationFn: async (payload: { id: string; action: 'start' | 'pause' | 'resume' | 'cancel' | 'delete' }) => {
      const { id, action } = payload;
      if (action === 'start') {
        return tenantApi.sendingPlans.start(id);
      }
      if (action === 'pause') {
        return tenantApi.sendingPlans.pause(id);
      }
      if (action === 'resume') {
        return tenantApi.sendingPlans.resume(id);
      }
      if (action === 'cancel') {
        return tenantApi.sendingPlans.cancel(id);
      }
      return tenantApi.sendingPlans.delete(id);
    },
    onSuccess: async (_, variables) => {
      const labels: Record<string, string> = {
        start: '已启动',
        pause: '已暂停',
        resume: '已恢复',
        cancel: '已取消',
        delete: '已删除',
      };
      message.success(labels[variables.action]);
      await queryClient.invalidateQueries({ queryKey: queryKeys.sendingPlans.all() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all() });
    },
    onError: (error) => {
      message.error(getErrorMessage(error));
    },
  });

  const plans = plansQuery.data ?? [];
  const keyword = normalizeText(appliedFilters.keyword);
  const [createdFrom, createdTo] = appliedFilters.created_at ?? [];

  const visiblePlans = plans.filter((plan) => {
    if (appliedFilters.status?.length && !appliedFilters.status.includes(plan.status as SendingPlanStatus)) {
      return false;
    }

    if (keyword && !normalizeText(plan.name).includes(keyword)) {
      return false;
    }

    const createdAt = parseDateTime(plan.created_at);
    if (createdAt && createdFrom && createdTo) {
      const start = parseDateTime(createdFrom);
      const end = parseDateTime(createdTo);
      if (start !== null && end !== null) {
        const endOfDay = end + 24 * 60 * 60 * 1000 - 1;
        if (createdAt < start || createdAt > endOfDay) {
          return false;
        }
      }
    }

    return true;
  });

  const submitFilters = () => {
    const values = filterForm.getFieldsValue();
    const range = values.created_at;
    setAppliedFilters({
      keyword: values.keyword?.trim(),
      status: values.status,
      created_at:
        range?.[0] && range?.[1]
          ? [range[0].format('YYYY-MM-DD'), range[1].format('YYYY-MM-DD')]
          : undefined,
    });
  };

  const resetFilters = () => {
    filterForm.resetFields();
    setAppliedFilters({});
  };

  const columns: ColumnsType<SendingPlan> = [
    {
      title: '计划名称',
      dataIndex: 'name',
      render: (name: string, record) => (
        <Button type="link" style={{ padding: 0, fontWeight: 500 }} onClick={() => navigate(`/send-plans/${record.id}`)}>
          {name}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (status: string) => <StatusTag status={status as SendingPlanStatus} />,
    },
    {
      title: '收件人',
      width: 110,
      render: (_, record) => {
        const total = record.total_recipients ?? 0;
        const sent = record.sent_count ?? 0;
        return <Text>{total > 0 ? `${sent}/${total} 人` : '—'}</Text>;
      },
    },
    {
      title: '进度',
      width: 180,
      render: (_, record) =>
        record.status === 'draft' ? (
          <Text type="secondary">—</Text>
        ) : (
          <Progress
            percent={getPlanProgress(record)}
            size="small"
            strokeColor={record.status === 'completed' ? '#52c41a' : '#1677ff'}
            style={{ marginBottom: 0 }}
          />
        ),
    },
    {
      title: '时间',
      width: 180,
      render: (_, record) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {record.started_at
            ? `${formatDateTime(record.started_at)} 开始`
            : record.scheduled_at
              ? `${formatDateTime(record.scheduled_at)} 排期`
              : formatDateTime(record.created_at)}
        </Text>
      ),
    },
    {
      title: '操作',
      width: 260,
      render: (_, record) => {
        const status = record.status as SendingPlanStatus;
        const busy = actionMutation.isPending;

        return (
          <Space size={4} wrap>
            <Button type="link" size="small" onClick={() => navigate(`/send-plans/${record.id}`)}>
              详情
            </Button>

            {(status === 'draft' || status === 'scheduled') && (
              <Popconfirm
                title="确认启动此计划？"
                onConfirm={() => actionMutation.mutate({ id: record.id, action: 'start' })}
              >
                <Button type="link" size="small" icon={<PlayCircleOutlined />} disabled={busy}>
                  启动
                </Button>
              </Popconfirm>
            )}

            {status === 'running' && (
              <Popconfirm
                title="确认暂停此计划？"
                onConfirm={() => actionMutation.mutate({ id: record.id, action: 'pause' })}
              >
                <Button type="link" size="small" icon={<PauseCircleOutlined />} disabled={busy}>
                  暂停
                </Button>
              </Popconfirm>
            )}

            {status === 'paused' && (
              <Popconfirm
                title="确认恢复此计划？"
                onConfirm={() => actionMutation.mutate({ id: record.id, action: 'resume' })}
              >
                <Button type="link" size="small" icon={<PlayCircleOutlined />} disabled={busy}>
                  恢复
                </Button>
              </Popconfirm>
            )}

            {(status === 'running' || status === 'scheduled' || status === 'paused') && (
              <Popconfirm
                title="确认取消此计划？"
                onConfirm={() => actionMutation.mutate({ id: record.id, action: 'cancel' })}
              >
                <Button type="link" size="small" icon={<StopOutlined />} danger disabled={busy}>
                  取消
                </Button>
              </Popconfirm>
            )}

            {(status === 'draft' || status === 'cancelled') && (
              <Popconfirm
                title="确认删除此计划？"
                onConfirm={() => actionMutation.mutate({ id: record.id, action: 'delete' })}
              >
                <Button type="link" size="small" danger disabled={busy}>
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Space style={{ justifyContent: 'space-between', width: '100%' }} align="center">
          <Title level={5} style={{ margin: 0 }}>发送计划</Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/send-plans/new')}>
            新建计划
          </Button>
        </Space>

        {plansQuery.isError && (
          <Alert
            type="error"
            showIcon
            message="发送计划加载失败"
            description={getErrorMessage(plansQuery.error)}
          />
        )}

        <Card size="small">
          <Form form={filterForm} layout="inline" style={{ rowGap: 8 }}>
            <Form.Item name="status" label="状态">
              <Select mode="multiple" placeholder="全部" style={{ width: 220 }} allowClear maxTagCount="responsive">
                {STATUS_OPTIONS.map((status) => (
                  <Option key={status} value={status}>
                    <StatusTag status={status} />
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="keyword" label="关键字">
              <Input placeholder="搜索计划名称" prefix={<SearchOutlined />} style={{ width: 220 }} allowClear />
            </Form.Item>
            <Form.Item name="created_at" label="创建时间">
              <RangePicker style={{ width: 260 }} />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button type="primary" icon={<SearchOutlined />} onClick={submitFilters}>
                  搜索
                </Button>
                <Button icon={<ReloadOutlined />} onClick={resetFilters}>
                  重置
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={visiblePlans}
          loading={plansQuery.isLoading}
          size="middle"
          locale={{
            emptyText: (
              <Empty
                description={appliedFilters.keyword || appliedFilters.status?.length ? '没有匹配的发送计划' : '还没有发送计划'}
              >
                <Button type="primary" onClick={() => navigate('/send-plans/new')}>
                  新建计划
                </Button>
              </Empty>
            ),
          }}
        />
      </Space>
    </>
  );
}

Component.displayName = 'SendPlansPage';
