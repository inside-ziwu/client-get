import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  Typography,
  Alert,
  Progress,
} from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;

interface UsageRecord {
  id: string;
  date: string;
  function: string;
  tokens: number;
  model: string;
}

interface RechargeRecord {
  id: string;
  date: string;
  amount: number;
  by: string;
  note: string;
}

const MOCK_USAGE: UsageRecord[] = [
  { id: 'u1', date: '2026-04-17', function: '客户评分分析', tokens: 4200, model: 'DeepSeek V3' },
  { id: 'u2', date: '2026-04-16', function: 'AI 邮件模板生成', tokens: 2100, model: 'DeepSeek V3' },
  { id: 'u3', date: '2026-04-16', function: '情报洞察推送', tokens: 1800, model: 'DeepSeek V3' },
  { id: 'u4', date: '2026-04-15', function: '发送效果分析', tokens: 3100, model: 'Gemini 2.5' },
  { id: 'u5', date: '2026-04-14', function: 'AI 邮件模板生成', tokens: 1900, model: 'DeepSeek V3' },
  { id: 'u6', date: '2026-04-13', function: '客户评分分析', tokens: 5600, model: 'DeepSeek V3' },
];

const MOCK_RECHARGE: RechargeRecord[] = [
  { id: 'r1', date: '2026-04-01', amount: 500, by: '平台管理员', note: '月度额度补充' },
  { id: 'r2', date: '2026-03-01', amount: 500, by: '平台管理员', note: '月度额度补充' },
  { id: 'r3', date: '2026-02-01', amount: 300, by: '平台管理员', note: '初始额度' },
];

const FUNCTION_USAGE = [
  { name: '客户评分分析', tokens: 9800, color: '#1677ff' },
  { name: 'AI 模板生成', tokens: 4000, color: '#52c41a' },
  { name: '情报洞察', tokens: 1800, color: '#faad14' },
  { name: '发送效果分析', tokens: 3100, color: '#722ed1' },
];

const TOTAL_USED = FUNCTION_USAGE.reduce((s, f) => s + f.tokens, 0);
const CURRENT_BALANCE = 520;

export function Component() {
  const usageCols: ColumnsType<UsageRecord> = [
    { title: '日期', dataIndex: 'date', width: 110 },
    { title: '功能', dataIndex: 'function', render: (v) => <Text>{v}</Text> },
    { title: '模型', dataIndex: 'model', width: 130, render: (v) => <Tag>{v}</Tag> },
    {
      title: 'Token 用量', dataIndex: 'tokens', width: 120,
      render: (v) => <Text>{v.toLocaleString()}</Text>,
    },
  ];

  const rechargeCols: ColumnsType<RechargeRecord> = [
    { title: '日期', dataIndex: 'date', width: 110 },
    {
      title: '充值额度', dataIndex: 'amount', width: 120,
      render: (v) => <Text strong style={{ color: '#52c41a' }}>+{v.toLocaleString()} tokens</Text>,
    },
    { title: '操作人', dataIndex: 'by', width: 120 },
    { title: '备注', dataIndex: 'note', render: (v) => <Text type="secondary">{v}</Text> },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Title level={5} style={{ marginBottom: 0 }}>AI 额度</Title>

      {CURRENT_BALANCE < 200 && (
        <Alert
          type="warning"
          showIcon
          message="AI 额度不足 200 tokens，部分 AI 功能即将不可用。请联系平台管理员充值。"
        />
      )}

      {/* 余额概览 */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="当前余额"
              value={CURRENT_BALANCE}
              suffix="tokens"
              valueStyle={{ color: CURRENT_BALANCE < 200 ? '#ff4d4f' : '#1677ff' }}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="本月已用" value={TOTAL_USED} suffix="tokens" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="累计充值" value={1300} suffix="tokens" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="本月剩余天数"
              value={13}
              suffix="天"
            />
          </Card>
        </Col>
      </Row>

      {/* 功能用量分布 */}
      <Card title="功能用量分布（本月）" size="small">
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          {FUNCTION_USAGE.map((f) => (
            <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Text style={{ width: 130, flexShrink: 0, fontSize: 13 }}>{f.name}</Text>
              <Progress
                percent={Math.round((f.tokens / TOTAL_USED) * 100)}
                strokeColor={f.color}
                style={{ flex: 1, marginBottom: 0 }}
                format={(p) => `${p}%`}
              />
              <Text style={{ width: 80, textAlign: 'right', fontSize: 12, flexShrink: 0 }}>
                {f.tokens.toLocaleString()} tokens
              </Text>
            </div>
          ))}
        </Space>
      </Card>

      {/* 使用明细 */}
      <Card title="近期使用明细" size="small">
        <Table
          rowKey="id"
          columns={usageCols}
          dataSource={MOCK_USAGE}
          size="small"
          pagination={{ pageSize: 5, size: 'small' }}
        />
      </Card>

      {/* 充值记录 */}
      <Card title="充值记录" size="small">
        <Table
          rowKey="id"
          columns={rechargeCols}
          dataSource={MOCK_RECHARGE}
          size="small"
          pagination={false}
        />
        <div style={{ marginTop: 12 }}>
          <Alert
            type="info"
            showIcon
            message="如需充值 AI 额度，请联系平台管理员操作。额度由管理员统一管理和分配。"
          />
        </div>
      </Card>
    </Space>
  );
}

Component.displayName = 'AIBalanceSettingsPage';
