import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Typography,
  message,
  Tabs,
  Descriptions,
  Badge,
  InputNumber,
  Switch,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  ArrowLeftOutlined,
  PlusCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;
const { Option } = Select;

interface TenantRow {
  id: string;
  name: string;
  industry: string;
  domain_count: number;
  ai_balance: number;
  status: 'active' | 'suspended' | 'archived';
  created_at: string;
  contact: string;
}

interface Domain {
  id: string;
  domain: string;
  dns_verified: boolean;
  warmup_stage: number | null;
  today_remaining: string;
}

interface TeamMember {
  id: string;
  username: string;
  role: string;
  status: 'active' | 'disabled';
}

interface BalanceRecord {
  id: string;
  date: string;
  amount: number;
  operated_by: string;
}

const MOCK_TENANTS: TenantRow[] = [
  { id: 't1', name: 'xxx科技有限公司', industry: 'PCB', domain_count: 2, ai_balance: 520, status: 'active', created_at: '2026-01-15', contact: 'admin@xxx.com' },
  { id: 't2', name: 'yyy电子贸易', industry: 'PCB', domain_count: 1, ai_balance: 80, status: 'active', created_at: '2026-02-20', contact: 'admin@yyy.com' },
  { id: 't3', name: 'zzz进出口集团', industry: '电子元器件', domain_count: 3, ai_balance: 1250, status: 'active', created_at: '2026-03-01', contact: 'admin@zzz.com' },
  { id: 't4', name: 'aaa外贸科技', industry: 'PCB', domain_count: 0, ai_balance: 0, status: 'suspended', created_at: '2025-12-10', contact: 'admin@aaa.com' },
];

const MOCK_DOMAINS: Domain[] = [
  { id: 'd1', domain: 'mail.xxx.com', dns_verified: true, warmup_stage: 3, today_remaining: '67/100' },
  { id: 'd2', domain: 'mx2.xxx.com', dns_verified: false, warmup_stage: null, today_remaining: '—' },
];

const MOCK_TEAM: TeamMember[] = [
  { id: 'u1', username: 'admin@xxx.com', role: '管理员', status: 'active' },
  { id: 'u2', username: 'op01@xxx.com', role: '业务员', status: 'active' },
  { id: 'u3', username: 'viewer01@xxx.com', role: '只读观察者', status: 'active' },
];

const MOCK_BALANCE_RECORDS: BalanceRecord[] = [
  { id: 'b1', date: '2026-04-15', amount: 500, operated_by: '运营人员 admin' },
  { id: 'b2', date: '2026-04-01', amount: 200, operated_by: '运营人员 admin' },
];

const STATUS_CONFIG = {
  active: { color: 'success', label: '正常' },
  suspended: { color: 'warning', label: '已暂停' },
  archived: { color: 'default', label: '已归档' },
} as const;

function TenantDetailPage({ tenant, onBack }: { tenant: TenantRow; onBack: () => void }) {
  const [rechargeOpen, setRechargeOpen] = useState(false);
  const [domainDrawerOpen, setDomainDrawerOpen] = useState(false);
  const [rechargeAmount, setRechargeAmount] = useState<number>(500);
  const [addUserOpen, setAddUserOpen] = useState(false);
  const [form] = Form.useForm();

  const domainColumns: ColumnsType<Domain> = [
    { title: '域名', dataIndex: 'domain', render: (v) => <Text strong>{v}</Text> },
    {
      title: 'DNS验证',
      dataIndex: 'dns_verified',
      width: 100,
      render: (v) => v ? <Badge status="success" text="已验证" /> : <Badge status="warning" text="待验证" />,
    },
    {
      title: '预热阶段', dataIndex: 'warmup_stage', width: 100,
      render: (v) => v != null ? <Tag color="blue">阶段{v}</Tag> : <Text type="secondary">—</Text>,
    },
    { title: '今日剩余', dataIndex: 'today_remaining', width: 100 },
    { title: '操作', width: 60, render: () => <Button type="link" size="small">编辑</Button> },
  ];

  const teamColumns: ColumnsType<TeamMember> = [
    { title: '用户名', dataIndex: 'username' },
    { title: '角色', dataIndex: 'role', render: (v) => <Tag>{v}</Tag> },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v) => <Switch checked={v === 'active'} size="small" onChange={() => message.info('状态已更新')} />,
    },
    { title: '操作', width: 60, render: () => <Button type="link" size="small">编辑</Button> },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="text" icon={<ArrowLeftOutlined />} onClick={onBack}>返回租户列表</Button>
      </div>

      <Descriptions
        title={tenant.name}
        bordered
        column={2}
        style={{ marginBottom: 24 }}
        extra={<Tag color={STATUS_CONFIG[tenant.status].color}>{STATUS_CONFIG[tenant.status].label}</Tag>}
      >
        <Descriptions.Item label="行业">{tenant.industry}</Descriptions.Item>
        <Descriptions.Item label="联系人">{tenant.contact}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{tenant.created_at}</Descriptions.Item>
        <Descriptions.Item label="AI余额">¥{tenant.ai_balance.toFixed(2)}</Descriptions.Item>
      </Descriptions>

      <Tabs
        items={[
          {
            key: 'domains',
            label: '域名管理',
            children: (
              <>
                <div style={{ marginBottom: 12 }}>
                  <Button icon={<PlusOutlined />} onClick={() => setDomainDrawerOpen(true)}>添加域名</Button>
                </div>
                <Table rowKey="id" columns={domainColumns} dataSource={MOCK_DOMAINS} size="small" pagination={false} />
              </>
            ),
          },
          {
            key: 'team',
            label: '团队账号',
            children: (
              <>
                <div style={{ marginBottom: 12 }}>
                  <Button icon={<PlusOutlined />} onClick={() => setAddUserOpen(true)}>新建账号</Button>
                </div>
                <Table rowKey="id" columns={teamColumns} dataSource={MOCK_TEAM} size="small" pagination={false} />
              </>
            ),
          },
          {
            key: 'balance',
            label: 'AI余额',
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 8, padding: 20 }}>
                  <Text type="secondary">当前余额</Text>
                  <div style={{ fontSize: 28, fontWeight: 600, color: '#389e0d', marginTop: 4 }}>
                    ¥{tenant.ai_balance.toFixed(2)}
                  </div>
                  <Button
                    type="primary"
                    style={{ marginTop: 12 }}
                    icon={<PlusCircleOutlined />}
                    onClick={() => setRechargeOpen(true)}
                  >
                    充值
                  </Button>
                </div>
                <div>
                  <Title level={5}>充值记录</Title>
                  <Table
                    rowKey="id"
                    dataSource={MOCK_BALANCE_RECORDS}
                    size="small"
                    pagination={false}
                    columns={[
                      { title: '日期', dataIndex: 'date' },
                      { title: '充值金额', dataIndex: 'amount', render: (v) => <Text style={{ color: '#389e0d' }}>+¥{v}</Text> },
                      { title: '操作人', dataIndex: 'operated_by' },
                    ]}
                  />
                </div>
              </Space>
            ),
          },
        ]}
      />

      {/* 充值弹窗 */}
      <Modal
        title="为租户充值AI额度"
        open={rechargeOpen}
        onOk={() => { message.success(`充值 ¥${rechargeAmount} 成功`); setRechargeOpen(false); }}
        onCancel={() => setRechargeOpen(false)}
        okText="确认充值"
      >
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="充值金额（元）" required>
            <InputNumber
              value={rechargeAmount}
              min={1}
              step={100}
              style={{ width: '100%' }}
              prefix="¥"
              onChange={(v) => setRechargeAmount(v ?? 500)}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 添加域名 Drawer */}
      <Drawer
        title="添加域名"
        width={480}
        open={domainDrawerOpen}
        onClose={() => setDomainDrawerOpen(false)}
        extra={<Button type="primary" onClick={() => { message.success('域名已添加'); setDomainDrawerOpen(false); }}>保存</Button>}
      >
        <Form layout="vertical">
          <Form.Item label="域名" rules={[{ required: true }]}><Input placeholder="mail.company.com" /></Form.Item>
          <Form.Item label="SPF 记录"><Input /></Form.Item>
          <Form.Item label="DKIM 记录"><Input /></Form.Item>
          <Form.Item label="DMARC 记录"><Input /></Form.Item>
          <Button onClick={() => message.info('DNS验证已触发')}>验证 DNS</Button>
        </Form>
      </Drawer>

      {/* 新建账号弹窗 */}
      <Modal
        title="新建账号"
        open={addUserOpen}
        onOk={() => { form.validateFields().then(() => { message.success('账号已创建'); setAddUserOpen(false); form.resetFields(); }); }}
        onCancel={() => { setAddUserOpen(false); form.resetFields(); }}
        okText="创建"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="email" label="邮箱" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select>
              <Option value="admin">管理员</Option>
              <Option value="operator">业务员</Option>
              <Option value="viewer">只读观察者</Option>
            </Select>
          </Form.Item>
          <Form.Item name="password" label="初始密码" rules={[{ required: true }]}><Input.Password /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

export function Component() {
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<TenantRow | null>(null);
  const [form] = Form.useForm();

  if (selectedTenant) {
    return <TenantDetailPage tenant={selectedTenant} onBack={() => setSelectedTenant(null)} />;
  }

  const columns: ColumnsType<TenantRow> = [
    {
      title: '公司名称',
      dataIndex: 'name',
      render: (name) => <Text strong>{name}</Text>,
    },
    { title: '行业', dataIndex: 'industry', render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '域名数', dataIndex: 'domain_count', width: 80, render: (n) => <Badge count={n} showZero style={{ backgroundColor: n > 0 ? '#1677ff' : '#d9d9d9' }} /> },
    {
      title: 'AI余额', dataIndex: 'ai_balance', width: 100,
      render: (v) => (
        <Text type={v < 100 ? 'danger' : undefined}>¥{v.toFixed(2)}</Text>
      ),
    },
    {
      title: '状态', dataIndex: 'status', width: 90,
      render: (v: keyof typeof STATUS_CONFIG) => <Badge status={STATUS_CONFIG[v].color} text={STATUS_CONFIG[v].label} />,
    },
    { title: '创建时间', dataIndex: 'created_at', width: 110 },
    {
      title: '操作', width: 80,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => setSelectedTenant(record)}>详情</Button>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新建租户
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={MOCK_TENANTS} size="middle" />

      <Modal
        title="新建租户"
        open={createOpen}
        onOk={() => form.validateFields().then(() => { message.success('租户已创建，系统正在初始化...'); setCreateOpen(false); form.resetFields(); })}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        okText="创建"
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="公司名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="industry" label="所属行业" rules={[{ required: true }]}>
            <Select>
              <Option value="PCB">PCB</Option>
              <Option value="电子元器件">电子元器件</Option>
            </Select>
          </Form.Item>
          <Form.Item name="contact_name" label="联系人" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="contact_phone" label="联系方式" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="admin_email" label="初始管理员账号" rules={[{ required: true, type: 'email' }]}><Input /></Form.Item>
          <Form.Item name="admin_password" label="初始密码" rules={[{ required: true, min: 8 }]}><Input.Password /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

Component.displayName = 'TenantsPage';
