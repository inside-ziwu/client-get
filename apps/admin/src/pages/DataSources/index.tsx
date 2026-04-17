import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Drawer,
  Tabs,
  Form,
  Input,
  InputNumber,
  Switch,
  Typography,
  Popconfirm,
  message,
  Descriptions,
  Badge,
  Modal,
} from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;

interface DataSource {
  id: string;
  name: string;
  system_alias: string;   // 系统内部编码，如 waimao_tong
  display_alias: string;  // 租户展示别名，如 贸易数据
  usage: string;
  account_count: number;
  is_active: boolean;
  daily_quota: number;
  today_used: number;
}

interface Account {
  id: string;
  username: string;
  account_no?: string;
  is_active: boolean;
  daily_quota: number;
  today_used: number;
  consecutive_errors: number;
  last_used_at?: string;
  // 账号级采集频率
  request_interval: number;   // 秒
  batch_size: number;
  window_start: string;
  window_end: string;
}

const MOCK_SOURCES: DataSource[] = [
  { id: 's1', name: '网易外贸通', system_alias: 'waimao_tong', display_alias: '贸易数据', usage: '公司信息搜索', account_count: 3, is_active: true, daily_quota: 1000, today_used: 342 },
  { id: 's2', name: '腾道', system_alias: 'tengdao', display_alias: '采购数据', usage: '海关进出口数据', account_count: 2, is_active: true, daily_quota: 500, today_used: 120 },
  { id: 's3', name: '励销云', system_alias: 'lixiaoyun', display_alias: '企业数据', usage: '精准客户反查', account_count: 1, is_active: true, daily_quota: 200, today_used: 87 },
];

const MOCK_ACCOUNTS: Account[] = [
  { id: 'a1', username: 'admin@waimao.com', account_no: 'ACC001', is_active: true, daily_quota: 400, today_used: 150, consecutive_errors: 0, last_used_at: '2026-04-17 14:32', request_interval: 30, batch_size: 100, window_start: '02:00', window_end: '06:00' },
  { id: 'a2', username: 'user2@waimao.com', account_no: 'ACC002', is_active: true, daily_quota: 400, today_used: 130, consecutive_errors: 0, last_used_at: '2026-04-17 14:28', request_interval: 45, batch_size: 80, window_start: '01:00', window_end: '05:00' },
  { id: 'a3', username: 'user3@waimao.com', account_no: 'ACC003', is_active: false, daily_quota: 200, today_used: 62, consecutive_errors: 3, last_used_at: '2026-04-16 09:12', request_interval: 60, batch_size: 50, window_start: '03:00', window_end: '07:00' },
];

function AccountTab() {
  const [addOpen, setAddOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [addForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const openEdit = (account: Account) => {
    setEditingAccount(account);
    editForm.setFieldsValue({
      username: account.username,
      account_no: account.account_no,
      daily_quota: account.daily_quota,
      request_interval: account.request_interval,
      batch_size: account.batch_size,
      window_start: account.window_start,
      window_end: account.window_end,
    });
    setEditOpen(true);
  };

  const cols: ColumnsType<Account> = [
    {
      title: '账号',
      width: 220,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Space size={6}>
            <Text style={{ whiteSpace: 'nowrap' }}>{r.username}</Text>
            {r.consecutive_errors > 0 && <Badge count={r.consecutive_errors} title="连续出错次数" />}
          </Space>
          {r.account_no && (
            <Text type="secondary" style={{ fontSize: 11 }}>编号：{r.account_no}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 70,
      render: (v) => <Switch checked={v} size="small" onChange={() => message.info('状态已更新')} />,
    },
    {
      title: '日配额 / 已用',
      width: 120,
      render: (_, r) => <Text style={{ whiteSpace: 'nowrap' }}>{r.today_used} / {r.daily_quota}</Text>,
    },
    {
      title: '采集频率',
      width: 160,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>间隔 {r.request_interval}s · 批量 {r.batch_size} 条</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>{r.window_start} ~ {r.window_end}</Text>
        </Space>
      ),
    },
    {
      title: '最后使用',
      dataIndex: 'last_used_at',
      width: 140,
      render: (v) => v ?? '—',
    },
    {
      title: '操作',
      width: 110,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除该账号？" onConfirm={() => message.success('已删除')}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <Button icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>添加账号</Button>
      </div>
      <Table rowKey="id" columns={cols} dataSource={MOCK_ACCOUNTS} size="small" pagination={false} scroll={{ x: 700 }} />

      {/* 添加账号 */}
      <Modal
        title="添加账号"
        open={addOpen}
        onOk={() => addForm.validateFields().then(() => { message.success('账号已添加'); setAddOpen(false); addForm.resetFields(); })}
        onCancel={() => { setAddOpen(false); addForm.resetFields(); }}
      >
        <Form form={addForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="username" label="登录邮箱" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Form.Item name="account_no" label="账号编号（选填）"><Input /></Form.Item>
          <Form.Item name="daily_quota" label="日配额" initialValue={400}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item label="采集时间窗口">
            <Space>
              <Form.Item name="window_start" noStyle initialValue="02:00"><Input style={{ width: 90 }} placeholder="HH:mm" /></Form.Item>
              <Text>~</Text>
              <Form.Item name="window_end" noStyle initialValue="06:00"><Input style={{ width: 90 }} placeholder="HH:mm" /></Form.Item>
            </Space>
          </Form.Item>
          <Form.Item name="request_interval" label="请求间隔（秒）" initialValue={30}><InputNumber min={5} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="batch_size" label="批量上限（条/批）" initialValue={100}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>

      {/* 编辑账号（含频率） */}
      <Modal
        title={`编辑账号 — ${editingAccount?.username}`}
        open={editOpen}
        onOk={() => editForm.validateFields().then(() => { message.success('已保存'); setEditOpen(false); })}
        onCancel={() => setEditOpen(false)}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="username" label="登录邮箱" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="account_no" label="账号编号（选填）"><Input /></Form.Item>
          <Form.Item name="daily_quota" label="日配额"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item label="采集时间窗口">
            <Space>
              <Form.Item name="window_start" noStyle><Input style={{ width: 90 }} placeholder="HH:mm" /></Form.Item>
              <Text>~</Text>
              <Form.Item name="window_end" noStyle><Input style={{ width: 90 }} placeholder="HH:mm" /></Form.Item>
            </Space>
          </Form.Item>
          <Form.Item name="request_interval" label="请求间隔（秒）"><InputNumber min={5} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="batch_size" label="批量上限（条/批）"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}

export function Component() {
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sourceForm] = Form.useForm();

  const openConfig = (source: DataSource) => {
    setEditingSource(source);
    sourceForm.setFieldsValue({
      display_alias: source.display_alias,
      usage: source.usage,
      is_active: source.is_active,
    });
    setDrawerOpen(true);
  };

  const columns: ColumnsType<DataSource> = [
    {
      title: '渠道名称',
      dataIndex: 'name',
      render: (name, r) => (
        <Space>
          <Text strong>{name}</Text>
          {!r.is_active && <Tag>已禁用</Tag>}
        </Space>
      ),
    },
    {
      title: '系统编码',
      dataIndex: 'system_alias',
      width: 130,
      render: (v) => <Tag color="default" style={{ fontFamily: 'monospace' }}>{v}</Tag>,
    },
    {
      title: '租户展示别名',
      dataIndex: 'display_alias',
      width: 130,
      render: (v) => <Tag color="blue">{v}</Tag>,
    },
    { title: '用途', dataIndex: 'usage' },
    {
      title: '账号数',
      dataIndex: 'account_count',
      width: 80,
      render: (n) => <Badge count={n} style={{ backgroundColor: '#52c41a' }} />,
    },
    {
      title: '今日用量',
      width: 160,
      render: (_, r) => (
        <Space direction="vertical" size={2}>
          <Text style={{ fontSize: 12 }}>{r.today_used} / {r.daily_quota}</Text>
          <div style={{ background: '#f0f0f0', borderRadius: 4, width: 120, height: 6, overflow: 'hidden' }}>
            <div style={{
              background: r.today_used / r.daily_quota > 0.8 ? '#ff4d4f' : '#1677ff',
              width: `${Math.min((r.today_used / r.daily_quota) * 100, 100)}%`,
              height: '100%',
            }} />
          </div>
        </Space>
      ),
    },
    {
      title: '操作',
      width: 90,
      render: (_, record) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openConfig(record)}>
          配置
        </Button>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />}>添加渠道</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={MOCK_SOURCES} size="middle" pagination={false} />

      <Drawer
        title={`配置 — ${editingSource?.name}`}
        width={680}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={<Button type="primary" onClick={() => { message.success('配置已保存'); setDrawerOpen(false); }}>保存</Button>}
      >
        <Tabs items={[
          {
            key: 'accounts',
            label: '账号管理',
            children: <AccountTab />,
          },
          {
            key: 'basic',
            label: '基本配置',
            children: (
              <Form form={sourceForm} layout="vertical">
                <Form.Item name="display_alias" label="租户展示别名" extra="租户在公司列表、数据标记等处看到的名称，不暴露真实数据源">
                  <Input placeholder="如：贸易数据" style={{ width: 240 }} />
                </Form.Item>
                <Form.Item name="usage" label="用途说明">
                  <Input />
                </Form.Item>
                <Form.Item name="is_active" label="启用状态" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Form>
            ),
          },
          {
            key: 'rules',
            label: '落库规则',
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Descriptions bordered column={1} size="small">
                  <Descriptions.Item label="路径1">直接采集 → shared_companies</Descriptions.Item>
                  <Descriptions.Item label="路径2">竞品反查 → competitor → shared_companies</Descriptions.Item>
                  <Descriptions.Item label="去重策略">数据源ID为主，公司名辅助</Descriptions.Item>
                </Descriptions>
                <Text type="secondary" style={{ fontSize: 12 }}>落库规则由平台统一维护，不支持自定义修改。</Text>
              </Space>
            ),
          },
        ]} />
      </Drawer>
    </>
  );
}

Component.displayName = 'DataSourcesPage';
