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
  Switch,
  Typography,
  Popconfirm,
  Upload,
  message,
  Drawer,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  ImportOutlined,
  DownloadOutlined,
  EditOutlined,
  DeleteOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;
const { Option } = Select;

interface IntelSource {
  id: string;
  name: string;
  url: string;
  industry: string;
  category: string;
  frequency: string;
  is_active: boolean;
  last_fetched_at?: string;
  error_count: number;
}

const MOCK_SOURCES: IntelSource[] = [
  { id: 'i1', name: 'PCB行业资讯', url: 'https://www.pcbinfo.com/rss', industry: 'PCB', category: '行业动态', frequency: '每日', is_active: true, last_fetched_at: '2026-04-17 08:00', error_count: 0 },
  { id: 'i2', name: '全球PCB市场报告', url: 'https://pcbmarket.report/feed', industry: 'PCB', category: '市场分析', frequency: '每周', is_active: true, last_fetched_at: '2026-04-15 09:00', error_count: 0 },
  { id: 'i3', name: '覆铜板价格动态', url: 'https://copperclad.price/feed', industry: 'PCB', category: '原材料', frequency: '每日', is_active: true, last_fetched_at: '2026-04-17 07:30', error_count: 1 },
  { id: 'i4', name: '电子元器件行业周报', url: 'https://ec-weekly.com/rss', industry: '电子元器件', category: '行业动态', frequency: '每周', is_active: false, last_fetched_at: '2026-04-10 09:00', error_count: 5 },
];


export function Component() {
  const [editOpen, setEditOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<IntelSource | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [form] = Form.useForm();

  const openEdit = (source?: IntelSource) => {
    setEditingSource(source ?? null);
    if (source) {
      form.setFieldsValue(source);
    } else {
      form.resetFields();
    }
    setEditOpen(true);
  };

  const handleSave = () => {
    form.validateFields().then(() => {
      message.success(editingSource ? '情报源已更新' : '情报源已添加');
      setEditOpen(false);
    });
  };

  const columns: ColumnsType<IntelSource> = [
    {
      title: 'URL',
      dataIndex: 'url',
      width: 240,
      render: (v) => (
        <Text style={{ fontSize: 12 }} copyable ellipsis={{ tooltip: v }}>{v}</Text>
      ),
    },
    { title: '名称', dataIndex: 'name' },
    { title: '行业', dataIndex: 'industry', render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '分类标签', dataIndex: 'category', render: (v) => <Tag>{v}</Tag> },
    { title: '采集频率', dataIndex: 'frequency', width: 90 },
    {
      title: '状态', width: 80,
      render: (_, r) => (
        <Switch
          checked={r.is_active}
          size="small"
          onChange={() => message.info('状态已切换')}
        />
      ),
    },
    {
      title: '最后采集',
      dataIndex: 'last_fetched_at',
      render: (v, r) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>{v ?? '从未'}</Text>
          {r.error_count > 0 && <Text type="danger" style={{ fontSize: 11 }}>出错 {r.error_count} 次</Text>}
        </Space>
      ),
    },
    {
      title: '操作', width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此情报源？" onConfirm={() => message.success('已删除')}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openEdit()}>手动添加</Button>
        <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>Excel批量导入</Button>
        <Button icon={<DownloadOutlined />} onClick={() => message.success('模板已下载')}>下载模板</Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={MOCK_SOURCES} size="middle" />

      {/* 编辑/新增弹窗 */}
      <Drawer
        title={editingSource ? '编辑情报源' : '添加情报源'}
        width={480}
        open={editOpen}
        onClose={() => setEditOpen(false)}
        extra={<Button type="primary" onClick={handleSave}>保存</Button>}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="url" label="RSS / 网站 URL" rules={[{ required: true }]}>
            <Input prefix={<GlobalOutlined />} placeholder="https://example.com/rss" />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="industry" label="行业" rules={[{ required: true }]}>
            <Select>
              <Option value="PCB">PCB</Option>
              <Option value="电子元器件">电子元器件</Option>
            </Select>
          </Form.Item>
          <Form.Item name="category" label="分类标签">
            <Select>
              <Option value="行业动态">行业动态</Option>
              <Option value="市场分析">市场分析</Option>
              <Option value="原材料">原材料</Option>
              <Option value="展会">展会</Option>
            </Select>
          </Form.Item>
          <Form.Item name="frequency" label="采集频率">
            <Select>
              <Option value="每日">每日</Option>
              <Option value="每周">每周</Option>
              <Option value="每月">每月</Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked" initialValue>
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>

      {/* Excel导入弹窗 */}
      <Modal
        title="Excel批量导入情报源"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        footer={null}
        width={480}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Button icon={<DownloadOutlined />} block onClick={() => message.success('模板已下载')}>
            下载导入模板
          </Button>
          <Upload.Dragger accept=".xlsx,.xls" showUploadList={false} beforeUpload={() => false}>
            <p className="ant-upload-drag-icon"><ImportOutlined /></p>
            <p>点击或拖拽上传 Excel 文件</p>
            <p className="ant-upload-hint">支持 .xlsx / .xls 格式</p>
          </Upload.Dragger>
          <Alert
            type="info"
            showIcon
            message="导入字段：URL / 名称 / 行业 / 分类 / 频率"
          />
          <Button type="primary" block onClick={() => { message.success('导入成功：5条 / 重复跳过：0条 / 格式错误：0条'); setImportOpen(false); }}>
            开始导入
          </Button>
        </Space>
      </Modal>
    </>
  );
}

Component.displayName = 'IntelligenceSourcesPage';
