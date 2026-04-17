import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Progress,
  Space,
  Tag,
  List,
  Button,
  Badge,
  Divider,
  Alert,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  SendOutlined,
  BellOutlined,
  ReadOutlined,
  RightOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { StatusTag } from '@shared/ui';
import type { SendingPlanStatus } from '@shared/types';

const { Text } = Typography;

interface ActivePlan {
  id: string;
  name: string;
  status: SendingPlanStatus;
  progress: number;
  sent: number;
  total: number;
  delivery_rate: number;
  reply_rate: number;
}

interface IntelArticle {
  id: string;
  title: string;
  category: string;
  published_at: string;
  summary: string;
}

interface NotificationItem {
  id: string;
  title: string;
  created_at: string;
  is_read: boolean;
}

const MOCK_PLANS: ActivePlan[] = [
  { id: 'p1', name: '德国PCB采购商首轮开发', status: 'running', progress: 78, sent: 54, total: 69, delivery_rate: 95, reply_rate: 4.2 },
  { id: 'p2', name: '美国电路板供应商触达', status: 'running', progress: 35, sent: 28, total: 80, delivery_rate: 92, reply_rate: 2.8 },
];

const MOCK_INTEL: IntelArticle[] = [
  { id: 'i1', title: '全球PCB行业2026年Q1市场报告', category: '行业动态', published_at: '2小时前', summary: '2026年Q1全球PCB市场规模达到135亿美元，东南亚产能扩张加速，中国厂商面临竞争压力，高端HDI板需求持续增长。' },
  { id: 'i2', title: '覆铜板价格动态 — 4月第3周', category: '价格走势', published_at: '5小时前', summary: '受原材料成本上升影响，覆铜板价格较上周上涨2.3%，预计短期内维持高位震荡。' },
  { id: 'i3', title: '欧盟PCB环保新规将于Q3生效', category: '政策法规', published_at: '昨天', summary: '欧盟新RoHS指令将于2026年Q3正式实施，出口欧洲市场的PCB厂商需提前准备合规文件。' },
];

const MOCK_NOTIFICATIONS: NotificationItem[] = [
  { id: 'n1', title: '域名 mail.xxx.com 升级至第3阶段', created_at: '2分钟前', is_read: false },
  { id: 'n2', title: 'AI余额不足，当前余额 ¥12.30', created_at: '1小时前', is_read: false },
  { id: 'n3', title: '采集任务完成，新增153家公司', created_at: '3小时前', is_read: true },
  { id: 'n4', title: '发送计划"德国首轮开发"已完成', created_at: '昨天', is_read: true },
];

const CATEGORY_COLOR: Record<string, string> = {
  '行业动态': 'blue',
  '价格走势': 'orange',
  '政策法规': 'red',
  '市场分析': 'purple',
};

export function Component() {
  const navigate = useNavigate();
  const unreadCount = MOCK_NOTIFICATIONS.filter((n) => !n.is_read).length;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 待评分提示 */}
      <Alert
        type="info"
        showIcon
        message={
          <Space>
            <ThunderboltOutlined />
            <Text>待评分公司: <Text strong>53家</Text>（T+1评分将在今晚执行）</Text>
            <Button type="link" size="small" onClick={() => navigate('/companies')}>
              查看 <RightOutlined />
            </Button>
          </Space>
        }
        closable
      />

      {/* 概览卡片 */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="今日已发送"
              value={127}
              suffix={
                <Text style={{ fontSize: 12 }}>
                  <ArrowUpOutlined style={{ color: '#52c41a' }} /> 12%
                </Text>
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="邮件打开率"
              value="22.5"
              suffix={
                <Space size={4}>
                  <Text>%</Text>
                  <Text style={{ fontSize: 12 }}>
                    <ArrowUpOutlined style={{ color: '#52c41a' }} /> 1.3%
                  </Text>
                </Space>
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable>
            <Statistic
              title="回复率"
              value="3.2"
              suffix={
                <Space size={4}>
                  <Text>%</Text>
                  <Text style={{ fontSize: 12 }}>
                    <ArrowDownOutlined style={{ color: '#ff4d4f' }} /> 0.5%
                  </Text>
                </Space>
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card
            hoverable
            onClick={() => navigate('/settings/ai-balance')}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="AI 剩余额度"
              value={520}
              prefix="¥"
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 两栏: 发送计划 + 行业情报 */}
      <Row gutter={[16, 16]}>
        {/* 进行中的发送计划 */}
        <Col span={14}>
          <Card
            title={
              <Space>
                <SendOutlined />
                <Text strong>进行中的发送计划</Text>
                <Badge count={MOCK_PLANS.length} style={{ backgroundColor: '#1677ff' }} />
              </Space>
            }
            extra={<Button type="link" size="small" onClick={() => navigate('/send-plans')}>全部计划 <RightOutlined /></Button>}
          >
            {MOCK_PLANS.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 0', color: '#999' }}>
                <Text type="secondary">暂无进行中的发送计划</Text>
                <div style={{ marginTop: 8 }}>
                  <Button type="primary" size="small" onClick={() => navigate('/send-plans/new')}>新建计划</Button>
                </div>
              </div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {MOCK_PLANS.map((plan) => (
                  <div
                    key={plan.id}
                    style={{ padding: '12px 0', cursor: 'pointer' }}
                    onClick={() => navigate(`/send-plans/${plan.id}`)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <Space>
                        <Text strong>{plan.name}</Text>
                        <StatusTag status={plan.status} />
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>{plan.sent}/{plan.total}人</Text>
                    </div>
                    <Progress
                      percent={plan.progress}
                      size="small"
                      strokeColor="#1677ff"
                      format={(p) => `${p}%`}
                    />
                    <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>触达率 {plan.delivery_rate}%</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>回复率 {plan.reply_rate}%</Text>
                    </div>
                    <Divider style={{ margin: '12px 0 0 0' }} />
                  </div>
                ))}
              </Space>
            )}
          </Card>
        </Col>

        {/* 行业情报 + 最新通知 */}
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
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {MOCK_INTEL.map((article) => (
                  <div key={article.id}>
                    <Space style={{ marginBottom: 4 }}>
                      <Tag color={CATEGORY_COLOR[article.category] ?? 'default'} style={{ fontSize: 11 }}>
                        {article.category}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>{article.published_at}</Text>
                    </Space>
                    <div>
                      <Text strong style={{ fontSize: 13 }}>📰 {article.title}</Text>
                    </div>
                    <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
                      {article.summary.slice(0, 60)}…
                    </Text>
                    <Divider style={{ margin: '10px 0 0 0' }} />
                  </div>
                ))}
              </Space>
            </Card>

            {/* 最新通知 */}
            <Card
              title={
                <Space>
                  <BellOutlined />
                  <Text strong>最新通知</Text>
                  {unreadCount > 0 && <Badge count={unreadCount} />}
                </Space>
              }
            >
              <List
                size="small"
                dataSource={MOCK_NOTIFICATIONS.slice(0, 4)}
                renderItem={(item) => (
                  <List.Item
                    style={{ opacity: item.is_read ? 0.6 : 1 }}
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{item.created_at}</Text>}
                  >
                    <Space>
                      {!item.is_read && <Badge dot />}
                      <Text>{item.title}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Space>
        </Col>
      </Row>
    </Space>
  );
}

Component.displayName = 'DashboardPage';
