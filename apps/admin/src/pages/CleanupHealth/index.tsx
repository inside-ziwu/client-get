import {
  Alert,
  Badge,
  Card,
  Col,
  Collapse,
  Row,
  Space,
  Statistic,
  Table,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../lib/api';

interface CleanupHealthData {
  pending_count: number;
  oldest_pending_seconds: number | null;
  failed_exhausted_count: number;
  processed_per_minute: number;
  reconcile_a: Array<Record<string, unknown>>;
  reconcile_b: Array<Record<string, unknown>>;
  reconcile_c: Array<Record<string, unknown>>;
}

const EMPTY_HEALTH: CleanupHealthData = {
  pending_count: 0,
  oldest_pending_seconds: null,
  failed_exhausted_count: 0,
  processed_per_minute: 0,
  reconcile_a: [],
  reconcile_b: [],
  reconcile_c: [],
};

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } }).response?.status === 404;
}

function formatDuration(seconds: number | null) {
  if (seconds === null) {
    return '—';
  }
  if (seconds >= 3600) {
    return `${Math.floor(seconds / 60)} 分钟`;
  }

  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
}

function cardAlertStyle(level: 'normal' | 'warning' | 'error') {
  if (level === 'error') {
    return { borderColor: '#ff4d4f', borderWidth: 2 };
  }
  if (level === 'warning') {
    return { borderColor: '#faad14', borderWidth: 2 };
  }
  return undefined;
}

function valueColor(level: 'normal' | 'warning' | 'error') {
  if (level === 'error') return '#ff4d4f';
  if (level === 'warning') return '#faad14';
  return undefined;
}

function pendingLevel(count: number) {
  if (count > 500) return 'error' as const;
  if (count > 200) return 'warning' as const;
  return 'normal' as const;
}

function oldestLevel(seconds: number | null) {
  return seconds !== null && seconds > 600 ? 'error' as const : 'normal' as const;
}

function failedLevel(count: number) {
  return count > 0 ? 'error' as const : 'normal' as const;
}

function formatCell(value: unknown) {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function ReconcileTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  const firstRow = rows[0];
  const columns: ColumnsType<Record<string, unknown>> = firstRow
    ? Object.keys(firstRow).map((key) => ({
        title: key,
        dataIndex: key,
        ellipsis: true,
        render: (value: unknown) => formatCell(value),
      }))
    : [];

  return (
    <Table<Record<string, unknown>>
      columns={columns}
      dataSource={rows}
      rowKey={(_, index) => String(index ?? 0)}
      pagination={false}
      size="small"
    />
  );
}

export function Component() {
  const { data, isFetching } = useQuery({
    queryKey: ['admin', 'cleanup-health'],
    queryFn: async () => {
      try {
        return (await adminApi.collection.getCleanupHealth()).data.data;
      } catch (error) {
        if (isNotFound(error)) {
          return EMPTY_HEALTH;
        }
        throw error;
      }
    },
    refetchInterval: 30_000,
  });

  const health = data ?? EMPTY_HEALTH;
  const pendingAlert = pendingLevel(health.pending_count);
  const oldestAlert = oldestLevel(health.oldest_pending_seconds);
  const failedAlert = failedLevel(health.failed_exhausted_count);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={4} style={{ margin: 0 }}>清洗健康</Typography.Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={isFetching} style={cardAlertStyle(pendingAlert)}>
            <Statistic
              title="待处理"
              value={health.pending_count}
              valueStyle={{ color: valueColor(pendingAlert) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={isFetching} style={cardAlertStyle(oldestAlert)}>
            <Statistic
              title="最早等待"
              value={formatDuration(health.oldest_pending_seconds)}
              valueStyle={{ color: valueColor(oldestAlert) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={isFetching} style={cardAlertStyle(failedAlert)}>
            <Statistic
              title="失败累积"
              value={health.failed_exhausted_count}
              valueStyle={{ color: valueColor(failedAlert) }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={isFetching}>
            <Statistic title="处理速率" value={health.processed_per_minute} suffix="条/分钟" />
          </Card>
        </Col>
      </Row>

      <Collapse
        items={[
          {
            key: 'reconcile_a',
            label: (
              <Space>
                <span>差集 A（raw → cleanup_queue 缺失）</span>
                <Badge count={health.reconcile_a.length} />
              </Space>
            ),
            children: (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Alert type="error" showIcon message="事务原子性异常，正常应为 0。" />
                <ReconcileTable rows={health.reconcile_a} />
              </Space>
            ),
          },
          {
            key: 'reconcile_b',
            label: (
              <Space>
                <span>差集 B（cleanup_queue done → clean_companies 缺失）</span>
                <Badge count={health.reconcile_b.length} />
              </Space>
            ),
            children: (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Alert type="warning" showIcon message="清洗写入失败。" />
                <ReconcileTable rows={health.reconcile_b} />
              </Space>
            ),
          },
          {
            key: 'reconcile_c',
            label: (
              <Space>
                <span>差集 C（clean_companies → tenant_companies 缺失）</span>
                <Badge count={health.reconcile_c.length} />
              </Space>
            ),
            children: (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Alert type="info" showIcon message="未关联租户。" />
                <ReconcileTable rows={health.reconcile_c} />
              </Space>
            ),
          },
        ]}
      />
    </Space>
  );
}

Component.displayName = 'CleanupHealthPage';
