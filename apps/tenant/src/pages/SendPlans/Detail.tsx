import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Space,
  Typography,
  Progress,
  Statistic,
  Row,
  Col,
  Card,
  Table,
  Tag,
  Popconfirm,
  message,
  Descriptions,
  Alert,
} from 'antd';
import {
  ArrowLeftOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { StatusTag } from '@shared/ui';

const { Text, Title } = Typography;

const MOCK_SEQUENCE = [
  { step: 1, template: '首次触达-PCB通用', sent: 54, opened: 21, clicked: 8, replied: 5, condition: '立即' },
  { step: 2, template: '跟进询价-PCB', sent: 38, opened: 12, clicked: 3, replied: 2, condition: '未回复 3天后' },
  { step: 3, template: '促成下单-通用', sent: 0, opened: 0, clicked: 0, replied: 0, condition: '未回复 5天后' },
];

export function Component() {
  const { id } = useParams();
  const navigate = useNavigate();

  const plan = {
    id,
    name: '德国PCB采购商首轮开发',
    status: 'running' as import('@shared/types').SendingPlanStatus,
    total_recipients: 69,
    sent_count: 54,
    domain: 'mail.xxx.com',
    started_at: '2026-04-10',
    group_name: '德国A级客户',
  };

  const progress = Math.round((plan.sent_count / plan.total_recipients) * 100);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 面包屑 + 操作 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/send-plans')}>
            发送计划
          </Button>
          <Text type="secondary">/</Text>
          <Title level={4} style={{ margin: 0 }}>{plan.name}</Title>
          <StatusTag status={plan.status} />
        </Space>
        <Space>
          {plan.status === 'running' && (
            <Popconfirm title="确认暂停此计划？" onConfirm={() => message.success('已暂停')}>
              <Button icon={<PauseCircleOutlined />}>暂停</Button>
            </Popconfirm>
          )}
          {plan.status === 'paused' && (
            <Popconfirm title="确认恢复此计划？" onConfirm={() => message.success('已恢复')}>
              <Button type="primary" icon={<PlayCircleOutlined />}>恢复</Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      {/* 进度概览 */}
      <Card>
        <div style={{ marginBottom: 12 }}>
          <Space style={{ justifyContent: 'space-between', width: '100%' }}>
            <Text>发送进度: <Text strong>{plan.sent_count}/{plan.total_recipients}人</Text></Text>
            <Text type="secondary">当前序列: 第 2 封</Text>
          </Space>
        </div>
        <Progress percent={progress} strokeColor="#1677ff" />

        <Row gutter={[16, 0]} style={{ marginTop: 20 }}>
          <Col span={6}>
            <Statistic title="已发送" value={127} />
          </Col>
          <Col span={6}>
            <Statistic title="触达" value={121} suffix={<Text type="secondary" style={{ fontSize: 12 }}>(95.3%)</Text>} />
          </Col>
          <Col span={6}>
            <Statistic title="打开" value={28} suffix={<Text type="secondary" style={{ fontSize: 12 }}>(22.0%)</Text>} />
          </Col>
          <Col span={6}>
            <Statistic title="回复" value={5} valueStyle={{ color: '#52c41a' }} suffix={<Text type="secondary" style={{ fontSize: 12 }}>(3.9%)</Text>} />
          </Col>
        </Row>
      </Card>

      {/* 基本信息 */}
      <Descriptions bordered column={3} size="small">
        <Descriptions.Item label="收件人群组">{plan.group_name}</Descriptions.Item>
        <Descriptions.Item label="发送域名">{plan.domain}</Descriptions.Item>
        <Descriptions.Item label="开始时间">{plan.started_at}</Descriptions.Item>
      </Descriptions>

      {/* 序列执行情况 */}
      <div>
        <Title level={5}>序列执行情况</Title>
        <Table
          rowKey="step"
          dataSource={MOCK_SEQUENCE}
          size="middle"
          pagination={false}
          columns={[
            { title: '序列#', dataIndex: 'step', width: 60 },
            { title: '模板', dataIndex: 'template' },
            { title: '触发条件', dataIndex: 'condition', render: (v) => <Tag>{v}</Tag> },
            { title: '已发送', dataIndex: 'sent', width: 80 },
            {
              title: '打开率', width: 80,
              render: (_, r) => r.sent > 0 ? `${Math.round((r.opened / r.sent) * 100)}%` : '—',
            },
            {
              title: '点击率', width: 80,
              render: (_, r) => r.sent > 0 ? `${Math.round((r.clicked / r.sent) * 100)}%` : '—',
            },
            {
              title: '回复率', width: 80,
              render: (_, r) => r.sent > 0 ? (
                <Text style={{ color: '#52c41a' }}>{Math.round((r.replied / r.sent) * 100)}%</Text>
              ) : '—',
            },
          ]}
        />
      </div>

      {/* 执行中可编辑提示 */}
      {plan.status === 'running' && (
        <Alert
          type="info"
          showIcon
          message="执行中可操作"
          description="可追加收件人（新增群组成员）或修改未来序列的模板。已发送内容和发送策略不可修改。"
        />
      )}
    </Space>
  );
}

Component.displayName = 'SendPlanDetailPage';
