import { useEffect, useState } from 'react';
import {
  Button,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import { DeleteOutlined, EditOutlined, ImportOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { adminApi } from '../../lib/api';
import type { IntelligenceSource as ApiIntelligenceSource } from '@shared/api';
import type { ImportResult } from '@shared/types';

const { Text, Title } = Typography;

type SourceFormValues = {
  name: string;
  type: ApiIntelligenceSource['type'];
  url?: string;
  config_json: string;
  is_active: boolean;
};

const EMPTY_SOURCE: SourceFormValues = {
  name: '',
  type: 'rss',
  url: '',
  config_json: '{}',
  is_active: true,
};

const SOURCE_TYPES: Array<{ label: string; value: ApiIntelligenceSource['type'] }> = [
  { label: 'RSS', value: 'rss' },
  { label: '网站', value: 'website' },
  { label: '手工', value: 'manual' },
];

function parseJson(text: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }

  return JSON.parse(trimmed);
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

export function Component() {
  const [items, setItems] = useState<ApiIntelligenceSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<ApiIntelligenceSource | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [form] = Form.useForm<SourceFormValues>();
  const [importForm] = Form.useForm<{ items_json: string }>();

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.intelligenceSources.list();
      setItems(response.data.data);
    } catch {
      message.error('加载情报源失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue(EMPTY_SOURCE);
    setDrawerOpen(true);
  };

  const openEdit = (record: ApiIntelligenceSource) => {
    setEditing(record);
    form.setFieldsValue({
      name: record.name,
      type: record.type,
      url: record.url ?? '',
      config_json: formatJson(record.config ?? {}),
      is_active: record.is_active,
    });
    setDrawerOpen(true);
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        name: values.name.trim(),
        type: values.type,
        url: values.url?.trim() || undefined,
        config: parseJson(values.config_json),
        is_active: values.is_active,
      };

      if (editing) {
        await adminApi.intelligenceSources.update(editing.id, payload);
        message.success('情报源已更新');
      } else {
        await adminApi.intelligenceSources.create(payload);
        message.success('情报源已创建');
      }

      setDrawerOpen(false);
      setEditing(null);
      form.resetFields();
      await load();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('配置 JSON 格式不正确');
        return;
      }

      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const deleteSource = async (id: string) => {
    try {
      await adminApi.intelligenceSources.delete(id);
      message.success('情报源已删除');
      await load();
    } catch {
      message.error('删除失败');
    }
  };

  const saveImport = async () => {
    try {
      const values = await importForm.validateFields();
      const parsed = JSON.parse(values.items_json) as Array<Partial<ApiIntelligenceSource>>;
      if (!Array.isArray(parsed)) {
        throw new Error('invalid');
      }

      setImporting(true);
      const response = await adminApi.intelligenceSources.batchImport(parsed);
      const result = response.data.data as ImportResult;
      message.success(`导入完成：成功 ${result.success} 条，失败 ${result.failed} 条`);
      setImportOpen(false);
      importForm.resetFields();
      await load();
    } catch (error) {
      if (error instanceof SyntaxError || error instanceof Error && error.message === 'invalid') {
        message.error('请粘贴合法的 JSON 数组');
        return;
      }

      message.error('导入失败');
    } finally {
      setImporting(false);
    }
  };

  const columns: ColumnsType<ApiIntelligenceSource> = [
    { title: '名称', dataIndex: 'name', render: (value) => <Text strong>{value}</Text> },
    { title: '类型', dataIndex: 'type', width: 110, render: (value) => <Tag color="blue">{value}</Tag> },
    {
      title: 'URL',
      dataIndex: 'url',
      ellipsis: true,
      render: (value) => value ? <Text style={{ fontSize: 12 }}>{value}</Text> : '—',
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 90,
      render: (value, record) => (
        <Switch
          checked={value}
          size="small"
          onChange={async (checked) => {
            try {
              await adminApi.intelligenceSources.update(record.id, { is_active: checked });
              message.success('状态已更新');
              await load();
            } catch {
              message.error('状态更新失败');
            }
          }}
        />
      ),
    },
    { title: '最后采集', dataIndex: 'last_fetched_at', width: 180, render: (value) => value ?? '从未' },
    { title: '更新时间', dataIndex: 'updated_at', width: 180 },
    {
      title: '操作',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该情报源？" onConfirm={() => void deleteSource(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={5} style={{ margin: 0 }}>
            情报源管理
          </Title>
          <Text type="secondary">仅保留后端支持的来源类型、启停、导入和删除。</Text>
        </div>
        <Space>
          <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
            批量导入
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增情报源
          </Button>
        </Space>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={false} />

      <Drawer
        title={editing ? `编辑情报源 - ${editing.name}` : '新增情报源'}
        width={560}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={<Button type="primary" loading={saving} onClick={() => void save()}>保存</Button>}
      >
        <Form form={form} layout="vertical" initialValues={EMPTY_SOURCE}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="来源类型" rules={[{ required: true, message: '请选择来源类型' }]}>
            <Select options={SOURCE_TYPES} />
          </Form.Item>
          <Form.Item name="url" label="URL">
            <Input placeholder="https://example.com/rss" />
          </Form.Item>
          <Form.Item name="config_json" label="配置 JSON">
            <Input.TextArea rows={8} placeholder='{"category":"行业动态"}' />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title="批量导入情报源"
        open={importOpen}
        onCancel={() => {
          setImportOpen(false);
          importForm.resetFields();
        }}
        onOk={() => void saveImport()}
        confirmLoading={importing}
        okText="开始导入"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Button
            onClick={() => {
              importForm.setFieldsValue({
                items_json: JSON.stringify(
                  [
                    { name: '行业动态 RSS', type: 'rss', url: 'https://example.com/rss', config: {} },
                  ],
                  null,
                  2,
                ),
              });
            }}
          >
            填入示例
          </Button>
          <Form form={importForm} layout="vertical">
            <Form.Item
              name="items_json"
              label="JSON 数组"
              rules={[{ required: true, message: '请粘贴 JSON 数组' }]}
            >
              <Input.TextArea rows={10} placeholder='[{"name":"行业动态 RSS","type":"rss","url":"https://example.com/rss","config":{}}]' />
            </Form.Item>
          </Form>
          <Upload.Dragger beforeUpload={() => false} showUploadList={false} accept=".json,.txt">
            <p className="ant-upload-drag-icon"><ImportOutlined /></p>
            <p>也可以将 JSON 文件内容粘贴到上方</p>
          </Upload.Dragger>
        </Space>
      </Modal>
    </>
  );
}

Component.displayName = 'IntelligenceSourcesPage';
