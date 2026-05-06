import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Card,
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
  message,
} from 'antd';
import { EditOutlined, EyeOutlined, PlusOutlined } from '@ant-design/icons';
import { formatDateTime } from '../../lib/format';
import type { ColumnsType } from 'antd/es/table';
import {
  createAdminApi,
  createApiClient,
  type PlatformEmailTemplate,
} from '@shared/api';
import GrapesEmailEditor, { type GrapesEmailEditorRef } from '../../components/GrapesEmailEditor';

const { Text, Title } = Typography;
const adminApi = createAdminApi(createApiClient('admin'));

// ─── Predefined variables ────────────────────────────────────────────────────
const SYSTEM_VARIABLES = [
  { name: 'company_name', label: '公司名称' },
  { name: 'contact_name', label: '联系人姓名' },
  { name: 'contact_email', label: '联系人邮箱' },
  { name: 'contact_title', label: '联系人职位' },
  { name: 'sender_name', label: '发件人姓名' },
  { name: 'sender_company', label: '发件人公司' },
  { name: 'sender_title', label: '发件人职位' },
  { name: 'sender_email', label: '发件人邮箱' },
  { name: 'product_name', label: '产品名称' },
  { name: 'website', label: '官网链接' },
  { name: 'unsubscribe_link', label: '退订链接' },
];

type EditMode = 'visual' | 'html';

type TemplateFormValues = {
  name: string;
  industry: string;
  subject: string;
  category: string;
  body_html: string;
  variable_names: string[];
  is_active: boolean;
};

const EMPTY_TEMPLATE: TemplateFormValues = {
  name: '',
  industry: '',
  subject: '',
  category: '',
  body_html: '',
  variable_names: [],
  is_active: true,
};

export function Component() {
  const [items, setItems] = useState<PlatformEmailTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<PlatformEmailTemplate | null>(null);
  const [editMode, setEditMode] = useState<EditMode>('visual');
  const [currentDesign, setCurrentDesign] = useState<unknown>(null);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [form] = Form.useForm<TemplateFormValues>();
  const grapesRef = useRef<GrapesEmailEditorRef>(null);

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
    setCurrentDesign(null);
    setEditMode('visual');
    form.setFieldsValue(EMPTY_TEMPLATE);
    setDrawerOpen(true);
  };

  const openEdit = (record: PlatformEmailTemplate) => {
    setEditing(record);
    setCurrentDesign(record.body_design ?? null);
    setEditMode(record.body_design ? 'visual' : 'html');
    form.setFieldsValue({
      name: record.name,
      industry: record.industry ?? '',
      subject: record.subject,
      category: record.category,
      body_html: record.body_html,
      variable_names: (record.variables ?? []).map((v) => v.name),
      is_active: record.is_active,
    });
    setDrawerOpen(true);
  };

  const onSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const variables = SYSTEM_VARIABLES.filter((v) =>
        (values.variable_names ?? []).includes(v.name),
      );

      let body_html: string;
      let body_design: unknown;

      if (editMode === 'visual' && grapesRef.current) {
        body_html = grapesRef.current.getHtml();
        body_design = grapesRef.current.getDesign();
      } else {
        body_html = values.body_html;
        body_design = null;
      }

      const payload = {
        name: values.name,
        industry: values.industry.trim() || 'general',
        subject: values.subject,
        category: values.category,
        body_html,
        body_design,
        variables,
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
      setCurrentDesign(null);
      form.resetFields();
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (error as any)?.response?.data?.detail ?? (error as any)?.message ?? '未知错误';
      message.error(`保存失败：${detail}`);
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

  const openPreview = () => {
    if (editMode === 'visual' && grapesRef.current) {
      setPreviewHtml(grapesRef.current.getHtml());
    } else {
      setPreviewHtml(form.getFieldValue('body_html') as string);
    }
  };

  const columns: ColumnsType<PlatformEmailTemplate> = useMemo(
    () => [
      { title: '名称', dataIndex: 'name', render: (value) => <Text strong>{value}</Text> },
      { title: '分类', dataIndex: 'category', render: (value) => <Tag color="blue">{value}</Tag> },
      { title: '主题', dataIndex: 'subject', ellipsis: true },
      {
        title: '编辑器',
        width: 100,
        render: (_, record) =>
          record.body_design ? <Tag color="purple">可视化</Tag> : <Tag>HTML</Tag>,
      },
      {
        title: '状态',
        dataIndex: 'is_active',
        width: 90,
        render: (value) => (value ? <Tag color="green">启用</Tag> : <Tag>停用</Tag>),
      },
      { title: '更新时间', dataIndex: 'updated_at', width: 180, render: (v) => formatDateTime(v as string) },
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        width={editMode === 'visual' ? 1100 : 720}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setEditing(null);
          setCurrentDesign(null);
          form.resetFields();
        }}
        extra={
          <Space>
            <Button icon={<EyeOutlined />} onClick={openPreview}>
              预览
            </Button>
            <Button
              onClick={() => setEditMode((m) => (m === 'visual' ? 'html' : 'visual'))}
            >
              {editMode === 'visual' ? '切换 HTML 源码' : '切换可视化编辑器'}
            </Button>
            <Button type="primary" loading={saving} onClick={() => void onSave()}>
              保存
            </Button>
          </Space>
        }
      >
        <Form layout="vertical" form={form} initialValues={EMPTY_TEMPLATE}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="industry" label="行业（用于新租户自动复制）">
            <Input placeholder="PCB / 通用" />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true, message: '请输入分类' }]}>
            <Input placeholder="如：首次触达 / 跟进 / 节日问候" />
          </Form.Item>
          <Form.Item name="subject" label="主题" rules={[{ required: true, message: '请输入主题' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="variable_names" label="模板变量">
            <Select
              mode="multiple"
              placeholder="选择模板中使用的变量"
              options={SYSTEM_VARIABLES.map((v) => ({
                label: `{{${v.name}}} — ${v.label}`,
                value: v.name,
              }))}
            />
          </Form.Item>

          {/* Visual editor — only mounted when in visual mode to avoid GrapeJS init on every render */}
          {editMode === 'visual' && (
            <Form.Item label="邮件正文（可视化编辑器）">
              <GrapesEmailEditor
                ref={grapesRef}
                initialDesign={currentDesign ?? undefined}
                height={580}
              />
            </Form.Item>
          )}

          {editMode === 'html' && (
            <Form.Item
              name="body_html"
              label="邮件正文（HTML 源码）"
              rules={[{ required: true, message: '请输入正文' }]}
            >
              <Input.TextArea rows={18} placeholder="<p>Hello {{contact_name}}</p>" />
            </Form.Item>
          )}

          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title="邮件预览"
        open={previewHtml !== null}
        onCancel={() => setPreviewHtml(null)}
        footer={<Button onClick={() => setPreviewHtml(null)}>关闭</Button>}
        width={860}
        styles={{ body: { padding: 0, height: 600 } }}
      >
        <iframe
          srcDoc={previewHtml ?? ''}
          style={{ width: '100%', height: 600, border: 'none' }}
          title="邮件预览"
          sandbox="allow-same-origin"
        />
      </Modal>
    </Space>
  );
}

Component.displayName = 'EmailTemplatesPage';
