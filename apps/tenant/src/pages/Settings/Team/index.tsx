import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
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
import { PlusOutlined, UserOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiClient, createTenantApi, queryKeys, type TeamUser } from '@shared/api';

const { Text, Title } = Typography;

type Role = 'admin' | 'operator' | 'viewer';
type MemberStatus = 'active' | 'disabled';

type TeamFormValues = {
  email: string;
  name: string;
  role: Role;
};

const api = createTenantApi(createApiClient('tenant'));

const ROLE_LABELS: Record<Role, string> = {
  admin: '管理员',
  operator: '运营',
  viewer: '只读',
};

const ROLE_COLORS: Record<Role, string> = {
  admin: 'blue',
  operator: 'purple',
  viewer: 'default',
};

const STATUS_LABELS: Record<MemberStatus, string> = {
  active: '已激活',
  disabled: '已禁用',
};

const STATUS_COLOR: Record<MemberStatus, 'success' | 'error'> = {
  active: 'success',
  disabled: 'error',
};

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('zh-CN');
}

function readPrimaryRole(user: TeamUser): Role {
  const first = user.roles?.[0];
  if (first === 'admin' || first === 'operator' || first === 'viewer') {
    return first;
  }
  return 'viewer';
}

function readStatus(user: TeamUser): MemberStatus {
  return user.status === 'disabled' ? 'disabled' : 'active';
}

export function Component() {
  const queryClient = useQueryClient();
  const [inviteForm] = Form.useForm<TeamFormValues>();
  const [editForm] = Form.useForm<TeamFormValues>();
  const [open, setOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<TeamUser | null>(null);

  const teamQuery = useQuery<TeamUser[]>({
    queryKey: queryKeys.team.list(),
    queryFn: async () => (await api.team.list()).data.data,
  });

  useEffect(() => {
    if (!open) {
      inviteForm.resetFields();
    }
  }, [open, inviteForm]);

  useEffect(() => {
    if (editingMember) {
      editForm.setFieldsValue({
        name: editingMember.name,
        email: editingMember.email,
        role: readPrimaryRole(editingMember),
      });
    } else {
      editForm.resetFields();
    }
  }, [editingMember, editForm]);

  const createMutation = useMutation({
    mutationFn: (values: TeamFormValues) =>
      api.team.create({
        email: values.email,
        name: values.name,
        roles: [values.role],
        must_change_pwd: true,
        status: 'active',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.team.list() });
      message.success('成员已创建');
      setOpen(false);
      inviteForm.resetFields();
    },
    onError: () => message.error('成员创建失败，请稍后重试'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; roles?: Role[]; status?: MemberStatus } }) =>
      api.team.update(id, data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.team.list() });
      message.success('成员信息已更新');
      setEditingMember(null);
    },
    onError: () => message.error('更新失败，请稍后重试'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.team.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.team.list() });
      message.success('成员已移除');
    },
    onError: () => message.error('删除失败，请稍后重试'),
  });

  const columns: ColumnsType<TeamUser> = useMemo(
    () => [
      {
        title: '成员',
        render: (_, record) => (
          <Space>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: '50%',
                background: '#e6f4ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <UserOutlined style={{ color: '#1677ff' }} />
            </div>
            <div>
              <div><Text strong>{record.name}</Text></div>
              <div><Text type="secondary" style={{ fontSize: 12 }}>{record.email}</Text></div>
            </div>
          </Space>
        ),
      },
      {
        title: '角色',
        width: 180,
        render: (_, record) => (
          <Space wrap>
            {(record.roles ?? []).map((role) => (
              <Tag key={role} color={ROLE_COLORS[role as Role] ?? 'default'}>
                {ROLE_LABELS[role as Role] ?? role}
              </Tag>
            ))}
          </Space>
        ),
      },
      {
        title: '状态',
        width: 100,
        render: (_, record) => {
          const status = readStatus(record);
          return <Badge status={STATUS_COLOR[status]} text={STATUS_LABELS[status]} />;
        },
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        width: 110,
        render: (value: string) => <Text type="secondary">{formatDate(value)}</Text>,
      },
      {
        title: '操作',
        width: 220,
        render: (_, record) => {
          const status = readStatus(record);
          return (
            <Space size={0}>
              {status === 'active' && (
                <Button
                  type="link"
                  size="small"
                  onClick={() => updateMutation.mutate({ id: record.id, data: { status: 'disabled' } })}
                >
                  禁用
                </Button>
              )}
              {status === 'disabled' && (
                <Button
                  type="link"
                  size="small"
                  onClick={() => updateMutation.mutate({ id: record.id, data: { status: 'active' } })}
                >
                  启用
                </Button>
              )}
              <Button
                type="link"
                size="small"
                onClick={() => setEditingMember(record)}
              >
                修改角色
              </Button>
              <Popconfirm
                title="确认删除该成员？"
                onConfirm={() => deleteMutation.mutate(record.id)}
              >
                <Button type="link" size="small" danger>
                  删除
                </Button>
              </Popconfirm>
            </Space>
          );
        },
      },
    ],
    [deleteMutation, updateMutation],
  );

  const team = teamQuery.data ?? [];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>团队管理</Title>
          <Text type="secondary">团队成员来自真实 API，角色严格使用 `admin / operator / viewer`。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          新增成员
        </Button>
      </div>

      <Alert
        type="info"
        showIcon
        message="成员列表来自 `/api/v1/team/users`，页面不再把角色伪装成单独的 `role` 字段。"
      />

      <Card size="small">
        <Table<TeamUser>
          rowKey="id"
          columns={columns}
          dataSource={team}
          loading={teamQuery.isLoading}
          size="middle"
          pagination={false}
          locale={{ emptyText: '暂无团队成员' }}
        />
      </Card>

      <Card title="角色说明" size="small">
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div>
            <Tag color="blue">管理员</Tag>
            <Text type="secondary">可管理规则、模板、发送计划与团队成员。</Text>
          </div>
          <div>
            <Tag color="purple">运营</Tag>
            <Text type="secondary">可处理日常运营动作，但不负责团队配置。</Text>
          </div>
          <div>
            <Tag>只读</Tag>
            <Text type="secondary">只能查看数据，适合观察者角色。</Text>
          </div>
        </Space>
      </Card>

      <Modal
        title="新增团队成员"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={async () => {
          const values = await inviteForm.validateFields();
          createMutation.mutate(values);
        }}
        okText="创建成员"
        confirmLoading={createMutation.isPending}
      >
        <Form form={inviteForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="姓名"
            rules={[{ required: true, whitespace: true, message: '请输入姓名' }]}
          >
            <Input placeholder="张三" />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}
          >
            <Input placeholder="user@company.com" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="viewer">
            <Select
              options={[
                { value: 'admin', label: '管理员' },
                { value: 'operator', label: '运营' },
                { value: 'viewer', label: '只读' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="修改成员"
        open={Boolean(editingMember)}
        onCancel={() => setEditingMember(null)}
        onOk={async () => {
          if (!editingMember) return;
          const values = await editForm.validateFields();
          updateMutation.mutate({
            id: editingMember.id,
            data: {
              name: values.name,
              roles: [values.role],
            },
          });
        }}
        okText="保存"
        confirmLoading={updateMutation.isPending}
      >
        <Form
          form={editForm}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="name"
            label="姓名"
            rules={[{ required: true, whitespace: true, message: '请输入姓名' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色">
            <Select
              options={[
                { value: 'admin', label: '管理员' },
                { value: 'operator', label: '运营' },
                { value: 'viewer', label: '只读' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'TeamSettingsPage';
