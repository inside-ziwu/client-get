import { useState } from 'react';
import {
  Steps,
  Button,
  Form,
  Input,
  Select,
  Radio,
  Checkbox,
  Space,
  Typography,
  Table,
  Tag,
  InputNumber,
  Alert,
  Descriptions,
  message,
  Divider,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const MOCK_GROUPS = [
  { id: 'g1', name: '德国A级客户', count: 45 },
  { id: 'g2', name: '美国PCB采购商', count: 78 },
  { id: 'g3', name: '优先跟进', count: 23 },
  { id: 'g4', name: '日本精密客户', count: 31 },
];

const MOCK_TEMPLATES = [
  { id: 'pt1', name: '首次触达-PCB行业通用', category: '首次触达', subject: 'Inquiry about {{产品标签}} Products' },
  { id: 'ct1', name: '我的跟进模板', category: '跟进', subject: 'Re: {{产品标签}} — Quick Update' },
  { id: 'pt3', name: '促成下单-通用', category: '促成下单', subject: 'Special Offer: {{产品标签}}' },
];

const MOCK_DOMAINS = [
  { id: 'd1', domain: 'mail.xxx.com', stage: 3, remaining: '67/100', verified: true },
  { id: 'd2', domain: 'mx2.xxx.com', stage: null, remaining: '—', verified: false },
];

interface SequenceStep {
  id: string;
  step_number: number;
  condition: string;
  delay_days: number;
  template_id: string;
}

const STEPS = ['基本信息', '收件人', '模板', '策略', '序列', '确认'];

export function Component() {
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);
  const [form] = Form.useForm();
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('pt1');
  const [selectedDomainId, setSelectedDomainId] = useState<string>('d1');
  const [sequence, setSequence] = useState<SequenceStep[]>([
    { id: 's1', step_number: 1, condition: '立即发送', delay_days: 0, template_id: 'pt1' },
    { id: 's2', step_number: 2, condition: '未回复', delay_days: 3, template_id: '' },
    { id: 's3', step_number: 3, condition: '未回复', delay_days: 5, template_id: '' },
  ]);

  const totalSelected = MOCK_GROUPS.filter((g) => selectedGroups.includes(g.id)).reduce((s, g) => s + g.count, 0);
  const excluded = Math.round(totalSelected * 0.12);
  const actualSend = totalSelected - excluded;

  const addSequenceStep = () => {
    setSequence((prev) => [...prev, {
      id: `s${Date.now()}`,
      step_number: prev.length + 1,
      condition: '未回复',
      delay_days: 7,
      template_id: '',
    }]);
  };

  const removeStep = (id: string) => {
    setSequence((prev) => prev.filter((s) => s.id !== id).map((s, i) => ({ ...s, step_number: i + 1 })));
  };

  const seqCols: ColumnsType<SequenceStep> = [
    { title: '序列#', dataIndex: 'step_number', width: 60 },
    {
      title: '触发条件', dataIndex: 'condition', width: 120,
      render: (v, r) => r.step_number === 1 ? <Text type="secondary">立即发送</Text> : (
        <Select value={v} size="small" style={{ width: 110 }}
          onChange={(val) => setSequence(prev => prev.map(s => s.id === r.id ? { ...s, condition: val } : s))}>
          <Option value="未回复">未回复</Option>
          <Option value="未打开">未打开</Option>
          <Option value="已打开">已打开</Option>
        </Select>
      ),
    },
    {
      title: '间隔天数', dataIndex: 'delay_days', width: 100,
      render: (v, r) => r.step_number === 1 ? <Text type="secondary">—</Text> : (
        <InputNumber value={v} min={1} size="small" style={{ width: 80 }}
          onChange={(val) => setSequence(prev => prev.map(s => s.id === r.id ? { ...s, delay_days: val ?? 3 } : s))} />
      ),
    },
    {
      title: '模板', dataIndex: 'template_id',
      render: (v, r) => r.step_number === 1 ? (
        <Tag color="blue">{MOCK_TEMPLATES.find(t => t.id === selectedTemplateId)?.name ?? '(Step 3 选择)'}</Tag>
      ) : (
        <Select value={v || undefined} placeholder="选择模板" size="small" style={{ width: 200 }}
          onChange={(val) => setSequence(prev => prev.map(s => s.id === r.id ? { ...s, template_id: val } : s))}>
          {MOCK_TEMPLATES.map(t => <Option key={t.id} value={t.id}>{t.name}</Option>)}
        </Select>
      ),
    },
    {
      title: '', width: 50,
      render: (_, r) => r.step_number > 1 ? (
        <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => removeStep(r.id)} />
      ) : null,
    },
  ];

  const stepContent = [
    /* Step 1: 基本信息 */
    <Form form={form} layout="vertical" key="step1">
      <Form.Item name="name" label="计划名称" rules={[{ required: true, message: '请输入计划名称' }]}>
        <Input placeholder="如：德国PCB采购商首轮开发" />
      </Form.Item>
      <Form.Item name="description" label="说明备注（选填）">
        <TextArea rows={3} />
      </Form.Item>
    </Form>,

    /* Step 2: 收件人 */
    <Space direction="vertical" style={{ width: '100%' }} size="middle" key="step2">
      <Form layout="vertical">
        <Form.Item label="收件人来源">
          <Radio.Group defaultValue="group">
            <Radio value="group">从群组选择</Radio>
            <Radio value="filter">从公司列表筛选</Radio>
          </Radio.Group>
        </Form.Item>
      </Form>
      <div>
        <Text strong>选择群组：</Text>
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {MOCK_GROUPS.map((g) => (
            <Checkbox
              key={g.id}
              checked={selectedGroups.includes(g.id)}
              onChange={(e) => {
                if (e.target.checked) setSelectedGroups(prev => [...prev, g.id]);
                else setSelectedGroups(prev => prev.filter(id => id !== g.id));
              }}
            >
              {g.name} ({g.count}人)
            </Checkbox>
          ))}
        </div>
      </div>
      {totalSelected > 0 && (
        <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6, padding: 12 }}>
          <Space direction="vertical" size={4}>
            <Text>已选收件人: <Text strong>{totalSelected}</Text> 人</Text>
            <Text type="secondary">自动排除: 黑名单 / 已退订 / 待补全 → {excluded} 人</Text>
            <Text>实际发送: <Text strong style={{ color: '#52c41a' }}>{actualSend}</Text> 人</Text>
          </Space>
        </div>
      )}
    </Space>,

    /* Step 3: 模板 */
    <Space direction="vertical" style={{ width: '100%' }} size="middle" key="step3">
      <Text type="secondary">选择第 1 封邮件模板（后续序列模板在 Step 5 中配置）</Text>
      <Radio.Group value={selectedTemplateId} onChange={(e) => setSelectedTemplateId(e.target.value)} style={{ width: '100%' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          {MOCK_TEMPLATES.map((t) => (
            <div
              key={t.id}
              style={{
                padding: '12px 16px',
                border: `1px solid ${selectedTemplateId === t.id ? '#1677ff' : '#f0f0f0'}`,
                borderRadius: 6,
                background: selectedTemplateId === t.id ? '#e6f4ff' : '#fff',
                cursor: 'pointer',
              }}
              onClick={() => setSelectedTemplateId(t.id)}
            >
              <Space>
                <Radio value={t.id} />
                <div>
                  <Text strong>{t.name}</Text>
                  <Tag color="cyan" style={{ marginLeft: 8, fontSize: 11 }}>{t.category}</Tag>
                  <div><Text type="secondary" style={{ fontSize: 12 }}>{t.subject}</Text></div>
                </div>
              </Space>
            </div>
          ))}
        </Space>
      </Radio.Group>
    </Space>,

    /* Step 4: 发送策略 */
    <Form layout="vertical" key="step4">
      <Form.Item label="目标时区">
        <Select defaultValue="auto" style={{ width: 300 }}>
          <Option value="auto">自动匹配收件人时区</Option>
          <Option value="CET">CET（中欧标准时间）</Option>
          <Option value="EST">EST（美东标准时间）</Option>
          <Option value="JST">JST（日本标准时间）</Option>
        </Select>
      </Form.Item>
      <Form.Item label="发送时段（目标国当地时间）">
        <Space>
          <Select defaultValue={9} style={{ width: 100 }}>
            {Array.from({ length: 24 }, (_, i) => <Option key={i} value={i}>{String(i).padStart(2, '0')}:00</Option>)}
          </Select>
          <Text>~</Text>
          <Select defaultValue={11} style={{ width: 100 }}>
            {Array.from({ length: 24 }, (_, i) => <Option key={i} value={i}>{String(i).padStart(2, '0')}:00</Option>)}
          </Select>
        </Space>
      </Form.Item>
      <Form.Item label="发送间隔（随机）">
        <Space>
          <InputNumber defaultValue={30} min={5} suffix="秒" style={{ width: 110 }} />
          <Text>~</Text>
          <InputNumber defaultValue={120} min={10} suffix="秒" style={{ width: 110 }} />
        </Space>
      </Form.Item>
      <Form.Item label="发送域名" required>
        <Radio.Group value={selectedDomainId} onChange={(e) => setSelectedDomainId(e.target.value)}>
          <Space direction="vertical">
            {MOCK_DOMAINS.map((d) => (
              <Radio key={d.id} value={d.id} disabled={!d.verified}>
                <Space>
                  <Text>{d.domain}</Text>
                  {d.verified ? (
                    <>
                      <Tag color="blue">阶段{d.stage}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>今日剩余: {d.remaining}</Text>
                    </>
                  ) : (
                    <Tag>DNS验证中</Tag>
                  )}
                </Space>
              </Radio>
            ))}
          </Space>
        </Radio.Group>
      </Form.Item>
    </Form>,

    /* Step 5: 序列邮件 */
    <Space direction="vertical" style={{ width: '100%' }} size="middle" key="step5">
      <Alert type="info" showIcon message="收到回复后自动停止该联系人的后续序列邮件" />
      <Table
        rowKey="id"
        columns={seqCols}
        dataSource={sequence}
        size="small"
        pagination={false}
        footer={() => (
          <Button size="small" icon={<PlusOutlined />} onClick={addSequenceStep}>添加序列</Button>
        )}
      />
    </Space>,

    /* Step 6: 确认 */
    <Space direction="vertical" style={{ width: '100%' }} size="large" key="step6">
      <Descriptions bordered column={2} title="发送计划摘要">
        <Descriptions.Item label="计划名称" span={2}>
          {form.getFieldValue('name') || '(未填写)'}
        </Descriptions.Item>
        <Descriptions.Item label="收件人数">
          {actualSend}人（来自 {selectedGroups.length} 个群组）
        </Descriptions.Item>
        <Descriptions.Item label="序列封数">{sequence.length} 封</Descriptions.Item>
        <Descriptions.Item label="发送域名">
          {MOCK_DOMAINS.find(d => d.id === selectedDomainId)?.domain ?? '—'}
        </Descriptions.Item>
        <Descriptions.Item label="时区策略">自动匹配 09:00–11:00</Descriptions.Item>
      </Descriptions>
      <Alert type="warning" showIcon message={'确认后将进入草稿状态，需手动点击"执行"开始发送。'} />
    </Space>,
  ];

  const handleNext = () => {
    if (current === 0) {
      form.validateFields().then(() => setCurrent((c) => c + 1)).catch(() => {});
    } else {
      setCurrent((c) => c + 1);
    }
  };

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/send-plans')}>返回</Button>
        <Title level={4} style={{ margin: 0 }}>新建发送计划</Title>
      </div>

      <Steps current={current} items={STEPS.map((s) => ({ title: s }))} style={{ marginBottom: 32 }} />

      <div style={{ minHeight: 300, marginBottom: 24 }}>
        {stepContent[current]}
      </div>

      <Divider />
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Button disabled={current === 0} icon={<ArrowLeftOutlined />} onClick={() => setCurrent((c) => c - 1)}>
          上一步
        </Button>
        <Space>
          {current === STEPS.length - 1 ? (
            <>
              <Button icon={<SaveOutlined />} onClick={() => { message.success('已保存为草稿'); navigate('/send-plans'); }}>
                保存为草稿
              </Button>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => { message.success('发送计划已创建！'); navigate('/send-plans'); }}
              >
                确认创建
              </Button>
            </>
          ) : (
            <Button type="primary" icon={<ArrowRightOutlined />} onClick={handleNext}>
              下一步
            </Button>
          )}
        </Space>
      </Space>
    </div>
  );
}

Component.displayName = 'SendPlanWizardPage';
