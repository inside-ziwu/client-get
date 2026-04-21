import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Drawer,
  Form,
  Input,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
  Popconfirm,
} from 'antd';
import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  createAdminApi,
  createApiClient,
  type PlatformEmailTemplate,
} from '@shared/api';

const { Text, Title } = Typography;
const adminApi = createAdminApi(createApiClient('admin'));

type TemplateFormValues = {
  name: string;
  subject: string;
  category: string;
  body_html: string;
  variables_text: string;
  is_active: boolean;
};

const EMPTY_TEMPLATE: TemplateFormValues = {
  name: '',
  subject: '',
  category: '',
  body_html: '',
  variables_text: '',
  is_active: true,
};

function variablesToText(items: PlatformEmailTemplate['variables']) {
  return items.map((item) => `${item.name},${item.label}`).join('\n');
}

function textToVariables(text: string) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, ...rest] = line.split(',');
      const normalizedName = (name ?? '').trim();
      return {
        name: normalizedName,
        label: rest.join(',').trim() || normalizedName,
      };
    })
    .filter((item) => item.name);
}

export function Component() {
  const [items, setItems] = useState<PlatformEmailTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<PlatformEmailTemplate | null>(null);
  const [form] = Form.useForm<TemplateFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.emailTemplates.list();
      setItems(response.data.data);
    } catch {
      message.error('加载邮件模板失败');
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

  const openEdit = (record: PlatformEmailTemplate) => {
    setEditing(record);
    form.setFieldsValue({
      name: record.name,
      subject: record.subject,
      category: record.category,
      body_html: record.body_html,
      variables_text: variablesToText(record.variables),
      is_active: record.is_active,
    });
    setDrawerOpen(true);
  };

  const onSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        name: values.name,
        subject: values.subject,
        category: values.category,
        body_html: values.body_html,
        variables: textToVariables(values.variables_text),
        is_active: values.is_active,
      };

      if (editing) {
        const response = await adminApi.emailTemplates.update(editing.id, payload);
        setItems((prev) => prev.map((item) => (item.id === editing.id ? response.data.data : item)));
      } else {
        const response = await adminApi.emailTemplates.create(payload);
        setItems((prev) => [response.data.data, ...prev]);
      }

      message.success('模板已保存');
      setDrawerOpen(false);
      setEditing(null);
      form.resetFields();
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (id: string) => {
    try {
      await adminApi.emailTemplates.delete(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      message.success('模板已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<PlatformEmailTemplate> = useMemo(
    () => [
      { title: '名称', dataIndex: 'name', render: (value) => <Text strong>{value}</Text> },
      { title: '分类', dataIndex: 'category', render: (value) => <Tag color="blue">{value}</Tag> },
      { title: '主题', dataIndex: 'subject', ellipsis: true },
      {
        title: '状态',
        dataIndex: 'is_active',
        width: 90,
        render: (value) => (value ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
      },
      { title: '更新时间', dataIndex: 'updated_at', width: 180 },
      {
        title: '操作',
        width: 150,
        render: (_, record) => (
          <Space>
            <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
              编辑
            </Button>
            <Popconfirm title="确认删除该模板？" onConfirm={() => void onDelete(record.id)}>
              <Button type="link" danger>
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [items],
  );

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>
            邮件模板
          </Title>
          <Text type="secondary">模板数据来自后端接口，可直接新增、编辑和删除。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建模板
        </Button>
      </div>

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={items}
          pagination={false}
        />
      </Card>

      <Drawer
        title={editing ? '编辑邮件模板' : '新建邮件模板'}
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={<Button type="primary" loading={saving} onClick={() => void onSave()}>保存</Button>}
      >
        <Form layout="vertical" form={form} initialValues={EMPTY_TEMPLATE}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true, message: '请输入分类' }]}>
            <Input placeholder="如：首次触达 / 跟进 / 节日问候" />
          </Form.Item>
          <Form.Item name="subject" label="主题" rules={[{ required: true, message: '请输入主题' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="body_html" label="正文 HTML" rules={[{ required: true, message: '请输入正文' }]}>
            <Input.TextArea rows={12} placeholder="<p>Hello {{name}}</p>" />
          </Form.Item>
          <Form.Item name="variables_text" label="变量列表">
            <Input.TextArea rows={4} placeholder="company_name,公司名称&#10;contact_name,联系人姓名" />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>
    </Space>
  );
}

Component.displayName = 'EmailTemplatesPage';
