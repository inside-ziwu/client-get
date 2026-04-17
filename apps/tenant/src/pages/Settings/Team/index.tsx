import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  message,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;
const { Option } = Select;

type Role = 'owner' | 'admin' | 'member';
type MemberStatus = 'active' | 'invited' | 'disabled';

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: MemberStatus;
  joined_at: string;
  last_active?: string;
}

const ROLE_LABELS: Record<Role, string> = {
  owner: '所有者',
  admin: '管理员',
  member: '成员',
};

const ROLE_COLORS: Record<Role, string> = {
  owner: 'gold',
  admin: 'blue',
  member: 'default',
};

const STATUS_COLORS: Record<MemberStatus, 'success' | 'warning' | 'error'> = {
  active: 'success',
  invited: 'warning',
  disabled: 'error',
};

const STATUS_LABELS: Record<MemberStatus, string> = {
  active: '已激活',
  invited: '邀请中',
  disabled: '已禁用',
};

const MOCK_MEMBERS: TeamMember[] = [
  { id: 'm1', name: '张伟', email: 'zhang.wei@company.com', role: 'owner', status: 'active', joined_at: '2026-01-01', last_active: '2026-04-17' },
  { id: 'm2', name: '李娜', email: 'li.na@company.com', role: 'admin', status: 'active', joined_at: '2026-02-10', last_active: '2026-04-16' },
  { id: 'm3', name: '王磊', email: 'wang.lei@company.com', role: 'member', status: 'active', joined_at: '2026-03-01', last_active: '2026-04-15' },
  { id: 'm4', name: '赵敏', email: 'zhao.min@company.com', role: 'member', status: 'invited', joined_at: '2026-04-10' },
];

const ROLE_DESCRIPTIONS: { role: Role; label: string; perms: string[] }[] = [
  {
    role: 'owner',
    label: '所有者',
    perms: ['管理团队成员和角色', '管理账户和计费', '所有管理员权限'],
  },
  {
    role: 'admin',
    label: '管理员',
    perms: ['创建和管理发送计划', '编辑评分规则和关键词', '查看所有数据和报告', '管理邮件模板'],
  },
  {
    role: 'member',
    label: '成员',
    perms: ['查看公司和联系人列表', '查看发送计划和报告', '使用模板（不可编辑）'],
  },
];

export function Component() {
  const [members, setMembers] = useState<TeamMember[]>(MOCK_MEMBERS);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [form] = Form.useForm();

  const handleInvite = () => {
    form.validateFields().then((values) => {
      const newMember: TeamMember = {
        id: `m${Date.now()}`,
        name: values.email.split('@')[0],
        email: values.email,
        role: values.role,
        status: 'invited',
        joined_at: new Date().toISOString().slice(0, 10),
      };
      setMembers((prev) => [...prev, newMember]);
      message.success(`已向 ${values.email} 发送邀请邮件`);
      setInviteOpen(false);
      form.resetFields();
    }).catch(() => {});
  };

  const handleDisable = (id: string) => {
    setMembers((prev) => prev.map((m) => m.id === id ? { ...m, status: 'disabled' } : m));
    message.success('已禁用该成员');
  };

  const handleEnable = (id: string) => {
    setMembers((prev) => prev.map((m) => m.id === id ? { ...m, status: 'active' } : m));
    message.success('已重新启用该成员');
  };

  const columns: ColumnsType<TeamMember> = [
    {
      title: '成员',
      render: (_, r) => (
        <Space>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#e6f4ff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <UserOutlined style={{ color: '#1677ff' }} />
          </div>
          <div>
            <div><Text strong>{r.name}</Text></div>
            <div><Text type="secondary" style={{ fontSize: 12 }}>{r.email}</Text></div>
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      width: 100,
      render: (v: Role) => <Tag color={ROLE_COLORS[v]}>{ROLE_LABELS[v]}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: MemberStatus) => (
        <Badge status={STATUS_COLORS[v]} text={STATUS_LABELS[v]} />
      ),
    },
    {
      title: '加入时间',
      dataIndex: 'joined_at',
      width: 110,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '最后活跃',
      dataIndex: 'last_active',
      width: 110,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v ?? '—'}</Text>,
    },
    {
      title: '操作',
      width: 140,
      render: (_, r) => (
        <Space size={4}>
          {r.role !== 'owner' && r.status !== 'disabled' && (
            <Popconfirm title="确认禁用此成员？" onConfirm={() => handleDisable(r.id)}>
              <Button type="link" size="small" danger>禁用</Button>
            </Popconfirm>
          )}
          {r.status === 'disabled' && (
            <Button type="link" size="small" onClick={() => handleEnable(r.id)}>启用</Button>
          )}
          {r.status === 'invited' && (
            <Button type="link" size="small" onClick={() => message.success('已重新发送邀请')}>
              重发邀请
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>团队管理</Title>
          <Text type="secondary">管理团队成员、角色分配和访问权限</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setInviteOpen(true)}>
          邀请成员
        </Button>
      </div>

      <Card size="small">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={members}
          size="middle"
          pagination={false}
        />
      </Card>

      {/* 角色权限说明 */}
      <Card title="角色权限说明" size="small">
        <div style={{ display: 'flex', gap: 16 }}>
          {ROLE_DESCRIPTIONS.map((r) => (
            <div
              key={r.role}
              style={{
                flex: 1,
                padding: '12px 16px',
                border: '1px solid #f0f0f0',
                borderRadius: 6,
                background: '#fafafa',
              }}
            >
              <Tag color={ROLE_COLORS[r.role]} style={{ marginBottom: 8 }}>{r.label}</Tag>
              <Space direction="vertical" size={4}>
                {r.perms.map((p) => (
                  <Text key={p} style={{ fontSize: 12 }}>• {p}</Text>
                ))}
              </Space>
            </div>
          ))}
        </div>
      </Card>

      <Modal
        title="邀请团队成员"
        open={inviteOpen}
        onOk={handleInvite}
        onCancel={() => { setInviteOpen(false); form.resetFields(); }}
        okText="发送邀请"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="email" label="邮箱地址" rules={[{ required: true, type: 'email', message: '请输入有效的邮箱地址' }]}>
            <Input placeholder="colleague@company.com" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="member" rules={[{ required: true }]}>
            <Select>
              <Option value="admin">管理员</Option>
              <Option value="member">成员</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'TeamSettingsPage';
