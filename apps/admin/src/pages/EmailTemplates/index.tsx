import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Drawer,
  Form,
  Input,
  Select,
  Typography,
  message,
} from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface PlatformTemplate {
  id: string;
  name: string;
  category: string;
  industry: string;
  subject: string;
  body_preview: string;
  use_count: number;
}

const MOCK_TEMPLATES: PlatformTemplate[] = [
  { id: 'pt1', name: '首次触达-PCB行业通用', category: '首次触达', industry: 'PCB', subject: 'Inquiry about {{产品标签}} Products', body_preview: 'Dear {{联系人姓名}},\n\nI am reaching out regarding our {{产品标签}} products...', use_count: 128 },
  { id: 'pt2', name: '跟进询价-PCB', category: '跟进', industry: 'PCB', subject: 'Follow-up: {{产品标签}} Inquiry', body_preview: 'Dear {{联系人姓名}},\n\nI hope this email finds you well. I\'m following up on...', use_count: 67 },
  { id: 'pt3', name: '促成下单-通用', category: '促成下单', industry: 'PCB', subject: 'Special Offer: {{产品标签}}', body_preview: 'Dear {{联系人姓名}},\n\nWe have a special promotional offer...', use_count: 34 },
  { id: 'pt4', name: '节日问候-元旦', category: '节日问候', industry: '通用', subject: 'Happy New Year from {{公司名称}}', body_preview: 'Dear {{联系人姓名}},\n\nWishing you a prosperous New Year...', use_count: 215 },
];

const VARIABLES = ['{{公司名称}}', '{{联系人姓名}}', '{{联系人职位}}', '{{产品标签}}'];

function TemplateEditor({ template, onClose }: { template: PlatformTemplate | null; onClose: () => void }) {
  const [form] = Form.useForm();
  const [bodyValue, setBodyValue] = useState(template?.body_preview ?? '');

  const insertVariable = (variable: string) => {
    setBodyValue((prev) => prev + variable);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        name: template?.name,
        category: template?.category,
        industry: template?.industry,
        subject: template?.subject,
        body_html: template?.body_preview,
      }}
    >
      <Form.Item name="category" label="场景标签" rules={[{ required: true }]}>
        <Select>
          <Option value="首次触达">首次触达</Option>
          <Option value="跟进">跟进</Option>
          <Option value="促成下单">促成下单</Option>
          <Option value="节日问候">节日问候</Option>
        </Select>
      </Form.Item>
      <Form.Item name="industry" label="行业" rules={[{ required: true }]}>
        <Select>
          <Option value="PCB">PCB</Option>
          <Option value="电子元器件">电子元器件</Option>
          <Option value="通用">通用</Option>
        </Select>
      </Form.Item>
      <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item name="subject" label="邮件主题" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item label="正文">
        <TextArea
          value={bodyValue}
          onChange={(e) => setBodyValue(e.target.value)}
          rows={10}
          style={{ fontFamily: 'monospace', fontSize: 13 }}
        />
      </Form.Item>
      <Form.Item label="可插入变量">
        <Space wrap>
          {VARIABLES.map((v) => (
            <Tag
              key={v}
              color="blue"
              style={{ cursor: 'pointer' }}
              onClick={() => insertVariable(v)}
            >
              {v}
            </Tag>
          ))}
        </Space>
      </Form.Item>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <Button onClick={onClose}>取消</Button>
        <Button type="primary" onClick={() => { message.success('模板已保存'); onClose(); }}>保存</Button>
      </div>
    </Form>
  );
}

export function Component() {
  const [editingTemplate, setEditingTemplate] = useState<PlatformTemplate | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [industryFilter, setIndustryFilter] = useState<string | undefined>(undefined);

  const filtered = industryFilter
    ? MOCK_TEMPLATES.filter((t) => t.industry === industryFilter)
    : MOCK_TEMPLATES;

  const columns: ColumnsType<PlatformTemplate> = [
    { title: '模板名称', dataIndex: 'name', render: (v) => <Text strong>{v}</Text> },
    { title: '场景标签', dataIndex: 'category', render: (v) => <Tag color="cyan">{v}</Tag> },
    { title: '行业', dataIndex: 'industry', render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '使用次数', dataIndex: 'use_count', width: 90 },
    {
      title: '操作', width: 80,
      render: (_, record) => (
        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => { setEditingTemplate(record); setDrawerOpen(true); }}>
          编辑
        </Button>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
        <Text>行业筛选：</Text>
        <Select
          placeholder="全部行业"
          style={{ width: 160 }}
          allowClear
          value={industryFilter}
          onChange={setIndustryFilter}
        >
          <Option value="PCB">PCB</Option>
          <Option value="电子元器件">电子元器件</Option>
          <Option value="通用">通用</Option>
        </Select>
        <Button type="primary" icon={<PlusOutlined />} style={{ marginLeft: 'auto' }} onClick={() => { setEditingTemplate(null); setDrawerOpen(true); }}>
          新建模板
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={filtered} size="middle" />

      <Drawer
        title={editingTemplate ? `编辑模板 — ${editingTemplate.name}` : '新建模板'}
        width={620}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={null}
      >
        <TemplateEditor template={editingTemplate} onClose={() => setDrawerOpen(false)} />
      </Drawer>
    </>
  );
}

Component.displayName = 'EmailTemplatesPage';
