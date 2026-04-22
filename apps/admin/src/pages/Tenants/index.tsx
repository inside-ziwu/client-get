import { useMemo, useState } from 'react';
import {
  Button,
  Card,
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
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys, type Tenant, type TenantDomain, type TenantTeamUser } from '@shared/api';
import type { AiProviderConfig } from '@shared/types';
import { adminApi } from '../../lib/api';

const { Text, Paragraph } = Typography;

type CreateTenantValues = {
  name: string;
  slug: string;
  industry: string;
  contact_name?: string;
  contact_phone?: string;
  admin_email: string;
  admin_name: string;
  admin_password: string;
};

type DomainValues = {
  domain: string;
};

type TenantUserValues = {
  email: string;
  name: string;
  password: string;
  roles: string[];
  must_change_pwd: boolean;
  status: string;
};

type OpenRouterValues = {
  api_key: string;
};

const ROLE_OPTIONS = [
  { label: '管理员', value: 'admin' },
  { label: '操作员', value: 'operator' },
  { label: '查看者', value: 'viewer' },
];

const PROVIDER_STATUS: Record<string, { color: string; label: string }> = {
  available: { color: 'green', label: '可用' },
  insufficient_balance: { color: 'orange', label: '余额不足' },
  unknown: { color: 'gold', label: '余额未知' },
  invalid_api_key: { color: 'red', label: 'Key 无效' },
  provider_error: { color: 'red', label: '服务异常' },
  not_configured: { color: 'default', label: '未配置' },
};

function formatDate(value?: string | null) {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function statusTag(status: string) {
  if (status === 'active') return <Tag color="green">启用</Tag>;
  if (status === 'suspended') return <Tag color="red">暂停</Tag>;
  return <Tag>{status}</Tag>;
}

export function Component() {
  const queryClient = useQueryClient();
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [domainOpen, setDomainOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [openRouterOpen, setOpenRouterOpen] = useState(false);
  const [createForm] = Form.useForm<CreateTenantValues>();
  const [domainForm] = Form.useForm<DomainValues>();
  const [userForm] = Form.useForm<TenantUserValues>();
  const [openRouterForm] = Form.useForm<OpenRouterValues>();

  const tenantsQuery = useQuery({
    queryKey: queryKeys.admin.tenants.list(),
    queryFn: async () => (await adminApi.tenants.list()).data.data,
  });

  const [detailQuery, domainsQuery, usersQuery, openRouterQuery] = useQueries({
    queries: [
      {
        queryKey: selectedTenantId ? queryKeys.admin.tenants.detail(selectedTenantId) : ['admin', 'tenants', 'detail', 'empty'],
        queryFn: async () => {
          if (!selectedTenantId) return null;
          return (await adminApi.tenants.detail(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
      {
        queryKey: selectedTenantId ? queryKeys.admin.tenants.domains(selectedTenantId) : ['admin', 'tenants', 'domains', 'empty'],
        queryFn: async () => {
          if (!selectedTenantId) return [] as TenantDomain[];
          return (await adminApi.tenants.listDomains(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
      {
        queryKey: selectedTenantId ? queryKeys.admin.tenants.team(selectedTenantId) : ['admin', 'tenants', 'team', 'empty'],
        queryFn: async () => {
          if (!selectedTenantId) return [] as TenantTeamUser[];
          return (await adminApi.tenants.listTeam(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
      {
        queryKey: selectedTenantId ? queryKeys.admin.tenants.aiProvider(selectedTenantId) : ['admin', 'tenants', 'aiProvider', 'empty'],
        queryFn: async () => {
          if (!selectedTenantId) return null;
          return (await adminApi.tenants.getOpenRouter(selectedTenantId)).data.data as AiProviderConfig;
        },
        enabled: Boolean(selectedTenantId),
      },
    ],
  });

  const refreshSelectedTenant = async () => {
    if (!selectedTenantId) return;
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.detail(selectedTenantId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.domains(selectedTenantId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.team(selectedTenantId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.aiProvider(selectedTenantId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.list() }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (values: CreateTenantValues) => adminApi.tenants.create(values),
    onSuccess: async (response) => {
      message.success('租户已创建');
      setCreateOpen(false);
      createForm.resetFields();
      setSelectedTenantId(response.data.data.id);
      await queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.list() });
    },
    onError: () => message.error('创建租户失败'),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'activate' | 'suspend' }) =>
      action === 'activate' ? adminApi.tenants.activate(id) : adminApi.tenants.suspend(id),
    onSuccess: async () => {
      message.success('租户状态已更新');
      await refreshSelectedTenant();
    },
    onError: () => message.error('租户状态更新失败'),
  });

  const domainMutation = useMutation({
    mutationFn: (values: DomainValues) => {
      if (!selectedTenantId) throw new Error('missing tenant');
      return adminApi.tenants.createDomain(selectedTenantId, values);
    },
    onSuccess: async () => {
      message.success('域名已添加');
      setDomainOpen(false);
      domainForm.resetFields();
      await refreshSelectedTenant();
    },
    onError: () => message.error('添加域名失败'),
  });

  const verifyDomainMutation = useMutation({
    mutationFn: ({ tenantId, domainId }: { tenantId: string; domainId: string }) =>
      adminApi.tenants.verifyDomain(tenantId, domainId),
    onSuccess: async () => {
      message.success('域名已触发验证');
      await refreshSelectedTenant();
    },
    onError: () => message.error('域名验证失败'),
  });

  const userMutation = useMutation({
    mutationFn: (values: TenantUserValues) => {
      if (!selectedTenantId) throw new Error('missing tenant');
      return adminApi.tenants.createTeamUser(selectedTenantId, values);
    },
    onSuccess: async () => {
      message.success('成员已创建');
      setUserOpen(false);
      userForm.resetFields();
      await refreshSelectedTenant();
    },
    onError: () => message.error('创建成员失败'),
  });

  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => {
      if (!selectedTenantId) throw new Error('missing tenant');
      return adminApi.tenants.deleteTeamUser(selectedTenantId, userId);
    },
    onSuccess: async () => {
      message.success('成员已删除');
      await refreshSelectedTenant();
    },
    onError: () => message.error('删除成员失败'),
  });

  const upsertOpenRouterMutation = useMutation({
    mutationFn: (values: OpenRouterValues) => {
      if (!selectedTenantId) throw new Error('missing tenant');
      return adminApi.tenants.updateOpenRouter(selectedTenantId, values);
    },
    onSuccess: async () => {
      message.success('OpenRouter 配置已更新');
      setOpenRouterOpen(false);
      openRouterForm.resetFields();
      await refreshSelectedTenant();
    },
    onError: () => message.error('OpenRouter 配置保存失败'),
  });

  const refreshOpenRouterMutation = useMutation({
    mutationFn: () => {
      if (!selectedTenantId) throw new Error('missing tenant');
      return adminApi.tenants.refreshOpenRouterBalance(selectedTenantId);
    },
    onSuccess: async () => {
      message.success('OpenRouter 余额已刷新');
      await refreshSelectedTenant();
    },
    onError: () => message.error('OpenRouter 余额刷新失败'),
  });

  const deleteOpenRouterMutation = useMutation({
    mutationFn: () => {
      if (!selectedTenantId) throw new Error('missing tenant');
      return adminApi.tenants.deleteOpenRouter(selectedTenantId);
    },
    onSuccess: async () => {
      message.success('OpenRouter 配置已清空');
      await refreshSelectedTenant();
    },
    onError: () => message.error('OpenRouter 配置清空失败'),
  });

  const tenantColumns: ColumnsType<Tenant> = [
    {
      title: '租户',
      dataIndex: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => setSelectedTenantId(record.id)}>{value}</a>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.slug}</Text>
        </Space>
      ),
    },
    { title: '行业', dataIndex: 'industry', width: 140 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (value) => statusTag(value),
    },
    {
      title: 'Onboarding',
      dataIndex: 'needs_onboarding',
      width: 120,
      render: (value) => (value ? <Tag color="orange">待完成</Tag> : <Tag color="green">已完成</Tag>),
    },
    {
      title: '操作',
      width: 180,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => setSelectedTenantId(record.id)}>
            详情
          </Button>
          {record.status === 'active' ? (
            <Popconfirm title="确认暂停此租户？" onConfirm={() => statusMutation.mutate({ id: record.id, action: 'suspend' })}>
              <Button type="link" size="small" danger>
                暂停
              </Button>
            </Popconfirm>
          ) : (
            <Button type="link" size="small" onClick={() => statusMutation.mutate({ id: record.id, action: 'activate' })}>
              启用
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const domainColumns: ColumnsType<TenantDomain> = [
    { title: '域名', dataIndex: 'domain' },
    {
      title: '验证状态',
      dataIndex: 'verification_status',
      width: 120,
      render: (value) => (value === 'verified' ? <Tag color="green">已验证</Tag> : <Tag color="orange">{value}</Tag>),
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          disabled={!selectedTenantId || record.verification_status === 'verified'}
          onClick={() => selectedTenantId && verifyDomainMutation.mutate({ tenantId: selectedTenantId, domainId: record.id })}
        >
          验证
        </Button>
      ),
    },
  ];

  const userColumns: ColumnsType<TenantTeamUser> = [
    {
      title: '成员',
      dataIndex: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.email}</Text>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'roles',
      width: 180,
      render: (value) => (
        <Space wrap>
          {(value ?? []).map((role: string) => (
            <Tag key={role}>{role}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (value) => statusTag(value),
    },
    {
      title: '强制改密',
      dataIndex: 'must_change_pwd',
      width: 120,
      render: (value) => (value ? '是' : '否'),
    },
    {
      title: '操作',
      width: 110,
      render: (_, record) => (
        <Popconfirm title="确认删除此成员？" onConfirm={() => deleteUserMutation.mutate(record.id)}>
          <Button type="link" size="small" danger>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const providerStatus =
    PROVIDER_STATUS[openRouterQuery.data?.balance.status ?? 'not_configured'] ??
    { color: 'default', label: '未配置' };
  const providerActionsDisabled = !selectedTenantId;
  const providerDetail = useMemo(() => openRouterQuery.data, [openRouterQuery.data]);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <Text strong style={{ fontSize: 16 }}>租户管理</Text>
            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              租户创建、域名管理、团队账号与租户级 OpenRouter 配置全部走真实后端。
            </Paragraph>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: queryKeys.admin.tenants.list() })}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新建租户
            </Button>
          </Space>
        </div>
      </Card>

      <Table
        rowKey="id"
        columns={tenantColumns}
        dataSource={tenantsQuery.data ?? []}
        loading={tenantsQuery.isLoading}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无租户数据" /> }}
      />

      <Drawer
        title={detailQuery.data ? `${detailQuery.data.name} / ${detailQuery.data.slug}` : '租户详情'}
        open={Boolean(selectedTenantId)}
        onClose={() => setSelectedTenantId(null)}
        width="72%"
      >
        {detailQuery.data && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Card size="small">
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="状态">{statusTag(detailQuery.data.status)}</Descriptions.Item>
                <Descriptions.Item label="Onboarding">{detailQuery.data.needs_onboarding ? '待完成' : '已完成'}</Descriptions.Item>
                <Descriptions.Item label="行业">{detailQuery.data.industry ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="Slug">{detailQuery.data.slug}</Descriptions.Item>
                <Descriptions.Item label="联系人">{detailQuery.data.contact_name ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="联系电话">{detailQuery.data.contact_phone ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="联系邮箱" span={2}>
                  {detailQuery.data.contact_email ?? '—'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card
              size="small"
              title="OpenRouter"
              extra={
                <Space>
                  <Button size="small" icon={<ReloadOutlined />} disabled={providerActionsDisabled} loading={refreshOpenRouterMutation.isPending} onClick={() => refreshOpenRouterMutation.mutate()}>
                    刷新余额
                  </Button>
                  <Button size="small" type="primary" icon={<SafetyCertificateOutlined />} disabled={providerActionsDisabled} onClick={() => setOpenRouterOpen(true)}>
                    {providerDetail?.is_configured ? '覆盖更新 Key' : '配置 Key'}
                  </Button>
                  <Button
                    size="small"
                    danger
                    disabled={!providerDetail?.is_configured}
                    loading={deleteOpenRouterMutation.isPending}
                    onClick={() => deleteOpenRouterMutation.mutate()}
                  >
                    清空
                  </Button>
                </Space>
              }
            >
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="状态">
                  <Tag color={providerStatus.color}>{providerStatus.label}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Key 掩码">{providerDetail?.secret_masked ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="可判定余额">{providerDetail?.balance.amount ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="余额来源">{providerDetail?.balance.source ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="最近刷新">{formatDate(providerDetail?.balance.checked_at)}</Descriptions.Item>
                <Descriptions.Item label="最近轮换">{formatDate(providerDetail?.last_rotated_at)}</Descriptions.Item>
                <Descriptions.Item label="最后修改人" span={2}>
                  {providerDetail?.configured_by
                    ? `${providerDetail.configured_by.name ?? '未知'} (${providerDetail.configured_by.email ?? '—'})`
                    : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="状态消息" span={2}>
                  {providerDetail?.balance.message ?? '当前租户尚未配置 OpenRouter API key'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card
              size="small"
              title="域名管理"
              extra={
                <Button size="small" onClick={() => setDomainOpen(true)}>
                  添加域名
                </Button>
              }
            >
              <Table
                rowKey="id"
                columns={domainColumns}
                dataSource={domainsQuery.data ?? []}
                loading={domainsQuery.isLoading}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无域名" /> }}
              />
            </Card>

            <Card
              size="small"
              title="团队账号"
              extra={
                <Button size="small" onClick={() => setUserOpen(true)}>
                  添加成员
                </Button>
              }
            >
              <Table
                rowKey="id"
                columns={userColumns}
                dataSource={usersQuery.data ?? []}
                loading={usersQuery.isLoading}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无团队成员" /> }}
              />
            </Card>
          </Space>
        )}
      </Drawer>

      <Modal
        title="创建租户"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={async () => createMutation.mutate(await createForm.validateFields())}
        confirmLoading={createMutation.isPending}
        width={680}
      >
        <Form form={createForm} layout="vertical" initialValues={{ industry: 'PCB' }}>
          <Form.Item name="name" label="租户名称" rules={[{ required: true, message: '请输入租户名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="slug" label="Slug" rules={[{ required: true, message: '请输入 slug' }]}>
            <Input placeholder="globex-pcb" />
          </Form.Item>
          <Form.Item name="industry" label="行业" rules={[{ required: true, message: '请输入行业' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label="联系人">
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label="联系电话">
            <Input />
          </Form.Item>
          <Form.Item name="admin_email" label="管理员邮箱" rules={[{ required: true, message: '请输入管理员邮箱' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="admin_name" label="管理员姓名" rules={[{ required: true, message: '请输入管理员姓名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="admin_password" label="管理员密码" rules={[{ required: true, message: '请输入管理员密码' }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加域名"
        open={domainOpen}
        onCancel={() => setDomainOpen(false)}
        onOk={async () => domainMutation.mutate(await domainForm.validateFields())}
        confirmLoading={domainMutation.isPending}
      >
        <Form form={domainForm} layout="vertical">
          <Form.Item name="domain" label="域名" rules={[{ required: true, message: '请输入域名' }]}>
            <Input placeholder="mail.globex.example.com" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="添加团队成员"
        open={userOpen}
        onCancel={() => setUserOpen(false)}
        onOk={async () => userMutation.mutate(await userForm.validateFields())}
        confirmLoading={userMutation.isPending}
      >
        <Form
          form={userForm}
          layout="vertical"
          initialValues={{ roles: ['viewer'], must_change_pwd: true, status: 'active' }}
        >
          <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="roles" label="角色" rules={[{ required: true, message: '请选择角色' }]}>
            <Select mode="multiple" options={ROLE_OPTIONS} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select options={[{ label: 'active', value: 'active' }, { label: 'disabled', value: 'disabled' }]} />
          </Form.Item>
          <Form.Item name="must_change_pwd" label="首次登录强制改密">
            <Select options={[{ label: '是', value: true }, { label: '否', value: false }]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={providerDetail?.is_configured ? '覆盖更新 OpenRouter API key' : '配置 OpenRouter API key'}
        open={openRouterOpen}
        onCancel={() => setOpenRouterOpen(false)}
        onOk={async () => upsertOpenRouterMutation.mutate(await openRouterForm.validateFields())}
        confirmLoading={upsertOpenRouterMutation.isPending}
      >
        <Form form={openRouterForm} layout="vertical">
          <Form.Item
            name="api_key"
            label="OpenRouter API key"
            rules={[{ required: true, message: '请输入 OpenRouter API key' }]}
          >
            <Input.Password placeholder="sk-or-v1-..." autoComplete="off" />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'TenantsPage';
