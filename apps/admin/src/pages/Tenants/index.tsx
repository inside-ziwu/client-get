import { useState } from 'react';
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
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../lib/api';
import type {
  BalanceTransaction,
  Tenant,
  TenantDomain,
  TenantTeamUser,
} from '@shared/api';

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

type RechargeValues = {
  amount: number;
  description?: string;
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

const ROLE_OPTIONS = [
  { label: '管理员', value: 'admin' },
  { label: '操作员', value: 'operator' },
  { label: '查看者', value: 'viewer' },
];

function formatDate(value?: string | null) {
  if (!value) {
    return '—';
  }
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
  const [rechargeOpen, setRechargeOpen] = useState(false);
  const [domainOpen, setDomainOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [createForm] = Form.useForm<CreateTenantValues>();
  const [rechargeForm] = Form.useForm<RechargeValues>();
  const [domainForm] = Form.useForm<DomainValues>();
  const [userForm] = Form.useForm<TenantUserValues>();

  const tenantsQuery = useQuery({
    queryKey: ['admin', 'tenants', 'list'],
    queryFn: async () => (await adminApi.tenants.list()).data.data,
  });

  const [detailQuery, domainsQuery, usersQuery, transactionsQuery] = useQueries({
    queries: [
      {
        queryKey: ['admin', 'tenants', 'detail', selectedTenantId],
        queryFn: async () => {
          if (!selectedTenantId) return null;
          return (await adminApi.tenants.detail(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
      {
        queryKey: ['admin', 'tenants', 'domains', selectedTenantId],
        queryFn: async () => {
          if (!selectedTenantId) return [] as TenantDomain[];
          return (await adminApi.tenants.listDomains(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
      {
        queryKey: ['admin', 'tenants', 'users', selectedTenantId],
        queryFn: async () => {
          if (!selectedTenantId) return [] as TenantTeamUser[];
          return (await adminApi.tenants.listTeam(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
      {
        queryKey: ['admin', 'tenants', 'transactions', selectedTenantId],
        queryFn: async () => {
          if (!selectedTenantId) return [] as BalanceTransaction[];
          return (await adminApi.tenants.listBalanceTransactions(selectedTenantId)).data.data;
        },
        enabled: Boolean(selectedTenantId),
      },
    ],
  });

  const refreshSelectedTenant = async () => {
    if (!selectedTenantId) {
      return;
    }
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'detail', selectedTenantId] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'domains', selectedTenantId] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'users', selectedTenantId] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'transactions', selectedTenantId] }),
      queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'list'] }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (values: CreateTenantValues) => adminApi.tenants.create(values),
    onSuccess: async (response) => {
      message.success('租户已创建');
      setCreateOpen(false);
      createForm.resetFields();
      setSelectedTenantId(response.data.data.id);
      await queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'list'] });
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

  const rechargeMutation = useMutation({
    mutationFn: (values: RechargeValues) => {
      if (!selectedTenantId) {
        throw new Error('missing tenant');
      }
      return adminApi.tenants.rechargeBalance(selectedTenantId, values);
    },
    onSuccess: async () => {
      message.success('余额已充值');
      setRechargeOpen(false);
      rechargeForm.resetFields();
      await refreshSelectedTenant();
    },
    onError: () => message.error('充值失败'),
  });

  const domainMutation = useMutation({
    mutationFn: (values: DomainValues) => {
      if (!selectedTenantId) {
        throw new Error('missing tenant');
      }
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
      message.success('域名已验证');
      await refreshSelectedTenant();
    },
    onError: () => message.error('域名验证失败'),
  });

  const userMutation = useMutation({
    mutationFn: (values: TenantUserValues) => {
      if (!selectedTenantId) {
        throw new Error('missing tenant');
      }
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
      if (!selectedTenantId) {
        throw new Error('missing tenant');
      }
      return adminApi.tenants.deleteTeamUser(selectedTenantId, userId);
    },
    onSuccess: async () => {
      message.success('成员已删除');
      await refreshSelectedTenant();
    },
    onError: () => message.error('删除成员失败'),
  });

  const tenantColumns: ColumnsType<Tenant> = [
    {
      title: '租户',
      dataIndex: 'name',
      render: (value, record) => (
        <Space direction="vertical" size={0}>
          <a onClick={() => setSelectedTenantId(record.id)}>{value}</a>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.slug}
          </Text>
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
      title: '余额',
      dataIndex: 'balance',
      width: 120,
      render: (value) => <Text strong>¥{value ?? 0}</Text>,
    },
    {
      title: 'Onboarding',
      dataIndex: 'needs_onboarding',
      width: 120,
      render: (value) => value ? <Tag color="orange">待完成</Tag> : <Tag color="green">已完成</Tag>,
    },
    {
      title: '操作',
      width: 210,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => setSelectedTenantId(record.id)}>
            详情
          </Button>
          {record.status === 'active' ? (
            <Popconfirm
              title="确认暂停此租户？"
              onConfirm={() => statusMutation.mutate({ id: record.id, action: 'suspend' })}
            >
              <Button type="link" size="small" danger>
                暂停
              </Button>
            </Popconfirm>
          ) : (
            <Button type="link" size="small" onClick={() => statusMutation.mutate({ id: record.id, action: 'activate' })}>
              启用
            </Button>
          )}
          <Button
            type="link"
            size="small"
            onClick={() => {
              setSelectedTenantId(record.id);
              setRechargeOpen(true);
            }}
          >
            充值
          </Button>
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
      render: (value) =>
        value === 'verified' ? <Tag color="green">已验证</Tag> : <Tag color="orange">{value}</Tag>,
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          disabled={!selectedTenantId || record.verification_status === 'verified'}
          onClick={() => {
            if (!selectedTenantId) return;
            verifyDomainMutation.mutate({ tenantId: selectedTenantId, domainId: record.id });
          }}
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
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.email}
          </Text>
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
      width: 110,
      render: (value) => value ? '是' : '否',
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

  const transactionColumns: ColumnsType<BalanceTransaction> = [
    { title: '类型', dataIndex: 'type', width: 120 },
    {
      title: '金额',
      dataIndex: 'amount',
      width: 120,
      render: (value) => <Text strong>¥{value}</Text>,
    },
    { title: '说明', dataIndex: 'description', render: (value) => value ?? '—' },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 180,
      render: (value) => <Text type="secondary">{formatDate(value)}</Text>,
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card size="small">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <Text strong style={{ fontSize: 16 }}>
              租户管理
            </Text>
            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              统一从真实后台接口完成租户创建、域名管理、团队账号和余额流水。
            </Paragraph>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['admin', 'tenants', 'list'] })}>
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
                <Descriptions.Item label="余额">¥{detailQuery.data.balance ?? 0}</Descriptions.Item>
                <Descriptions.Item label="行业">{detailQuery.data.industry ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="Onboarding">
                  {detailQuery.data.needs_onboarding ? '待完成' : '已完成'}
                </Descriptions.Item>
                <Descriptions.Item label="联系人">{detailQuery.data.contact_name ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="联系电话">{detailQuery.data.contact_phone ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="联系邮箱" span={2}>
                  {detailQuery.data.contact_email ?? '—'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card
              size="small"
              title="域名管理"
              extra={
                <Space>
                  <Button size="small" onClick={() => setDomainOpen(true)}>
                    添加域名
                  </Button>
                  <Button size="small" onClick={() => setRechargeOpen(true)}>
                    余额充值
                  </Button>
                </Space>
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

            <Card size="small" title="余额流水">
              <Table
                rowKey="id"
                columns={transactionColumns}
                dataSource={transactionsQuery.data ?? []}
                loading={transactionsQuery.isLoading}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无流水" /> }}
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
        title="租户充值"
        open={rechargeOpen}
        onCancel={() => setRechargeOpen(false)}
        onOk={async () => rechargeMutation.mutate(await rechargeForm.validateFields())}
        confirmLoading={rechargeMutation.isPending}
      >
        <Form form={rechargeForm} layout="vertical">
          <Form.Item name="amount" label="金额" rules={[{ required: true, message: '请输入充值金额' }]}>
            <InputNumber min={0.01} step={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input placeholder="manual recharge" />
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
            <Input placeholder="mail.globex.demo.test" />
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
    </Space>
  );
}

Component.displayName = 'TenantsPage';
