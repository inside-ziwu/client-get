import { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Typography,
  Progress,
  Popconfirm,
  message,
  Empty,
  Form,
  Select,
  Input,
  DatePicker,
} from 'antd';
import {
  PlusOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { StatusTag } from '@shared/ui';
import type { SendingPlanStatus } from '@shared/types';

const { RangePicker } = DatePicker;
const { Option } = Select;

const { Text } = Typography;

interface PlanRow {
  id: string;
  name: string;
  status: SendingPlanStatus;
  total_recipients: number;
  sent_count: number;
  scheduled_at?: string;
  started_at?: string;
  created_at: string;
}

const MOCK_PLANS: PlanRow[] = [
  { id: 'p1', name: '德国PCB采购商首轮开发', status: 'running', total_recipients: 69, sent_count: 54, started_at: '2026-04-10', created_at: '2026-04-09' },
  { id: 'p2', name: '美国电路板供应商触达', status: 'running', total_recipients: 80, sent_count: 28, started_at: '2026-04-14', created_at: '2026-04-13' },
  { id: 'p3', name: '英国工厂跟进序列', status: 'paused', total_recipients: 30, sent_count: 14, created_at: '2026-04-08' },
  { id: 'p4', name: 'Q1全球PCB采购商推广', status: 'completed', total_recipients: 200, sent_count: 200, created_at: '2026-03-01' },
  { id: 'p5', name: '日本精密电路合作方开发', status: 'draft', total_recipients: 0, sent_count: 0, scheduled_at: '2026-04-20', created_at: '2026-04-17' },
  { id: 'p6', name: '韩国供应链触达计划', status: 'scheduled', total_recipients: 45, sent_count: 0, scheduled_at: '2026-04-19', created_at: '2026-04-16' },
];

export function Component() {
  const navigate = useNavigate();
  const [data] = useState<PlanRow[]>(MOCK_PLANS);
  const [filterForm] = Form.useForm();

  const handleSearch = () => {
    message.info('搜索功能将在连接后端后生效');
  };

  const handleReset = () => {
    filterForm.resetFields();
  };

  const getProgress = (r: PlanRow) =>
    r.total_recipients > 0 ? Math.round((r.sent_count / r.total_recipients) * 100) : 0;

  const columns: ColumnsType<PlanRow> = [
    {
      title: '计划名称',
      dataIndex: 'name',
      render: (name, r) => (
        <a onClick={() => navigate(`/send-plans/${r.id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: SendingPlanStatus) => <StatusTag status={s} />,
    },
    {
      title: '收件人',
      width: 90,
      render: (_, r) => (
        <Text>
          {r.total_recipients > 0 ? `${r.sent_count}/${r.total_recipients}人` : `—`}
        </Text>
      ),
    },
    {
      title: '进度',
      width: 160,
      render: (_, r) => (
        r.status === 'draft' ? <Text type="secondary">—</Text> : (
          <Progress
            percent={getProgress(r)}
            size="small"
            strokeColor={r.status === 'completed' ? '#52c41a' : '#1677ff'}
            style={{ marginBottom: 0 }}
          />
        )
      ),
    },
    {
      title: '时间',
      width: 110,
      render: (_, r) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {r.started_at ? `${r.started_at} 开始` : r.scheduled_at ? `${r.scheduled_at} 排期` : r.created_at}
        </Text>
      ),
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space size={4}>
          {record.status === 'running' && (
            <Popconfirm title="确认暂停此计划？" onConfirm={() => message.success('已暂停')}>
              <Button type="link" size="small" icon={<PauseCircleOutlined />}>暂停</Button>
            </Popconfirm>
          )}
          {record.status === 'paused' && (
            <Popconfirm title="确认恢复此计划？" onConfirm={() => message.success('已恢复')}>
              <Button type="link" size="small" icon={<PlayCircleOutlined />}>恢复</Button>
            </Popconfirm>
          )}
          {record.status === 'draft' && (
            <Button type="link" size="small" onClick={() => navigate(`/send-plans/new`)}>编辑</Button>
          )}
          <Button type="link" size="small" onClick={() => navigate(`/send-plans/${record.id}`)}>详情</Button>
          {(record.status === 'draft' || record.status === 'cancelled') && (
            <Popconfirm title="确认删除？" onConfirm={() => message.success('已删除')}>
              <Button type="link" size="small" danger>删除</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/send-plans/new')}>
          新建计划
        </Button>
      </div>

      {/* 筛选面板 */}
      <div style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: '12px 16px', marginBottom: 16 }}>
        <Form form={filterForm} layout="inline" style={{ rowGap: 8 }}>
          <Form.Item name="status" label="状态">
            <Select mode="multiple" placeholder="全部" style={{ width: 220 }} allowClear>
              <Option value="running"><StatusTag status="running" /></Option>
              <Option value="paused"><StatusTag status="paused" /></Option>
              <Option value="scheduled"><StatusTag status="scheduled" /></Option>
              <Option value="completed"><StatusTag status="completed" /></Option>
              <Option value="draft"><StatusTag status="draft" /></Option>
              <Option value="cancelled"><StatusTag status="cancelled" /></Option>
            </Select>
          </Form.Item>
          <Form.Item name="keyword">
            <Input placeholder="搜索计划名称" prefix={<SearchOutlined />} style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="created_at" label="创建时间">
            <RangePicker style={{ width: 240 }} />
          </Form.Item>
        </Form>
        <div style={{ marginTop: 12 }}>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
          </Space>
        </div>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        size="middle"
        locale={{ emptyText: <Empty description={'还没有发送计划，点击"新建计划"开始'}><Button type="primary" onClick={() => navigate('/send-plans/new')}>新建计划</Button></Empty> }}
      />
    </>
  );
}

Component.displayName = 'SendPlansPage';
