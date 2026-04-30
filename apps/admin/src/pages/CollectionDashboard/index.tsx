import {
  Button,
  Card,
  Col,
  Empty,
  List,
  Progress,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import type { ProgressProps } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { CollectionKeyword } from '@shared/api';
import { adminApi } from '../../lib/api';

const { Text } = Typography;

type DashboardData = {
  today_companies: number;
  today_contacts: number;
  running_count: number;
  paused_count: number;
  error_count: number;
  keywords: CollectionKeyword[];
};

const EMPTY_DASHBOARD: DashboardData = {
  today_companies: 0,
  today_contacts: 0,
  running_count: 0,
  paused_count: 0,
  error_count: 0,
  keywords: [],
};

const STATUS_LABEL: Record<CollectionKeyword['subscription_status'], string> = {
  not_started: '未开始',
  pending: '排队中',
  running: '进行中',
  paused: '暂停',
  error: '异常',
  completed: '已完成',
};

const STATUS_COLOR: Record<CollectionKeyword['subscription_status'], string> = {
  not_started: 'default',
  pending: 'gold',
  running: 'blue',
  paused: 'default',
  error: 'red',
  completed: 'green',
};

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } }).response?.status === 404;
}

function progressPercent(todayCount: number, totalCount: number | null) {
  return Math.round((todayCount / Math.max(totalCount ?? 1, 1)) * 100);
}

function progressStatus(status: string | null): ProgressProps['status'] {
  if (status === 'running' || status === 'pending') return 'active';
  if (status === 'paused' || status === 'not_started' || status === 'cancelled' || status === null) return 'normal';
  if (status === 'error' || status === 'failed') return 'exception';
  if (status === 'completed') return 'success';
  return 'normal';
}

export function Component() {
  const { data, isFetching, refetch } = useQuery({
    queryKey: ['admin', 'collection-dashboard'],
    queryFn: async () => {
      try {
        return (await adminApi.collection.getDashboard()).data.data;
      } catch (error) {
        if (isNotFound(error)) {
          return EMPTY_DASHBOARD;
        }
        throw error;
      }
    },
    refetchInterval: 20_000,
  });

  const dashboard = data ?? EMPTY_DASHBOARD;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>采集看板</Typography.Title>
        <Button icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetch()}>
          刷新
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={5}>
          <Card><Statistic title="今日新增公司" value={dashboard.today_companies} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={5}>
          <Card><Statistic title="今日新增联系人" value={dashboard.today_contacts} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="进行中" value={dashboard.running_count} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <Card><Statistic title="暂停" value={dashboard.paused_count} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card><Statistic title="异常" value={dashboard.error_count} valueStyle={{ color: dashboard.error_count > 0 ? '#ff4d4f' : undefined }} /></Card>
        </Col>
      </Row>

      <Card title="关键词进度">
        <List
          dataSource={dashboard.keywords}
          locale={{ emptyText: <Empty description="暂无采集看板数据" /> }}
          renderItem={(keyword) => (
            <List.Item>
              <div style={{ width: '100%', display: 'grid', gridTemplateColumns: 'minmax(180px, 260px) 1fr', gap: 24 }}>
                <Space direction="vertical" size={4}>
                  <Space wrap>
                    <Text strong>{keyword.keyword}</Text>
                    <Tag color={STATUS_COLOR[keyword.subscription_status]}>
                      {STATUS_LABEL[keyword.subscription_status]}
                    </Tag>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    公司 {keyword.total_companies} · 联系人 {keyword.total_contacts}
                  </Text>
                </Space>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <div>
                    <Text type="secondary">直采进度</Text>
                    <Progress
                      percent={progressPercent(keyword.direct.today_pages, keyword.direct.total_pages)}
                      status={progressStatus(keyword.direct.status)}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {keyword.direct.today_pages}/{keyword.direct.total_pages ?? '?'} 页
                    </Text>
                  </div>
                  <div>
                    <Text type="secondary">反推进度</Text>
                    <Progress
                      percent={progressPercent(keyword.reverse_stage2.today_count, keyword.reverse_stage2.total_count)}
                      status={progressStatus(keyword.reverse_stage2.status)}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {keyword.reverse_stage2.today_count}/{keyword.reverse_stage2.total_count ?? '?'} 家
                    </Text>
                  </div>
                </Space>
              </div>
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}

Component.displayName = 'CollectionDashboardPage';
