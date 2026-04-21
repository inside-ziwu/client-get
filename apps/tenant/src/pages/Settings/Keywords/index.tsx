import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiClient, createTenantApi, queryKeys } from '@shared/api';

const { Text, Title } = Typography;

interface KeywordRecord {
  id: string;
  keyword: string;
  created_at: string;
}

const api = createTenantApi(createApiClient('tenant'));

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function Component() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [keywordInput, setKeywordInput] = useState('');
  const [editing, setEditing] = useState<KeywordRecord | null>(null);

  const keywordsQuery = useQuery({
    queryKey: queryKeys.keywords.list(),
    queryFn: async () => (await api.keywords.list()).data.data,
  });

  const createMutation = useMutation({
    mutationFn: (keyword: string) => api.keywords.create({ keyword }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.keywords.list() });
      message.success('关键词已添加');
      form.resetFields();
      setKeywordInput('');
    },
    onError: () => message.error('添加失败，请稍后重试'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, keyword }: { id: string; keyword: string }) =>
      api.keywords.update(id, { keyword }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.keywords.list() });
      message.success('关键词已更新');
      setEditing(null);
    },
    onError: () => message.error('更新失败，请稍后重试'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.keywords.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.keywords.list() });
      message.success('关键词已删除');
    },
    onError: () => message.error('删除失败，请稍后重试'),
  });

  useEffect(() => {
    if (editing) {
      editForm.setFieldsValue({ keyword: editing.keyword });
    }
  }, [editing, editForm]);

  const keywords = keywordsQuery.data ?? [];

  const columns: ColumnsType<KeywordRecord> = [
    {
      title: '关键词',
      dataIndex: 'keyword',
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (value: string) => <Text type="secondary">{formatDate(value)}</Text>,
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space size={0}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => setEditing(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="删除关键词"
            description="确认删除这个关键词？"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>关键词管理</Title>
          <Text type="secondary">使用真实接口管理租户关键词，新增、编辑和删除会立即同步到后端。</Text>
        </div>
      </div>

      <Alert
        type="info"
        showIcon
        message="关键词列表来自 `/api/v1/keywords`，修改后会立即保存，无需再点全局保存。"
      />

      <Card size="small">
        <Form form={form} layout="inline" onFinish={() => {
          const keyword = keywordInput.trim();
          if (!keyword) return;
          createMutation.mutate(keyword);
        }}>
          <Form.Item style={{ marginBottom: 0 }}>
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              placeholder="输入关键词后回车或点击添加"
              style={{ width: 320 }}
              onPressEnter={() => form.submit()}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              htmlType="submit"
              loading={createMutation.isPending}
            >
              添加关键词
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card size="small" title={`当前关键词 ${keywords.length}`}>
        <Table<KeywordRecord>
          rowKey="id"
          columns={columns}
          dataSource={keywords}
          loading={keywordsQuery.isLoading}
          size="middle"
          pagination={false}
          locale={{ emptyText: '暂无关键词，请先添加一条' }}
        />
      </Card>

      <Modal
        title="编辑关键词"
        open={Boolean(editing)}
        onCancel={() => setEditing(null)}
        onOk={async () => {
          const values = await editForm.validateFields();
          if (!editing) return;
          updateMutation.mutate({ id: editing.id, keyword: values.keyword.trim() });
        }}
        confirmLoading={updateMutation.isPending}
        okText="保存"
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="keyword"
            label="关键词"
            rules={[{ required: true, whitespace: true, message: '请输入关键词' }]}
          >
            <Input placeholder="例如：PCB" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'KeywordsSettingsPage';
