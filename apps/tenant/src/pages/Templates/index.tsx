import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Tabs,
  Drawer,
  Modal,
  Form,
  Input,
  Select,
  Typography,
  Popconfirm,
  message,
  Radio,
  Spin,
  Card,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  RobotOutlined,
  CopyOutlined,
  EditOutlined,
  DeleteOutlined,
  SendOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { AIBalanceGuard } from '@shared/ui';

const { Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface Template {
  id: string;
  name: string;
  category: string;
  source: 'platform' | 'custom';
  subject: string;
  body_preview: string;
  use_count: number;
  is_ai_generated?: boolean;
}

const MOCK_PLATFORM_TEMPLATES: Template[] = [
  { id: 'pt1', name: '首次触达-PCB行业通用', category: '首次触达', source: 'platform', subject: 'Inquiry about {{产品标签}} Products', body_preview: 'Dear {{联系人姓名}},\n\nI am reaching out regarding our {{产品标签}} products and believe there may be a great opportunity for collaboration...', use_count: 128 },
  { id: 'pt2', name: '跟进询价-PCB', category: '跟进', source: 'platform', subject: 'Follow-up: {{产品标签}} Inquiry', body_preview: 'Dear {{联系人姓名}},\n\nI hope this email finds you well. I\'m following up on my previous message regarding {{产品标签}}...', use_count: 67 },
  { id: 'pt3', name: '促成下单-通用', category: '促成下单', source: 'platform', subject: 'Special Offer: {{产品标签}} — Limited Time', body_preview: 'Dear {{联系人姓名}},\n\nWe have a special promotional offer for {{产品标签}} that I\'d like to share with you...', use_count: 34 },
  { id: 'pt4', name: '节日问候-新年', category: '节日问候', source: 'platform', subject: 'Happy New Year from {{公司名称}}', body_preview: 'Dear {{联系人姓名}},\n\nAs we step into the new year, I wanted to take a moment to express our gratitude...', use_count: 215 },
];

const MOCK_CUSTOM_TEMPLATES: Template[] = [
  { id: 'ct1', name: '我的跟进模板', category: '跟进', source: 'custom', subject: 'Re: {{产品标签}} — Quick Update', body_preview: 'Hi {{联系人姓名}},\n\nJust checking in on our previous conversation about {{产品标签}}...', use_count: 12, is_ai_generated: true },
  { id: 'ct2', name: '技术专业开发信', category: '首次触达', source: 'custom', subject: 'Technical Partnership Opportunity — {{产品标签}}', body_preview: 'Dear {{联系人姓名}},\n\nAs a technical specialist in {{产品标签}} manufacturing...', use_count: 5 },
];

const VARIABLES = ['{{公司名称}}', '{{联系人姓名}}', '{{联系人职位}}', '{{产品标签}}'];

const CATEGORY_COLOR: Record<string, string> = {
  '首次触达': 'blue',
  '跟进': 'cyan',
  '促成下单': 'green',
  '节日问候': 'orange',
};

interface AIGenerateResult {
  version: string;
  subject: string;
  body: string;
}

const MOCK_AI_RESULTS: AIGenerateResult[] = [
  { version: 'A', subject: 'Innovative {{产品标签}} Solutions for Your Business', body: 'Dear {{联系人姓名}},\n\nI hope this message finds you well. I am reaching out from {{公司名称}}, a leading manufacturer of {{产品标签}}...' },
  { version: 'B', subject: 'Hi {{联系人姓名}}, Quick Question About Your {{产品标签}} Needs', body: 'Hi {{联系人姓名}},\n\nI came across {{公司名称}} and noticed you work in the {{产品标签}} space...' },
  { version: 'C', subject: '{{产品标签}} Technical Partnership — {{公司名称}}', body: 'Dear {{联系人姓名}},\n\nAs a certified {{产品标签}} specialist, we at {{公司名称}} have been serving global clients since 2005...' },
];

function TemplateEditorDrawer({ template, open, onClose }: { template: Template | null; open: boolean; onClose: () => void }) {
  const [bodyValue, setBodyValue] = useState(template?.body_preview ?? '');
  const insertVar = (v: string) => setBodyValue((prev) => prev + v);

  return (
    <Drawer
      title={template ? `编辑模板 — ${template.name}` : '新建模板'}
      width={640}
      open={open}
      onClose={onClose}
      extra={<Button type="primary" onClick={() => { message.success('模板已保存'); onClose(); }}>保存</Button>}
    >
      <Form layout="vertical" initialValues={{ category: template?.category, name: template?.name, subject: template?.subject }}>
        <Form.Item name="name" label="模板名称" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="category" label="场景标签" rules={[{ required: true }]}>
          <Select>
            <Option value="首次触达">首次触达</Option>
            <Option value="跟进">跟进</Option>
            <Option value="促成下单">促成下单</Option>
            <Option value="节日问候">节日问候</Option>
          </Select>
        </Form.Item>
        <Form.Item name="subject" label="邮件主题" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item label="正文">
          <TextArea
            value={bodyValue}
            onChange={(e) => setBodyValue(e.target.value)}
            rows={12}
            style={{ fontFamily: 'monospace', fontSize: 13 }}
          />
        </Form.Item>
        <Form.Item label="插入变量">
          <Space wrap>
            {VARIABLES.map((v) => (
              <Tag key={v} color="blue" style={{ cursor: 'pointer' }} onClick={() => insertVar(v)}>{v}</Tag>
            ))}
          </Space>
        </Form.Item>
        {bodyValue && (
          <Form.Item label="预览效果">
            <div style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: 12, fontSize: 13, whiteSpace: 'pre-wrap' }}>
              {bodyValue
                .replace(/{{联系人姓名}}/g, 'John Doe')
                .replace(/{{公司名称}}/g, 'ABC Co Ltd')
                .replace(/{{产品标签}}/g, 'FPC PCB')
                .replace(/{{联系人职位}}/g, 'Purchasing Manager')}
            </div>
          </Form.Item>
        )}
      </Form>
    </Drawer>
  );
}

function AIGenerateModal({ open, onClose, balance }: { open: boolean; onClose: () => void; balance: number }) {
  const [step, setStep] = useState<'form' | 'loading' | 'result'>('form');
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);

  const handleGenerate = () => {
    setStep('loading');
    setTimeout(() => setStep('result'), 2000);
  };

  const handleSelect = (version: string) => {
    setSelectedVersion(version);
    message.success(`已选择版本 ${version}，即将进入模板编辑器`);
    onClose();
    setStep('form');
  };

  const handleClose = () => {
    onClose();
    setStep('form');
  };

  return (
    <Modal title="🤖 AI生成邮件模板" open={open} onCancel={handleClose} footer={null} width={700}>
      {step === 'form' && (
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="场景">
            <Select defaultValue="首次触达" style={{ width: '100%' }}>
              <Option value="首次触达">首次触达</Option>
              <Option value="跟进">跟进</Option>
              <Option value="促成下单">促成下单</Option>
              <Option value="节日问候">节日问候</Option>
            </Select>
          </Form.Item>
          <Form.Item label="产品信息（简述你的产品）">
            <TextArea rows={3} placeholder="如：PCB printed circuit board manufacturer, specializing in FPC and HDI boards..." />
          </Form.Item>
          <Form.Item label="语气风格">
            <Radio.Group defaultValue="formal">
              <Radio value="formal">正式商务</Radio>
              <Radio value="friendly">友好轻松</Radio>
              <Radio value="technical">技术专业</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="使用模型">
            <Select defaultValue="deepseek" style={{ width: 200 }}>
              <Option value="deepseek">DeepSeek V3</Option>
              <Option value="gemini">Gemini 2.5</Option>
              <Option value="glm">GLM-5</Option>
            </Select>
          </Form.Item>
          <AIBalanceGuard balance={balance}>
            <Button type="primary" block icon={<RobotOutlined />} onClick={handleGenerate}>
              生成
            </Button>
          </AIBalanceGuard>
        </Form>
      )}

      {step === 'loading' && (
        <div style={{ textAlign: 'center', padding: '48px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">AI 正在生成模板，请稍候…</Text>
          </div>
        </div>
      )}

      {step === 'result' && (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Text>已生成 3 个版本，请选择最适合的：</Text>
          <div style={{ display: 'flex', gap: 12 }}>
            {MOCK_AI_RESULTS.map((r) => (
              <Card
                key={r.version}
                size="small"
                style={{ flex: 1, cursor: 'pointer', border: selectedVersion === r.version ? '2px solid #1677ff' : undefined }}
                hoverable
                actions={[<Button type="link" size="small" onClick={() => handleSelect(r.version)}>选择此版本</Button>]}
              >
                <Text strong>版本 {r.version}</Text>
                <div style={{ marginTop: 6 }}>
                  <Text style={{ fontSize: 12 }}>{r.subject}</Text>
                </div>
                <div style={{ marginTop: 4, fontSize: 11, color: '#999', overflow: 'hidden', maxHeight: 60 }}>
                  {r.body.slice(0, 80)}…
                </div>
              </Card>
            ))}
          </div>
        </Space>
      )}
    </Modal>
  );
}

export function Component() {
  const [activeTab, setActiveTab] = useState('platform');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const AI_BALANCE = 520;

  const openEditor = (t?: Template) => {
    setEditingTemplate(t ?? null);
    setEditorOpen(true);
  };

  const expandedRowRender = (record: Template) => (
    <div style={{ padding: '8px 16px 16px', background: '#fafafa', borderRadius: 4 }}>
      <div style={{ marginBottom: 8 }}>
        <Text type="secondary" style={{ fontSize: 11 }}>主题行</Text>
        <div style={{ marginTop: 2, padding: '6px 10px', background: '#fff', border: '1px solid #f0f0f0', borderRadius: 4, fontSize: 13 }}>
          {record.subject}
        </div>
      </div>
      <div>
        <Text type="secondary" style={{ fontSize: 11 }}>正文预览</Text>
        <div style={{ marginTop: 2, padding: '10px 12px', background: '#fff', border: '1px solid #f0f0f0', borderRadius: 4, fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
          {record.body_preview}
        </div>
      </div>
    </div>
  );

  const platformCols: ColumnsType<Template> = [
    {
      title: '模板名称', dataIndex: 'name',
      render: (v) => <Text strong>{v}</Text>,
    },
    { title: '场景标签', dataIndex: 'category', width: 100, render: (v) => <Tag color={CATEGORY_COLOR[v] ?? 'default'}>{v}</Tag> },
    { title: '使用次数', dataIndex: 'use_count', width: 90 },
    {
      title: '操作', width: 140,
      render: () => (
        <Space>
          <Button type="link" size="small" icon={<SendOutlined />} onClick={() => message.success('已加入发送计划选择')}>使用</Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => message.success('已复制为自有模板')}>复制</Button>
        </Space>
      ),
    },
  ];

  const customCols: ColumnsType<Template> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      render: (v, r) => (
        <Space>
          <Text strong>{v}</Text>
          {r.is_ai_generated && <Tag color="purple" style={{ fontSize: 11 }}>AI生成</Tag>}
        </Space>
      ),
    },
    { title: '场景标签', dataIndex: 'category', width: 100, render: (v) => <Tag color={CATEGORY_COLOR[v] ?? 'default'}>{v}</Tag> },
    { title: '使用次数', dataIndex: 'use_count', width: 90 },
    {
      title: '操作', width: 160,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditor(record)}>编辑</Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => message.success('已复制')}>复制</Button>
          <Popconfirm title="确认删除此模板？" onConfirm={() => message.success('已删除')}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openEditor()}>新建模板</Button>
        <AIBalanceGuard balance={AI_BALANCE}>
          <Button icon={<RobotOutlined />} onClick={() => setAiModalOpen(true)}>AI生成</Button>
        </AIBalanceGuard>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'platform',
            label: `平台官方模板 (${MOCK_PLATFORM_TEMPLATES.length})`,
            children: (
              <Table
                rowKey="id"
                columns={platformCols}
                dataSource={MOCK_PLATFORM_TEMPLATES}
                size="middle"
                pagination={false}
                expandable={{ expandedRowRender }}
              />
            ),
          },
          {
            key: 'custom',
            label: `我的模板 (${MOCK_CUSTOM_TEMPLATES.length})`,
            children: MOCK_CUSTOM_TEMPLATES.length === 0 ? (
              <Empty
                description="还没有自建模板"
                style={{ padding: '48px 0' }}
              >
                <Space>
                  <Button type="primary" onClick={() => openEditor()}>新建模板</Button>
                  <Button icon={<RobotOutlined />} onClick={() => setAiModalOpen(true)}>AI生成</Button>
                </Space>
              </Empty>
            ) : (
              <Table
                rowKey="id"
                columns={customCols}
                dataSource={MOCK_CUSTOM_TEMPLATES}
                size="middle"
                pagination={false}
                expandable={{ expandedRowRender }}
              />
            ),
          },
        ]}
      />

      <TemplateEditorDrawer template={editingTemplate} open={editorOpen} onClose={() => setEditorOpen(false)} />
      <AIGenerateModal open={aiModalOpen} onClose={() => setAiModalOpen(false)} balance={AI_BALANCE} />
    </>
  );
}

Component.displayName = 'TemplatesPage';
