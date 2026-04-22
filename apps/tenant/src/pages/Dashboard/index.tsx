import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Divider,
  List,
  Progress,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  BellOutlined,
  ReadOutlined,
  RightOutlined,
  SendOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import type { DashboardFunnel } from '@shared/types';
import { StatusTag } from '@shared/ui';
import { queryKeys } from '@shared/api';
import { tenantApi } from '../../lib/api';

const { Text } = Typography;

const FUNNEL_LABELS: Record<string, string> = {
  pending_score: '待评分',
  scoring: '评分中',
  scored: '已评分',
  selected: '已选中',
  in_plan: '计划中',
  contacted: '已触达',
  replied: '已回复',
  converted: '已转化',
  excluded: '已排除',
};

const PROVIDER_STATUS: Record<string, { color: string; label: string }> = {
  available: { color: 'green', label: '可用' },
  insufficient_balance: { color: 'orange', label: '余额不足' },
  unknown: { color: 'gold', label: '余额未知' },
  invalid_api_key: { color: 'red', label: 'Key 无效' },
  provider_error: { color: 'red', label: '服务异常' },
  not_configured: { color: 'default', label: '未配置' },
};

export function Component() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [
    overviewQuery,
    funnelQuery,
    aiCapabilitiesQuery,
    plansQuery,
    intelQuery,
    notificationsQuery,
  ] = useQueries({
    queries: [
      {
        queryKey: queryKeys.dashboard.overview(),
        queryFn: async () => (await tenantApi.dashboard.overview()).data.data,
      },
      {
        queryKey: queryKeys.dashboard.funnel(),
        queryFn: async () => (await tenantApi.dashboard.funnel()).data.data as DashboardFunnel,
      },
      {
        queryKey: queryKeys.dashboard.aiCapabilities(),
        queryFn: async () => (await tenantApi.dashboard.aiCapabilities()).data.data,
      },
      {
        queryKey: queryKeys.sendingPlans.list({ status: 'running', limit: 3 }),
        queryFn: async () => (await tenantApi.sendingPlans.list({ status: 'running', limit: 3 })).data,
      },
      {
        queryKey: queryKeys.intelligence.list({ limit: 3 }),
        queryFn: async () => (await tenantApi.intelligence.list({ limit: 3 })).data,
      },
      {
        queryKey: ['tenant', 'notifications', 'list'],
        queryFn: async () => (await tenantApi.notifications.list()).data,
      },
    ],
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => tenantApi.notifications.markRead(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'notifications', 'list'] });
    },
  });

  const overview = overviewQuery.data;
  const funnel = funnelQuery.data;
  const activePlans = plansQuery.data?.data ?? [];
  const articles = intelQuery.data?.data ?? [];
  const notifications = notificationsQuery.data?.data ?? [];
  const unreadCount = notifications.filter((item) => !item.is_read).length;
  const provider = aiCapabilitiesQuery.data?.provider;
  const providerStatus =
    PROVIDER_STATUS[provider?.balance_status ?? 'not_configured'] ??
    { color: 'default', label: '未配置' };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Alert
        type="info"
        showIcon
        message={
          <Space wrap>
            <ThunderboltOutlined />
            <Text>
              当前运行中计划 <Text strong>{overview?.running_plans ?? overview?.active_plans ?? 0}</Text> 个，未读通知{' '}
              <Text strong>{overview?.unread_notifications ?? unreadCount}</Text> 条。
            </Text>
            <Button type="link" size="small" onClick={() => navigate('/companies')}>
              查看公司 <RightOutlined />
            </Button>
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card loading={overviewQuery.isLoading} hoverable>
            <Statistic title="公司总数" value={overview?.total_companies ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={overviewQuery.isLoading} hoverable>
            <Statistic title="已评分公司" value={overview?.scored_companies ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={overviewQuery.isLoading} hoverable>
            <Statistic
              title="总计划数"
              value={overview?.total_plans ?? 0}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable onClick={() => navigate('/settings/ai-provider')} style={{ cursor: 'pointer' }}>
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Text type="secondary">OpenRouter</Text>
              <Text strong style={{ fontSize: 20 }}>
                {providerStatus.label}
              </Text>
              <Space wrap>
                <Tag color={providerStatus.color}>{providerStatus.label}</Tag>
                <Text type="secondary">
                  {provider?.balance_amount == null ? '—' : `${provider.balance_amount} ${provider?.balance_source ?? ''}`.trim()}
                </Text>
              </Space>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={14}>
          <Card
            title={
              <Space>
                <SendOutlined />
                <Text strong>进行中的发送计划</Text>
              </Space>
            }
            extra={<Button type="link" size="small" onClick={() => navigate('/send-plans')}>全部计划 <RightOutlined /></Button>}
          >
            {activePlans.length === 0 ? (
              <Text type="secondary">暂无进行中的发送计划</Text>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {activePlans.map((plan) => {
                  const total = plan.total_recipients ?? 0;
                  const sent = plan.sent_count ?? 0;
                  const progress = total > 0 ? Math.round((sent / total) * 100) : 0;

                  return (
                    <div key={plan.id} style={{ padding: '8px 0', cursor: 'pointer' }} onClick={() => navigate(`/send-plans/${plan.id}`)}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <Space>
                          <Text strong>{plan.name}</Text>
                          <StatusTag status={plan.status as never} />
                        </Space>
                        <Text type="secondary" style={{ fontSize: 12 }}>{sent}/{total} 人</Text>
                      </div>
                      <Progress percent={progress} size="small" strokeColor="#1677ff" />
                    </div>
                  );
                })}
              </Space>
            )}
          </Card>
        </Col>

        <Col span={10}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card
              title={
                <Space>
                  <ReadOutlined />
                  <Text strong>行业情报</Text>
                </Space>
              }
              extra={<Button type="link" size="small" onClick={() => navigate('/intelligence')}>全部情报 <RightOutlined /></Button>}
            >
              {articles.length === 0 ? (
                <Text type="secondary">暂无情报数据</Text>
              ) : (
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  {articles.slice(0, 3).map((article) => (
                    <div key={article.article_id}>
                      <Space style={{ marginBottom: 4 }}>
                        <Tag color={article.ai_category ? 'blue' : 'default'} style={{ fontSize: 11 }}>
                          {article.ai_category ?? '未分类'}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {article.published_at ?? article.article_created_at}
                        </Text>
                      </Space>
                      <div>
                        <Text strong style={{ fontSize: 13 }}>{article.title}</Text>
                      </div>
                      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
                        {article.content_summary?.slice(0, 60) ?? '暂无摘要'}
                      </Text>
                      <Divider style={{ margin: '10px 0 0 0' }} />
                    </div>
                  ))}
                </Space>
              )}
            </Card>

            <Card
              title={
                <Space>
                  <BellOutlined />
                  <Text strong>最新通知</Text>
                  {unreadCount > 0 && <Badge count={unreadCount} />}
                </Space>
              }
            >
              {notifications.length === 0 ? (
                <Text type="secondary">暂无通知</Text>
              ) : (
                <List
                  size="small"
                  dataSource={notifications.slice(0, 4)}
                  renderItem={(item) => (
                    <List.Item
                      style={{ opacity: item.is_read ? 0.65 : 1, cursor: item.is_read ? 'default' : 'pointer' }}
                      onClick={() => !item.is_read && markReadMutation.mutate(item.id)}
                      extra={<Text type="secondary" style={{ fontSize: 12 }}>{item.created_at}</Text>}
                    >
                      <Space>
                        {!item.is_read && <Badge dot />}
                        <Text>{item.title}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Space>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="转化漏斗" loading={funnelQuery.isLoading}>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              {funnel?.stages.length ? (
                funnel.stages.map((stage) => {
                  const percent = funnel.total > 0 ? Math.round((stage.count / funnel.total) * 100) : 0;
                  return (
                    <div key={stage.status}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <Text>{FUNNEL_LABELS[stage.status] ?? stage.status}</Text>
                        <Text type="secondary">{stage.count} / {percent}%</Text>
                      </div>
                      <Progress percent={percent} size="small" />
                    </div>
                  );
                })
              ) : (
                <Text type="secondary">暂无漏斗数据</Text>
              )}
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="核心指标">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>运行中计划</Text>
                <Text strong>{overview?.running_plans ?? overview?.active_plans ?? 0}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>已评分公司</Text>
                <Text strong>{overview?.scored_companies ?? 0}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>总计划数</Text>
                <Text strong>{overview?.total_plans ?? 0}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>未读通知</Text>
                <Text strong>{overview?.unread_notifications ?? unreadCount}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>AI 状态</Text>
                <Tag color={providerStatus.color}>{providerStatus.label}</Tag>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

Component.displayName = 'DashboardPage';
