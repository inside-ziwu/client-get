import { useEffect, useState } from 'react';
import {
  Button,
  Drawer,
  Form,
  Input,
  Modal,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { adminApi } from '../../lib/api';
import type { ScoringTemplate as ApiScoringTemplate } from '@shared/api';

const { Text, Title } = Typography;

type TemplateFormValues = {
  name: string;
  industry?: string;
  description?: string;
  dimensions_json: string;
  grade_thresholds_json: string;
  is_active: boolean;
};

const EMPTY_TEMPLATE: TemplateFormValues = {
  name: '',
  industry: '',
  description: '',
  dimensions_json: '[]',
  grade_thresholds_json: '{}',
  is_active: true,
};

function formatJson(value: unknown) {
  return JSON.stringify(value ?? (Array.isArray(value) ? [] : {}), null, 2);
}

function parseJson(text: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }

  return JSON.parse(trimmed);
}

export function Component() {
  const [items, setItems] = useState<ApiScoringTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<ApiScoringTemplate | null>(null);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [versions, setVersions] = useState<ApiScoringTemplate[]>([]);
  const [form] = Form.useForm<TemplateFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.scoringTemplates.list();
      setItems(response.data.data);
    } catch {
      message.error('加载评分模板失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue(EMPTY_TEMPLATE);
    setDrawerOpen(true);
  };

  const openEdit = async (record: ApiScoringTemplate) => {
    setEditing(record);
    try {
      const response = await adminApi.scoringTemplates.detail(record.id);
      const template = response.data.data;
      form.setFieldsValue({
        name: template.name,
        industry: template.industry ?? '',
        description: template.description ?? '',
        dimensions_json: formatJson(template.dimensions ?? []),
        grade_thresholds_json: formatJson(template.grade_thresholds ?? {}),
        is_active: template.is_active ?? true,
      });
      setDrawerOpen(true);
    } catch {
      message.error('模板详情加载失败，请稍后重试');
      setEditing(null);
      return;
    }
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        name: values.name.trim(),
        industry: values.industry?.trim() || undefined,
        description: values.description?.trim() || undefined,
        dimensions: parseJson(values.dimensions_json),
        grade_thresholds: parseJson(values.grade_thresholds_json),
        is_active: values.is_active,
      };

      if (editing) {
        await adminApi.scoringTemplates.update(editing.id, payload);
        message.success('评分模板已更新');
      } else {
        await adminApi.scoringTemplates.create(payload);
        message.success('评分模板已创建');
      }

      setDrawerOpen(false);
      setEditing(null);
      form.resetFields();
      await load();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('JSON 格式不正确');
        return;
      }

      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const openVersions = async (record: ApiScoringTemplate) => {
    setEditing(record);
    setVersionsOpen(true);
    setVersionsLoading(true);
    try {
      const response = await adminApi.scoringTemplates.versions(record.id);
      setVersions(response.data.data);
    } catch {
      message.error('加载版本历史失败');
    } finally {
      setVersionsLoading(false);
    }
  };

  const columns: ColumnsType<ApiScoringTemplate> = [
    { title: '名称', dataIndex: 'name', render: (value) => <Text strong>{value}</Text> },
    { title: '行业', dataIndex: 'industry', width: 140, render: (value) => value ? <Tag color="blue">{value}</Tag> : '—' },
    { title: '维度数', width: 100, render: (_, record) => `${record.dimensions?.length ?? 0} 个` },
    { title: '版本', dataIndex: 'version', width: 90, render: (value) => value ?? '—' },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 90,
      render: (value, record) => (
        <Switch
          checked={Boolean(value)}
          size="small"
          onChange={async (checked) => {
            try {
              await adminApi.scoringTemplates.update(record.id, { is_active: checked });
              message.success('状态已更新');
              await load();
            } catch {
              message.error('状态更新失败');
            }
          }}
        />
      ),
    },
    { title: '更新时间', dataIndex: 'updated_at', width: 180 },
    {
      title: '操作',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => void openEdit(record)}>
            编辑
          </Button>
          <Button type="link" onClick={() => void openVersions(record)}>
            版本
          </Button>
        </Space>
      ),
    },
  ];

  const versionColumns: ColumnsType<ApiScoringTemplate> = [
    { title: '版本', dataIndex: 'version', width: 90 },
    { title: '名称', dataIndex: 'name' },
    { title: '更新时间', dataIndex: 'updated_at', width: 180 },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      render: (value) => (value ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={5} style={{ margin: 0 }}>
            评分模板
          </Title>
          <Text type="secondary">模板列表、启停和版本历史都来自真实接口。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建模板
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={false} />

      <Drawer
        title={editing ? `编辑评分模板 - ${editing.name}` : '新建评分模板'}
        width={720}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={<Button type="primary" loading={saving} onClick={() => void save()}>保存</Button>}
      >
        <Form form={form} layout="vertical" initialValues={EMPTY_TEMPLATE}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="industry" label="行业">
            <Input placeholder="PCB" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="dimensions_json" label="维度 JSON" rules={[{ required: true, message: '请输入维度 JSON' }]}>
            <Input.TextArea rows={8} placeholder='[{"id":"country","name":"国家匹配度","weight":20,"type":"rule"}]' />
          </Form.Item>
          <Form.Item name="grade_thresholds_json" label="等级阈值 JSON" rules={[{ required: true, message: '请输入等级阈值 JSON' }]}>
            <Input.TextArea rows={5} placeholder='{"S":90,"A":80,"B":60,"C":40,"D":0}' />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title={editing ? `版本历史 - ${editing.name}` : '版本历史'}
        open={versionsOpen}
        onCancel={() => setVersionsOpen(false)}
        footer={null}
        width={720}
      >
        <Table
          rowKey={(record) => `${record.id}-${record.version ?? record.updated_at}`}
          columns={versionColumns}
          dataSource={versions}
          loading={versionsLoading}
          pagination={false}
          size="small"
        />
      </Modal>
    </>
  );
}

Component.displayName = 'ScoringTemplatesPage';
