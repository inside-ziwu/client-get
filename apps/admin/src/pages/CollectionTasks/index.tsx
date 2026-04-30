import { useState } from 'react';
import {
  Badge,
  Button,
  Drawer,
  Popconfirm,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ClockCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  StopOutlined,
  SyncOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { CollectionHistoryItem, CollectionKeyword } from '@shared/api';
import { adminApi } from '../../lib/api';

const { Text } = Typography;

type ApiChannelKey = 'waimao_tong' | 'lixiaoyun';
type RowChannel = 'direct' | 'reverse';

const CHANNEL_LABEL = {
  direct: '直采（外贸通）',
  reverse: '反推（励销云→腾道）',
} as const;

const API_CHANNEL_BY_ROW: Record<RowChannel, ApiChannelKey> = {
  direct: 'waimao_tong',
  reverse: 'lixiaoyun',
};

const STATUS_COLOR: Record<string, string> = {
  not_started: 'default',
  pending: 'gold',
  running: 'blue',
  completed: 'green',
  failed: 'red',
  cancelled: 'default',
  paused: 'default',
  error: 'red',
};

const STATUS_LABEL: Record<string, string> = {
  not_started: '未执行',
  pending: '排队中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
  paused: '已暂停',
  error: '异常',
};

interface RowData {
  key: string;
  keyword: CollectionKeyword;
  channel: RowChannel;
  isFirst: boolean;
}

interface ReverseStageRow {
  key: 'stage1' | 'stage2';
  stage: string;
  status: string | null;
  totalCount: number;
  todayCount: number;
  dailyLimit: number | null;
  lastRunDate: string | null;
}

function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—';
}

function normalizeStatus(status: string | null) {
  return status ?? 'not_started';
}

function TaskStatus({ status }: { status: string | null }) {
  const normalized = normalizeStatus(status);
  return (
    <Space size={4}>
      <Badge color={STATUS_COLOR[normalized] ?? 'default'} />
      <Text>{STATUS_LABEL[normalized] ?? normalized}</Text>
    </Space>
  );
}

function channelStatus(row: RowData) {
  if (row.channel === 'direct') {
    return row.keyword.direct.status;
  }

  return row.keyword.reverse_stage2.status;
}

function channelLastRunDate(row: RowData) {
  if (row.channel === 'direct') {
    return row.keyword.direct.last_run_date;
  }

  return row.keyword.reverse_stage2.last_run_date;
}

function resultSummary(value: Record<string, unknown>) {
  const keys = Object.keys(value).filter((key) => key !== 'buyer_lookup_task_id');
  if (!keys.length) {
    return <Text type="secondary">—</Text>;
  }

  return (
    <Space size={4} wrap>
      {keys.map((key) => (
        <Text key={key} style={{ fontSize: 12 }}>
          {key.replace(/_count$/, '')}: {String(value[key])}
        </Text>
      ))}
    </Space>
  );
}

function ReverseDetailTable({ kw }: { kw: CollectionKeyword }) {
  const rows: ReverseStageRow[] = [
    {
      key: 'stage1',
      stage: 'stage1 励销云',
      status: kw.reverse_stage1.status,
      totalCount: kw.reverse_stage1.total_count,
      todayCount: kw.reverse_stage1.today_count,
      dailyLimit: kw.reverse_stage1.daily_limit,
      lastRunDate: kw.reverse_stage1.last_run_date,
    },
    {
      key: 'stage2',
      stage: 'stage2 腾道',
      status: kw.reverse_stage2.status,
      totalCount: kw.reverse_stage2.total_count,
      todayCount: kw.reverse_stage2.today_count,
      dailyLimit: kw.reverse_stage2.daily_limit,
      lastRunDate: kw.reverse_stage2.last_run_date,
    },
  ];

  const columns: ColumnsType<ReverseStageRow> = [
    {
      title: '阶段',
      dataIndex: 'stage',
      width: 160,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (value: string | null) => <TaskStatus status={value} />,
    },
    {
      title: '累计',
      dataIndex: 'totalCount',
      width: 120,
      render: (value: number) => <Text>{value} 家</Text>,
    },
    {
      title: '今日',
      key: 'today',
      width: 120,
      render: (_, row) => (
        <Text>
          {row.todayCount}/{row.dailyLimit ?? '?'}
        </Text>
      ),
    },
    {
      title: '上次运行',
      dataIndex: 'lastRunDate',
      render: (value: string | null) => formatDateTime(value),
    },
  ];

  return (
    <Table<ReverseStageRow>
      columns={columns}
      dataSource={rows}
      rowKey="key"
      pagination={false}
      size="small"
    />
  );
}

export function Component() {
  const queryClient = useQueryClient();
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyTarget, setHistoryTarget] = useState<{ keyword: CollectionKeyword; channel: RowChannel } | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin', 'collection-keywords'],
    queryFn: async () => (await adminApi.collection.listKeywords()).data.data,
    refetchInterval: 15_000,
  });

  const historyQuery = useQuery({
    queryKey: ['admin', 'collection-history', historyTarget?.keyword.keyword_normalized, historyTarget?.channel],
    queryFn: async () => {
      if (!historyTarget) return [];
      return (
        await adminApi.collection.listHistory(
          historyTarget.keyword.keyword_normalized,
          API_CHANNEL_BY_ROW[historyTarget.channel],
        )
      ).data.data;
    },
    enabled: !!historyTarget && historyOpen,
    staleTime: 0,
  });

  const invalidateKeywords = () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'collection-keywords'] });
  };

  const triggerMutation = useMutation({
    mutationFn: (params: { keyword: CollectionKeyword; channel: RowChannel }) =>
      adminApi.collection.trigger({
        keyword_normalized: params.keyword.keyword_normalized,
        channel: API_CHANNEL_BY_ROW[params.channel],
      }),
    onSuccess: (_, vars) => {
      message.success(`已触发「${vars.keyword.keyword}」${CHANNEL_LABEL[vars.channel]}`);
      invalidateKeywords();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message;
      message.error(detail ?? '触发失败，请重试');
    },
  });

  const stopMutation = useMutation({
    mutationFn: (keywordNormalized: string) => adminApi.collection.stop(keywordNormalized),
    onSuccess: () => {
      message.success('已提交停止任务');
      invalidateKeywords();
    },
    onError: () => message.error('停止失败，请重试'),
  });

  const resetMutation = useMutation({
    mutationFn: (keywordNormalized: string) => adminApi.collection.reset(keywordNormalized),
    onSuccess: () => {
      message.success('已重置关键词任务');
      invalidateKeywords();
    },
    onError: () => message.error('重置失败，请重试'),
  });

  const retryMutation = useMutation({
    mutationFn: (keywordNormalized: string) => adminApi.collection.retry(keywordNormalized),
    onSuccess: () => {
      message.success('已提交重试任务');
      invalidateKeywords();
    },
    onError: () => message.error('重试失败，请重试'),
  });

  const keywords = data ?? [];
  const rows: RowData[] = keywords.flatMap((keyword) =>
    (['direct', 'reverse'] as RowChannel[]).map((channel, index) => ({
      key: `${keyword.keyword_normalized}__${channel}`,
      keyword,
      channel,
      isFirst: index === 0,
    })),
  );

  const renderTriggerButton = (row: RowData, disabled = false) => (
    <Popconfirm
      title={`触发「${row.keyword.keyword}」${CHANNEL_LABEL[row.channel]}？`}
      onConfirm={() => triggerMutation.mutate({ keyword: row.keyword, channel: row.channel })}
      okText="确认"
      cancelText="取消"
      disabled={disabled}
    >
      <Tooltip title={disabled ? '当前渠道已有任务进行中' : undefined}>
        <Button
          size="small"
          icon={<PlayCircleOutlined />}
          disabled={disabled}
          loading={
            triggerMutation.isPending &&
            triggerMutation.variables?.keyword.keyword_normalized === row.keyword.keyword_normalized &&
            triggerMutation.variables?.channel === row.channel
          }
        >
          触发
        </Button>
      </Tooltip>
    </Popconfirm>
  );

  const renderDirectActions = (row: RowData) => {
    const keywordNormalized = row.keyword.keyword_normalized;
    const status = row.keyword.subscription_status;
    const isStopLoading = stopMutation.isPending && stopMutation.variables === keywordNormalized;
    const isResetLoading = resetMutation.isPending && resetMutation.variables === keywordNormalized;
    const isRetryLoading = retryMutation.isPending && retryMutation.variables === keywordNormalized;

    if (status === 'running' || status === 'pending') {
      return (
        <Button
          size="small"
          danger
          icon={<StopOutlined />}
          loading={isStopLoading}
          onClick={() => stopMutation.mutate(keywordNormalized)}
        >
          停止
        </Button>
      );
    }

    if (status === 'error') {
      return (
        <>
          <Button
            size="small"
            icon={<SyncOutlined />}
            loading={isRetryLoading}
            onClick={() => retryMutation.mutate(keywordNormalized)}
          >
            重试
          </Button>
          <Popconfirm
            title={`重置「${row.keyword.keyword}」全部采集状态？`}
            onConfirm={() => resetMutation.mutate(keywordNormalized)}
            okText="确认"
            cancelText="取消"
          >
            <Button size="small" icon={<UndoOutlined />} loading={isResetLoading}>
              重置
            </Button>
          </Popconfirm>
        </>
      );
    }

    if (status === 'paused') {
      return (
        <>
          {renderTriggerButton(row)}
          <Popconfirm
            title={`重置「${row.keyword.keyword}」全部采集状态？`}
            onConfirm={() => resetMutation.mutate(keywordNormalized)}
            okText="确认"
            cancelText="取消"
          >
            <Button size="small" icon={<UndoOutlined />} loading={isResetLoading}>
              重置
            </Button>
          </Popconfirm>
        </>
      );
    }

    return renderTriggerButton(row);
  };

  const columns: ColumnsType<RowData> = [
    {
      title: '关键词',
      key: 'keyword',
      width: 220,
      onCell: (row) => ({ rowSpan: row.isFirst ? 2 : 0 }),
      render: (_, row) => (
        <Space direction="vertical" size={2}>
          <Text strong>{row.keyword.keyword}</Text>
          <Space size={4} wrap>
            {row.keyword.tenants.map((tenant) => (
              <Tag key={tenant.id} style={{ fontSize: 11, marginBottom: 2 }}>{tenant.name}</Tag>
            ))}
          </Space>
          {row.keyword.error_msg && (
            <Text type="danger" style={{ fontSize: 12 }}>{row.keyword.error_msg}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '渠道',
      key: 'channel',
      width: 180,
      render: (_, row) => <Tag color={row.channel === 'direct' ? 'blue' : 'purple'}>{CHANNEL_LABEL[row.channel]}</Tag>,
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_, row) => <TaskStatus status={channelStatus(row)} />,
    },
    {
      title: '今日进度',
      key: 'progress',
      width: 160,
      render: (_, row) => {
        if (row.channel === 'direct') {
          const { today_pages, total_pages } = row.keyword.direct;
          return <Text>{today_pages}/{total_pages ?? '?'} 页</Text>;
        }

        const { today_count, total_count } = row.keyword.reverse_stage2;
        return <Text>{today_count}/{total_count ?? '?'} 家</Text>;
      },
    },
    {
      title: '累计',
      key: 'total',
      width: 220,
      onCell: (row) => ({ rowSpan: row.isFirst ? 2 : 0 }),
      render: (_, row) => (
        <Space direction="vertical" size={2}>
          <Text>公司 {row.keyword.total_companies} · 联系人 {row.keyword.total_contacts}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            最近运行：{formatDateTime(row.keyword.last_run_date)}
          </Text>
        </Space>
      ),
    },
    {
      title: '最近执行',
      key: 'lastRunDate',
      width: 180,
      render: (_, row) => formatDateTime(channelLastRunDate(row)),
    },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_, row) => (
        <Space wrap>
          {row.isFirst
            ? renderDirectActions(row)
            : renderTriggerButton(row)}
          <Button
            size="small"
            icon={<ClockCircleOutlined />}
            onClick={() => {
              setHistoryTarget({ keyword: row.keyword, channel: row.channel });
              setHistoryOpen(true);
            }}
          >
            历史
          </Button>
        </Space>
      ),
    },
  ];

  const historyColumns: ColumnsType<CollectionHistoryItem> = [
    {
      title: '创建时间',
      dataIndex: 'created_at',
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (value: string) => <Tag color={STATUS_COLOR[value] ?? 'default'}>{STATUS_LABEL[value] ?? value}</Tag>,
    },
    {
      title: '开始',
      dataIndex: 'started_at',
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '结束',
      dataIndex: 'completed_at',
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: '重试次数',
      dataIndex: 'attempt_count',
    },
    {
      title: '结果',
      dataIndex: 'result_summary',
      render: (value: Record<string, unknown>) => resultSummary(value),
    },
  ];

  return (
    <>
      <style>
        {`
          .collection-tasks-table .row-error > td {
            background: #fff1f0;
          }
        `}
      </style>
      <Space style={{ marginBottom: 16 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>采集任务管理</Typography.Title>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()} size="small">刷新</Button>
      </Space>

      <Table<RowData>
        className="collection-tasks-table"
        columns={columns}
        dataSource={rows}
        expandable={{
          rowExpandable: (row) => row.channel === 'reverse',
          expandedRowRender: (row) => <ReverseDetailTable kw={row.keyword} />,
        }}
        loading={isLoading}
        pagination={false}
        rowClassName={(row) => (row.keyword.error_msg ? 'row-error' : '')}
        rowKey="key"
        bordered
        size="middle"
      />

      <Drawer
        title={
          historyTarget
            ? `「${historyTarget.keyword.keyword}」${CHANNEL_LABEL[historyTarget.channel]} 历史记录`
            : '历史记录'
        }
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        width={820}
      >
        <Table<CollectionHistoryItem>
          columns={historyColumns}
          dataSource={historyQuery.data ?? []}
          loading={historyQuery.isLoading}
          rowKey="task_id"
          pagination={false}
          size="small"
        />
      </Drawer>
    </>
  );
}
