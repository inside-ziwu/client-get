import { useEffect, useState } from 'react';
import {
  Button,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { adminApi } from '../../lib/api';
import type {
  DataSource as ApiDataSource,
  DataSourceCredential as ApiDataSourceCredential,
} from '@shared/api';

const { Text } = Typography;

type SourceFormValues = {
  source_type: string;
  name: string;
  alias_code?: string;
  purpose?: string;
  config_json: string;
};

type CredentialFormValues = {
  account_label?: string;
  is_active: boolean;
};

const EMPTY_SOURCE: SourceFormValues = {
  source_type: '',
  name: '',
  alias_code: '',
  purpose: '',
  config_json: '{}',
};

const EMPTY_CREDENTIAL: CredentialFormValues = {
  account_label: '',
  is_active: true,
};

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
  const [items, setItems] = useState<ApiDataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<ApiDataSource | null>(null);
  const [credentialsOpen, setCredentialsOpen] = useState(false);
  const [credentialsLoading, setCredentialsLoading] = useState(false);
  const [credentials, setCredentials] = useState<ApiDataSourceCredential[]>([]);
  const [editingCredential, setEditingCredential] = useState<ApiDataSourceCredential | null>(null);
  const [credentialDrawerOpen, setCredentialDrawerOpen] = useState(false);
  const [sourceForm] = Form.useForm<SourceFormValues>();
  const [credentialForm] = Form.useForm<CredentialFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.dataSources.list();
      setItems(response.data.data);
    } catch {
      message.error('加载数据源失败');
    } finally {
      setLoading(false);
    }
  };

  const loadCredentials = async (sourceType: string) => {
    setCredentialsLoading(true);
    try {
      const response = await adminApi.dataSources.getCredentials(sourceType);
      setCredentials(response.data.data);
    } catch {
      message.error('加载凭证失败');
    } finally {
      setCredentialsLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    sourceForm.setFieldsValue(EMPTY_SOURCE);
    setDrawerOpen(true);
  };

  const openEdit = (record: ApiDataSource) => {
    setEditing(record);
    sourceForm.setFieldsValue({
      source_type: record.source_type,
      name: record.name,
      alias_code: record.alias_code ?? '',
      purpose: record.purpose ?? '',
      config_json: formatJson(record.config ?? {}),
    });
    setDrawerOpen(true);
  };

  const openCredentials = async (record: ApiDataSource) => {
    setEditing(record);
    setEditingCredential(null);
    setCredentialsOpen(true);
    credentialForm.setFieldsValue(EMPTY_CREDENTIAL);
    await loadCredentials(record.source_type);
  };

  const openCreateCredential = () => {
    setEditingCredential(null);
    credentialForm.setFieldsValue(EMPTY_CREDENTIAL);
    setCredentialDrawerOpen(true);
  };

  const openEditCredential = (record: ApiDataSourceCredential) => {
    setEditingCredential(record);
    credentialForm.setFieldsValue({
      account_label: record.account_label ?? '',
      is_active: record.is_active,
    });
    setCredentialDrawerOpen(true);
  };

  const saveSource = async () => {
    try {
      const values = await sourceForm.validateFields();
      setSaving(true);
      const payload = {
        source_type: values.source_type.trim(),
        name: values.name.trim(),
        alias_code: values.alias_code?.trim() || undefined,
        purpose: values.purpose?.trim() || undefined,
        config: parseJson(values.config_json),
      };

      if (editing) {
        await adminApi.dataSources.update(editing.source_type, payload);
        message.success('数据源已更新');
      } else {
        await adminApi.dataSources.create(payload);
        message.success('数据源已创建');
      }

      setDrawerOpen(false);
      setEditing(null);
      sourceForm.resetFields();
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

  const saveCredential = async () => {
    if (!editing) {
      return;
    }

    try {
      const values = await credentialForm.validateFields();
      const payload = {
        account_label: values.account_label?.trim() || undefined,
        is_active: values.is_active,
      };

      if (editingCredential) {
        await adminApi.dataSources.updateCredential(editing.source_type, editingCredential.id, payload);
        message.success('凭证已更新');
      } else {
        await adminApi.dataSources.createCredential(editing.source_type, payload);
        message.success('凭证已创建');
      }

      setCredentialDrawerOpen(false);
      setEditingCredential(null);
      credentialForm.resetFields();
      await loadCredentials(editing.source_type);
    } catch {
      message.error('保存凭证失败');
    }
  };

  const deleteCredential = async (id: string) => {
    if (!editing) {
      return;
    }

    try {
      await adminApi.dataSources.deleteCredential(editing.source_type, id);
      message.success('凭证已删除');
      await loadCredentials(editing.source_type);
    } catch {
      message.error('删除失败');
    }
  };

  const sourceColumns: ColumnsType<ApiDataSource> = [
    { title: '名称', dataIndex: 'name', render: (value) => <Text strong>{value}</Text> },
    { title: '类型', dataIndex: 'source_type', width: 180, render: (value) => <Tag color="blue">{value}</Tag> },
    { title: '别名编码', dataIndex: 'alias_code', width: 160, render: (value) => value ? <Tag>{value}</Tag> : '—' },
    { title: '用途', dataIndex: 'purpose', ellipsis: true, render: (value) => value ?? '—' },
    {
      title: '操作',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button type="link" onClick={() => void openCredentials(record)}>
            凭证
          </Button>
        </Space>
      ),
    },
  ];

  const credentialColumns: ColumnsType<ApiDataSourceCredential> = [
    { title: '账号标签', dataIndex: 'account_label', render: (value, record) => value ?? record.id },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      render: (value, record) => (
        <Switch
          checked={value}
          size="small"
          onChange={async (checked) => {
            if (!editing) {
              return;
            }

            try {
              await adminApi.dataSources.updateCredential(editing.source_type, record.id, {
                account_label: record.account_label,
                is_active: checked,
              });
              message.success('状态已更新');
              await loadCredentials(editing.source_type);
            } catch {
              message.error('状态更新失败');
            }
          }}
        />
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180 },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEditCredential(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该凭证？" onConfirm={() => void deleteCredential(record.id)}>
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
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增数据源
        </Button>
      </div>

      <Table rowKey="id" columns={sourceColumns} dataSource={items} loading={loading} pagination={false} />

      <Drawer
        title={editing ? `编辑数据源 - ${editing.name}` : '新增数据源'}
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={<Button type="primary" loading={saving} onClick={() => void saveSource()}>保存</Button>}
      >
        <Form form={sourceForm} layout="vertical" initialValues={EMPTY_SOURCE}>
          <Form.Item name="source_type" label="数据源类型" rules={[{ required: true, message: '请输入数据源类型' }]}>
            <Input placeholder="waimao_tong" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="alias_code" label="别名编码">
            <Input placeholder="trade_data" />
          </Form.Item>
          <Form.Item name="purpose" label="用途说明">
            <Input placeholder="公司信息搜索" />
          </Form.Item>
          <Form.Item name="config_json" label="配置 JSON">
            <Input.TextArea rows={8} placeholder='{"region":"cn"}' />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title={editing ? `凭证管理 - ${editing.name}` : '凭证管理'}
        open={credentialsOpen}
        onCancel={() => {
          setCredentialsOpen(false);
          setEditing(null);
          setEditingCredential(null);
          setCredentials([]);
          credentialForm.resetFields();
        }}
        footer={null}
        width={760}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateCredential} disabled={!editing}>
            新建凭证
          </Button>

          <Table
            rowKey="id"
            columns={credentialColumns}
            dataSource={credentials}
            loading={credentialsLoading}
            pagination={false}
            size="small"
          />
        </Space>
      </Modal>

      <Drawer
        title={editingCredential ? '编辑凭证' : '新建凭证'}
        width={420}
        open={credentialDrawerOpen}
        onClose={() => {
          setCredentialDrawerOpen(false);
          setEditingCredential(null);
          credentialForm.resetFields();
        }}
        extra={<Button type="primary" onClick={() => void saveCredential()}>保存</Button>}
      >
        <Form form={credentialForm} layout="vertical" initialValues={EMPTY_CREDENTIAL}>
          <Form.Item name="account_label" label="账号标签">
            <Input />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>
    </>
  );
}

Component.displayName = 'DataSourcesPage';
