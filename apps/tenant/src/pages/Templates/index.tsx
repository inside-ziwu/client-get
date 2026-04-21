import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { CopyOutlined, DeleteOutlined, EditOutlined, PlusOutlined, RobotOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { BillingBalance } from '@shared/types';
import { AIBalanceGuard } from '@shared/ui';
import type { EmailTemplate } from '@shared/api';
import { queryKeys } from '@shared/api';
import { tenantApi } from '../../lib/api';

const { Text, Paragraph } = Typography;

type EditorValues = {
  name: string;
  category: string;
  subject: string;
  body_html: string;
  body_text: string;
};

type AiValues = {
  name: string;
  category: string;
  company_name: string;
  prompt: string;
  subject?: string;
};

const CATEGORY_OPTIONS = [
  { label: 'cold_outreach', value: 'cold_outreach' },
  { label: 'follow_up', value: 'follow_up' },
  { label: 'promotion', value: 'promotion' },
  { label: 'festival', value: 'festival' },
];

export function Component() {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [editing, setEditing] = useState<EmailTemplate | null>(null);
  const [previewData, setPreviewData] = useState<{ subject?: string; body_html?: string; body_text?: string } | null>(null);
  const [editorForm] = Form.useForm<EditorValues>();
  const [aiForm] = Form.useForm<AiValues>();

  const templatesQuery = useQuery({
    queryKey: queryKeys.emailTemplates.list(),
    queryFn: async () => (await tenantApi.emailTemplates.list()).data.data,
  });

  const balanceQuery = useQuery({
    queryKey: queryKeys.billing.balance(),
    queryFn: async () => (await tenantApi.billing.balance()).data.data as BillingBalance,
  });

  const balance = balanceQuery.data?.balance ?? balanceQuery.data?.amount ?? 0;

  const createOrUpdateMutation = useMutation({
    mutationFn: async (values: EditorValues) => {
      const payload = {
        name: values.name.trim(),
        category: values.category.trim(),
        subject: values.subject.trim(),
        body_html: values.body_html,
        body_text: values.body_text,
        variables: [],
        source_type: editing?.source_type ?? 'custom',
      };
      if (editing) {
        return tenantApi.emailTemplates.update(editing.id, payload);
      }
      return tenantApi.emailTemplates.create(payload);
    },
    onSuccess: async () => {
      message.success(editing ? '模板已更新' : '模板已创建');
      setEditorOpen(false);
      setEditing(null);
      editorForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: queryKeys.emailTemplates.all() });
    },
    onError: () => message.error('模板保存失败'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tenantApi.emailTemplates.delete(id),
    onSuccess: async () => {
      message.success('模板已删除');
      await queryClient.invalidateQueries({ queryKey: queryKeys.emailTemplates.all() });
    },
    onError: () => message.error('模板删除失败'),
  });

  const cloneMutation = useMutation({
    mutationFn: (id: string) => tenantApi.emailTemplates.clone(id),
    onSuccess: async () => {
      message.success('模板已克隆');
      await queryClient.invalidateQueries({ queryKey: queryKeys.emailTemplates.all() });
    },
    onError: () => message.error('模板克隆失败'),
  });

  const aiMutation = useMutation({
    mutationFn: async (values: AiValues) =>
      (
        await tenantApi.emailTemplates.aiGenerate({
          prompt: values.prompt,
          company_name: values.company_name,
          category: values.category,
          subject: values.subject,
          name: values.name || undefined,
        })
      ).data.data,
    onSuccess: async (template) => {
      message.success('AI 模板已生成');
      setAiOpen(false);
      aiForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: queryKeys.emailTemplates.all() });
      setEditing(template);
      editorForm.setFieldsValue({
        name: template.name,
        category: template.category ?? 'cold_outreach',
        subject: template.subject,
        body_html: template.body_html,
        body_text: template.body_text ?? '',
      });
      setEditorOpen(true);
    },
    onError: () => message.error('AI 生成失败'),
  });

  const openCreate = () => {
    setEditing(null);
    editorForm.setFieldsValue({
      name: '',
      category: 'cold_outreach',
      subject: '',
      body_html: '',
      body_text: '',
    });
    setEditorOpen(true);
  };

  const openEdit = async (template: EmailTemplate) => {
    setEditing(template);
    const detail = (await tenantApi.emailTemplates.detail(template.id)).data.data;
    editorForm.setFieldsValue({
      name: detail.name,
      category: detail.category ?? 'cold_outreach',
      subject: detail.subject,
      body_html: detail.body_html,
      body_text: detail.body_text ?? '',
    });
    setEditorOpen(true);
  };

  const openPreview = async (template: EmailTemplate) => {
    try {
      const preview = (await tenantApi.emailTemplates.preview(template.id)).data.data;
      setPreviewData(preview);
      setPreviewOpen(true);
    } catch {
      message.error('模板预览加载失败');
    }
  };

  const templates = templatesQuery.data ?? [];
  const platformTemplates = useMemo(
    () => templates.filter((item) => item.source_type === 'platform_copy'),
    [templates],
  );
  const customTemplates = useMemo(
    () => templates.filter((item) => item.source_type !== 'platform_copy'),
    [templates],
  );

  const columns: ColumnsType<EmailTemplate> = [
    {
      title: '模板名称',
      dataIndex: 'name',
      render: (value, record) => (
        <Space>
          <Text strong>{value}</Text>
          {record.is_ai_generated && <Tag color="purple">AI</Tag>}
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 140,
      render: (value) => <Tag>{value ?? 'uncategorized'}</Tag>,
    },
    {
      title: '主题',
      dataIndex: 'subject',
      render: (value) => <Text type="secondary">{value}</Text>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 180,
    },
    {
      title: '操作',
      width: 260,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => void openPreview(record)}>
            预览
          </Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => void openEdit(record)}>
            编辑
          </Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => cloneMutation.mutate(record.id)}>
            克隆
          </Button>
          {record.source_type !== 'platform_copy' && (
            <Popconfirm title="确认删除此模板？" onConfirm={() => deleteMutation.mutate(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <div>
          <Text strong style={{ fontSize: 16 }}>邮件模板</Text>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            平台模板、副本模板和 AI 生成模板全部来自真实后端。
          </Paragraph>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建模板
          </Button>
          <AIBalanceGuard balance={balance}>
            <Button icon={<RobotOutlined />} onClick={() => setAiOpen(true)}>
              AI 生成
            </Button>
          </AIBalanceGuard>
        </Space>
      </Space>

      {templatesQuery.isError && (
        <Alert type="error" showIcon message="模板加载失败" />
      )}

      <Tabs
        items={[
          {
            key: 'platform',
            label: `平台模板 (${platformTemplates.length})`,
            children: (
              <Table
                rowKey="id"
                columns={columns}
                dataSource={platformTemplates}
                loading={templatesQuery.isLoading}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无平台模板副本" /> }}
              />
            ),
          },
          {
            key: 'custom',
            label: `自有模板 (${customTemplates.length})`,
            children: (
              <Table
                rowKey="id"
                columns={columns}
                dataSource={customTemplates}
                loading={templatesQuery.isLoading}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无自有模板" /> }}
              />
            ),
          },
        ]}
      />

      <Drawer
        title={editing ? `编辑模板 / ${editing.name}` : '新建模板'}
        width={720}
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        extra={
          <Button
            type="primary"
            loading={createOrUpdateMutation.isPending}
            onClick={async () => createOrUpdateMutation.mutate(await editorForm.validateFields())}
          >
            保存
          </Button>
        }
      >
        <Form form={editorForm} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true, message: '请输入分类' }]}>
            <Select options={CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item name="subject" label="主题" rules={[{ required: true, message: '请输入主题' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="body_html" label="HTML 正文" rules={[{ required: true, message: '请输入 HTML 正文' }]}>
            <Input.TextArea rows={8} />
          </Form.Item>
          <Form.Item name="body_text" label="纯文本正文">
            <Input.TextArea rows={6} />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal title="模板预览" open={previewOpen} onCancel={() => setPreviewOpen(false)} footer={null} width={760}>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="主题">{previewData?.subject ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="纯文本">
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{previewData?.body_text ?? '—'}</pre>
          </Descriptions.Item>
          <Descriptions.Item label="HTML">
            <div dangerouslySetInnerHTML={{ __html: previewData?.body_html ?? '<p>—</p>' }} />
          </Descriptions.Item>
        </Descriptions>
      </Modal>

      <Modal
        title="AI 生成模板"
        open={aiOpen}
        onCancel={() => setAiOpen(false)}
        onOk={async () => aiMutation.mutate(await aiForm.validateFields())}
        confirmLoading={aiMutation.isPending}
      >
        <Form form={aiForm} layout="vertical" initialValues={{ category: 'cold_outreach' }}>
          <Form.Item name="name" label="模板名称">
            <Input placeholder="AI 首触模板" />
          </Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true, message: '请选择分类' }]}>
            <Select options={CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item name="company_name" label="公司/行业描述" rules={[{ required: true, message: '请输入公司或行业描述' }]}>
            <Input placeholder="PCB manufacturer" />
          </Form.Item>
          <Form.Item name="prompt" label="生成要求" rules={[{ required: true, message: '请输入生成要求' }]}>
            <Input.TextArea rows={4} placeholder="强调交付能力、报价响应速度、德语客户场景" />
          </Form.Item>
          <Form.Item name="subject" label="主题偏好">
            <Input placeholder="可选，留空由后端生成" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'TemplatesPage';
