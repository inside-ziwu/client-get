import { useMemo, useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@shared/api';
import type { Company } from '@shared/api';
import { useCursorPagination } from '@shared/hooks';
import { tenantApi } from '../../lib/api';

const { Text, Paragraph } = Typography;

type CompanyContact = {
  name: string;
  email: string;
  title: string;
  is_default: boolean;
  raw: Record<string, unknown>;
};

type CreateCompanyValues = {
  name: string;
  country?: string;
  website?: string;
  industry?: string;
  contact_name?: string;
  contact_email?: string;
  contact_title?: string;
};

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function normalizeContact(record: Record<string, unknown>): CompanyContact {
  return {
    name: String(record.name ?? record.contact_name ?? record.full_name ?? '—'),
    email: String(record.email ?? record.contact_email ?? '—'),
    title: String(record.title ?? record.contact_title ?? '—'),
    is_default: Boolean(record.is_default ?? record.default ?? false),
    raw: record,
  };
}

export function Component() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [createForm] = Form.useForm<CreateCompanyValues>();
  const [filters, setFilters] = useState<Record<string, unknown>>({ limit: 20 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [blacklistTarget, setBlacklistTarget] = useState<{ id: string; name: string } | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const companiesQuery = useCursorPagination(
    queryKeys.companies.list(filters),
    async (cursor) => (await tenantApi.companies.list({ ...(filters as Record<string, unknown>), cursor, limit: 20 })).data,
  );

  const companies = useMemo(
    () => companiesQuery.data?.pages.flatMap((page) => page.data) ?? [],
    [companiesQuery.data],
  );

  const selectedCompanyQuery = useQuery({
    queryKey: selectedId ? queryKeys.companies.detail(selectedId) : ['tenant', 'companies', 'detail', 'empty'],
    queryFn: async () => {
      if (!selectedId) return null;
      return (await tenantApi.companies.detail(selectedId)).data.data;
    },
    enabled: Boolean(selectedId),
  });

  const contactsQuery = useQuery({
    queryKey: selectedId ? [...queryKeys.companies.detail(selectedId), 'contacts'] : ['tenant', 'companies', 'contacts', 'empty'],
    queryFn: async () => {
      if (!selectedId) return [];
      return (await tenantApi.companies.contacts(selectedId)).data.data.map(normalizeContact);
    },
    enabled: Boolean(selectedId),
  });

  const blacklistMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => tenantApi.companies.blacklist(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.companies.all() });
      message.success('已加入黑名单');
      setBlacklistTarget(null);
    },
    onError: () => message.error('黑名单操作失败'),
  });

  const createMutation = useMutation({
    mutationFn: (values: CreateCompanyValues) =>
      tenantApi.companies.create({
        name: values.name.trim(),
        country: values.country?.trim() || undefined,
        website: values.website?.trim() || undefined,
        industry: values.industry?.trim() || undefined,
        contact_name: values.contact_name?.trim() || undefined,
        contact_email: values.contact_email?.trim() || undefined,
        contact_title: values.contact_title?.trim() || undefined,
      }),
    onSuccess: async () => {
      message.success('公司已创建');
      setCreateOpen(false);
      createForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: queryKeys.companies.all() });
    },
    onError: () => message.error('公司创建失败'),
  });

  const columns: ColumnsType<Company> = [
    {
      title: '公司名称',
      dataIndex: 'name',
      render: (name, record) => (
        <Space>
          <a onClick={() => setSelectedId(record.id)}>{name}</a>
          {record.is_precise_customer && <Tag color="gold">精准</Tag>}
        </Space>
      ),
    },
    {
      title: '国家',
      dataIndex: 'country',
      width: 90,
      render: (value) => value ? <Tag>{value}</Tag> : '—',
    },
    {
      title: '行业',
      dataIndex: 'industry',
      width: 120,
      render: (value) => value ?? '—',
    },
    {
      title: '评级',
      dataIndex: 'grade',
      width: 80,
      render: (value) => value ? <Tag color="blue">{value}</Tag> : '—',
    },
    {
      title: '总分',
      dataIndex: 'total_score',
      width: 80,
      render: (value) => value ?? '—',
    },
    {
      title: '域名',
      dataIndex: 'domain',
      render: (value, record) => value ?? record.website ?? '—',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 170,
      render: (value) => value ? <Text type="secondary">{formatDate(value)}</Text> : '—',
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => setSelectedId(record.id)}>详情</Button>
          <Button type="link" size="small" danger onClick={() => setBlacklistTarget({ id: record.id, name: record.name })}>黑名单</Button>
        </Space>
      ),
    },
  ];

  const handleSearch = async () => {
    const values = await form.validateFields();
    setFilters({
      limit: 20,
      keyword: values.keyword?.trim() || undefined,
      grade: values.grade || undefined,
      country: values.country || undefined,
      min_score: values.min_score,
      max_score: values.max_score,
    });
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card size="small">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <Text strong style={{ fontSize: 16 }}>公司列表</Text>
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                直接展示后端公司数据，去掉本地 mock 的联系人/评分明细假字段。
              </Paragraph>
            </div>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新建公司
            </Button>
          </div>

          <Form form={form} layout="inline" initialValues={{}}>
            <Form.Item name="keyword" label="关键词">
              <Input placeholder="公司名 / 域名" style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="grade" label="评级">
              <Input placeholder="S/A/B/C/D" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="country" label="国家">
              <Input placeholder="DE / US / CN" style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="min_score" label="最低分">
              <InputNumber min={0} max={100} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="max_score" label="最高分">
              <InputNumber min={0} max={100} style={{ width: 120 }} />
            </Form.Item>
          </Form>

          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
            <Button icon={<ReloadOutlined />} onClick={() => { form.resetFields(); setFilters({ limit: 20 }); }}>重置</Button>
          </Space>
        </Space>
      </Card>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={companies}
        loading={companiesQuery.isLoading}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无公司数据" /> }}
      />

      <div style={{ textAlign: 'center' }}>
        <Button
          onClick={() => companiesQuery.fetchNextPage()}
          loading={companiesQuery.isFetchingNextPage}
          disabled={!companiesQuery.hasNextPage}
        >
          {companiesQuery.hasNextPage ? '加载更多' : '没有更多了'}
        </Button>
      </div>

      <Drawer
        title={selectedCompanyQuery.data ? selectedCompanyQuery.data.name : '公司详情'}
        open={Boolean(selectedId)}
        onClose={() => setSelectedId(null)}
        width="68%"
      >
        {selectedCompanyQuery.isLoading && <Text type="secondary">正在加载详情…</Text>}
        {selectedCompanyQuery.data && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="国家">{selectedCompanyQuery.data.country ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="行业">{selectedCompanyQuery.data.industry ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="评级">{selectedCompanyQuery.data.grade ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="总分">{selectedCompanyQuery.data.total_score ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="域名">{selectedCompanyQuery.data.domain ?? selectedCompanyQuery.data.website ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="精准客户">{selectedCompanyQuery.data.is_precise_customer ? '是' : '否'}</Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{selectedCompanyQuery.data.notes ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                <Space wrap>
                  {(selectedCompanyQuery.data.tags ?? []).length > 0
                    ? selectedCompanyQuery.data.tags!.map((tag) => <Tag key={tag}>{tag}</Tag>)
                    : '—'}
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="联系人">
              <Table<CompanyContact>
                rowKey={(record, index) => `${record.email}-${index}`}
                loading={contactsQuery.isLoading}
                dataSource={contactsQuery.data ?? []}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无联系人数据" /> }}
                columns={[
                  {
                    title: '姓名',
                    dataIndex: 'name',
                  },
                  {
                    title: '职位',
                    dataIndex: 'title',
                  },
                  {
                    title: '邮箱',
                    dataIndex: 'email',
                  },
                  {
                    title: '默认',
                    dataIndex: 'is_default',
                    width: 90,
                    render: (value) => value ? <Tag color="gold">默认</Tag> : '—',
                  },
                ]}
              />
            </Card>

            <Card size="small" title="原始字段">
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(selectedCompanyQuery.data, null, 2)}
              </pre>
            </Card>
          </Space>
        )}
      </Drawer>

      <Modal
        title={`确认拉黑 ${blacklistTarget?.name ?? ''}`}
        open={Boolean(blacklistTarget)}
        onCancel={() => setBlacklistTarget(null)}
        onOk={() => {
          if (!blacklistTarget) return;
          blacklistMutation.mutate({ id: blacklistTarget.id });
        }}
        confirmLoading={blacklistMutation.isPending}
      >
        <Text type="secondary">将该公司加入黑名单后，后续列表会按后端规则重新过滤。</Text>
      </Modal>

      <Modal
        title="新建公司"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={async () => createMutation.mutate(await createForm.validateFields())}
        confirmLoading={createMutation.isPending}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="公司名称" rules={[{ required: true, message: '请输入公司名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="country" label="国家">
            <Input placeholder="DE / US / JP" />
          </Form.Item>
          <Form.Item name="website" label="网站">
            <Input placeholder="https://example.com" />
          </Form.Item>
          <Form.Item name="industry" label="行业">
            <Input placeholder="PCB" />
          </Form.Item>
          <Form.Item name="contact_name" label="联系人姓名">
            <Input />
          </Form.Item>
          <Form.Item name="contact_email" label="联系人邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="contact_title" label="联系人职位">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'CompaniesPage';
