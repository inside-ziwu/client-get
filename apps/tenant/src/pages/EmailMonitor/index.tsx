import { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Select,
  DatePicker,
  Space,
  Typography,
  Button,
  Spin,
  Alert,
  Form,
} from 'antd';
import {
  RobotOutlined,
  FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { AIBalanceGuard } from '@shared/ui';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface AIInsight {
  text: string;
}

const MOCK_AI_INSIGHTS: AIInsight[] = [
  { text: '德国打开率35%高于全局平均22%，建议增加德国客户在后续计划中的比例' },
  { text: '周二上午9-11点打开率最高（28.3%），建议集中安排该时段发送' },
  { text: '模板A回复率4.5%优于模板B的2.1%，后续跟进序列推荐优先使用模板A' },
];

const SimpleBarChart = ({ data }: { data: { label: string; value: number; color?: string }[] }) => {
  const max = Math.max(...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minHeight: 140, justifyContent: 'center' }}>
      {data.map((d) => (
        <div key={d.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text style={{ width: 70, fontSize: 12, textAlign: 'right', flexShrink: 0 }}>{d.label}</Text>
          <div style={{ flex: 1, background: '#f0f0f0', borderRadius: 4, height: 18, overflow: 'hidden' }}>
            <div style={{
              width: max > 0 ? `${(d.value / max) * 100}%` : '0%',
              background: d.color ?? '#1677ff',
              height: '100%',
              borderRadius: 4,
              transition: 'width 0.5s ease',
            }} />
          </div>
          <Text style={{ width: 40, fontSize: 12, flexShrink: 0 }}>{d.value}%</Text>
        </div>
      ))}
    </div>
  );
};

const TREND_VALUES = [45, 62, 38, 71, 55, 83, 67, 90, 72, 58, 95, 78, 88, 102];
const TREND_DATES = TREND_VALUES.map((_, i) => `4/${i + 4}`);

const SimpleTrend = () => {
  const max = Math.max(...TREND_VALUES);
  return (
    <div style={{ minHeight: 140 }}>
      {/* 柱状区域 */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 110 }}>
        {TREND_VALUES.map((v, i) => (
          <div key={i} style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end' }}>
            <div style={{
              width: '100%',
              background: '#1677ff',
              borderRadius: '2px 2px 0 0',
              height: `${(v / max) * 100}%`,
              opacity: 0.8,
            }} />
          </div>
        ))}
      </div>
      {/* X 轴标签行，与柱区同列对齐 */}
      <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
        {TREND_DATES.map((d, i) => (
          <div key={i} style={{ flex: 1, textAlign: 'center' }}>
            {i % 3 === 0 && (
              <Text style={{ fontSize: 10, color: '#999' }}>{d}</Text>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export function Component() {
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiResult, setAiResult] = useState<AIInsight[] | null>(null);
  const AI_BALANCE = 520;

  const handleAIAnalyze = () => {
    setAiAnalyzing(true);
    setAiResult(null);
    setTimeout(() => {
      setAiAnalyzing(false);
      setAiResult(MOCK_AI_INSIGHTS);
    }, 2000);
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 执行状态概览 */}
      <div>
        <Title level={5} style={{ marginBottom: 12 }}>执行状态</Title>
        <Row gutter={[12, 12]}>
          {[
            { title: '总发送量', value: 1247 },
            { title: '今日发送', value: 45 },
            { title: '发送进度', value: '78%' },
            { title: '成功率', value: '97.2%' },
            { title: '退信率', value: '1.8%' },
          ].map((s) => (
            <Col span={4} key={s.title}>
              <Card size="small"><Statistic title={s.title} value={s.value} /></Card>
            </Col>
          ))}
          <Col span={4}>
            <Card size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>域名剩余</Text>
              <div style={{ marginTop: 4 }}>
                <Text strong>67/100</Text>
                <div><Text type="secondary" style={{ fontSize: 11 }}>mail.xxx.com</Text></div>
              </div>
            </Card>
          </Col>
        </Row>
      </div>

      {/* 效果指标 */}
      <div>
        <Title level={5} style={{ marginBottom: 12 }}>效果指标</Title>
        <Row gutter={[12, 12]}>
          {[
            { title: '触达率', value: '95.2%' },
            { title: '打开率', value: '22.5%' },
            { title: '点击率', value: '5.3%' },
            { title: '回复率', value: '3.2%', highlight: true },
            { title: '退订率', value: '0.1%' },
          ].map((s) => (
            <Col span={4} key={s.title}>
              <Card size="small">
                <Statistic
                  title={s.title}
                  value={s.value}
                  valueStyle={s.highlight ? { color: '#52c41a' } : undefined}
                />
              </Card>
            </Col>
          ))}
        </Row>
      </div>

      {/* 筛选面板 */}
      <Card size="small">
        <Form layout="inline" style={{ rowGap: 8 }}>
          <Form.Item label="时间范围">
            <RangePicker style={{ width: 240 }} />
          </Form.Item>
          <Form.Item label="发送计划">
            <Select placeholder="全部" style={{ width: 180 }} allowClear>
              <Option value="p1">德国PCB采购商首轮开发</Option>
              <Option value="p2">美国电路板供应商触达</Option>
            </Select>
          </Form.Item>
          <Form.Item label="评级">
            <Select mode="multiple" placeholder="全部" style={{ width: 180 }} allowClear>
              {['S', 'A', 'B', 'C', 'D'].map(g => <Option key={g} value={g}>{g}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item label="国家">
            <Select mode="multiple" placeholder="全部" style={{ width: 160 }} allowClear>
              <Option value="DE">德国</Option>
              <Option value="US">美国</Option>
              <Option value="JP">日本</Option>
            </Select>
          </Form.Item>
          <Form.Item label="模板">
            <Select placeholder="全部" style={{ width: 180 }} allowClear>
              <Option value="pt1">首次触达-PCB通用</Option>
              <Option value="ct1">我的跟进模板</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" icon={<FilterOutlined />}>筛选</Button>
              <Button icon={<ReloadOutlined />}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* 图表区 */}
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="发送量趋势（近14天）" size="small">
            <SimpleTrend />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="模板效果对比（打开率）" size="small">
            <SimpleBarChart data={[
              { label: '首次触达', value: 22 },
              { label: '跟进模板', value: 18 },
              { label: '促成下单', value: 15 },
              { label: '节日问候', value: 35, color: '#faad14' },
            ]} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="评级响应率对比（回复率）" size="small">
            <SimpleBarChart data={[
              { label: 'S级', value: 8, color: '#faad14' },
              { label: 'A级', value: 5, color: '#52c41a' },
              { label: 'B级', value: 3, color: '#1677ff' },
              { label: 'C级', value: 1, color: '#fa8c16' },
              { label: 'D级', value: 0, color: '#d9d9d9' },
            ]} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="序列阶段对比（打开率）" size="small">
            <SimpleBarChart data={[
              { label: '第1封', value: 22 },
              { label: '第2封', value: 18 },
              { label: '第3封', value: 12 },
            ]} />
          </Card>
        </Col>
      </Row>

      {/* AI 分析 */}
      <Card
        title={
          <Space>
            <RobotOutlined />
            <Text strong>AI 智能分析</Text>
          </Space>
        }
        extra={
          <AIBalanceGuard balance={AI_BALANCE}>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              loading={aiAnalyzing}
              onClick={handleAIAnalyze}
            >
              {aiAnalyzing ? '分析中…' : 'AI分析'}
            </Button>
          </AIBalanceGuard>
        }
      >
        {aiAnalyzing && (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <Spin />
            <div style={{ marginTop: 12 }}>
              <Text type="secondary">AI 正在分析发送数据，请稍候…</Text>
            </div>
          </div>
        )}
        {!aiAnalyzing && !aiResult && (
          <Text type="secondary">点击"AI分析"获取智能洞察和优化建议</Text>
        )}
        {aiResult && (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {aiResult.map((insight, i) => (
              <Alert
                key={i}
                type="info"
                showIcon
                message={insight.text}
              />
            ))}
          </Space>
        )}
      </Card>
    </Space>
  );
}

Component.displayName = 'EmailMonitorPage';
