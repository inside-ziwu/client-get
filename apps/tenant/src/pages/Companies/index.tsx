import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Drawer,
  Tabs,
  Form,
  Select,
  DatePicker,
  InputNumber,
  Modal,
  Upload,
  Popconfirm,
  Descriptions,
  Badge,
  Typography,
  Tooltip,
  message,
} from 'antd';
import {
  PlusOutlined,
  ImportOutlined,
  DownloadOutlined,
  WarningOutlined,
  UploadOutlined,
  SearchOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { RatingTag } from '@shared/ui';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text } = Typography;

interface CompanyRow {
  id: string;
  name: string;
  country: string;
  industry: string;
  product_tags: string[];
  contact_count: number;
  source: string;
  grade?: string;
  score?: number;
  status: string;
  employee_count?: number;
  website?: string;
  established_year?: number;
  export_record: boolean;
  data_mark: 'normal' | 'precise';
}

const MOCK_COMPANIES: CompanyRow[] = [
  { id: '1', name: 'ABC Electronics GmbH', country: 'DE', industry: 'PCB', product_tags: ['FPC', 'HDI'], contact_count: 3, source: '外贸通', grade: 'A', score: 82, status: 'scored', employee_count: 250, website: 'www.abc-elec.de', established_year: 2005, export_record: true, data_mark: 'normal' },
  { id: '2', name: 'XYZ Circuit Board Inc.', country: 'US', industry: 'PCB', product_tags: ['HDI', '多层板'], contact_count: 0, source: '腾道', grade: 'B', score: 65, status: 'scored', employee_count: 120, website: 'www.xyz-circuit.com', established_year: 2010, export_record: true, data_mark: 'normal' },
  { id: '3', name: '东莞精密电路有限公司', country: 'CN', industry: 'PCB', product_tags: ['FPC'], contact_count: 5, source: '励销云', grade: 'S', score: 95, status: 'selected', employee_count: 800, website: 'www.dgpcb.cn', established_year: 2001, export_record: true, data_mark: 'precise' },
  { id: '4', name: 'Techboard Solutions Ltd', country: 'GB', industry: 'PCB', product_tags: ['刚挠结合板'], contact_count: 2, source: '外贸通', grade: 'C', score: 48, status: 'scored', employee_count: 60, website: 'www.techboard.co.uk', established_year: 2015, export_record: false, data_mark: 'normal' },
  { id: '5', name: 'Nippon PCB Co., Ltd', country: 'JP', industry: 'PCB', product_tags: ['高频板', 'HDI'], contact_count: 4, source: '腾道', grade: 'A', score: 79, status: 'in_plan', employee_count: 450, website: 'www.nipponpcb.jp', established_year: 1998, export_record: true, data_mark: 'normal' },
  { id: '6', name: 'Seoul Circuits Korea', country: 'KR', industry: 'PCB', product_tags: ['多层板'], contact_count: 1, source: '外贸通', grade: 'B', score: 70, status: 'scored', employee_count: 180, website: 'www.seoulcircuits.kr', established_year: 2008, export_record: true, data_mark: 'normal' },
  { id: '7', name: 'Precision PCB Sdn Bhd', country: 'MY', industry: 'PCB', product_tags: ['FPC', '多层板'], contact_count: 0, source: '外贸通', grade: 'D', score: 35, status: 'scored', employee_count: 30, website: '', established_year: 2018, export_record: false, data_mark: 'normal' },
];

const SOURCE_COLOR: Record<string, string> = {
  '外贸通': 'blue',
  '腾道': 'purple',
  '励销云': 'cyan',
};

// 数据源别名——对用户隐藏官方供应商名称
const SOURCE_ALIAS: Record<string, string> = {
  '外贸通': '贸易数据',
  '腾道': '采购数据',
  '励销云': '企业数据',
};


const MOCK_CONTACTS = [
  { id: 'c1', name: 'John Doe', title: '采购经理', email: 'john.doe@abc-elec.de', is_default: true },
  { id: 'c2', name: 'Jane Smith', title: 'CEO', email: 'jane.smith@abc-elec.de', is_default: false },
  { id: 'c3', name: 'Hans Mueller', title: '技术总监', email: 'h.mueller@abc-elec.de', is_default: false },
];

const MOCK_EMAIL_RECORDS = [
  { seq: 1, sent_at: '2026-04-10', status: '已发送', opened: true, clicked: false, replied: false },
  { seq: 2, sent_at: '2026-04-15', status: '已发送', opened: true, clicked: true, replied: true },
];

const MOCK_DIMENSION_SCORES = [
  { name: '国家匹配度', score: 18, max: 20 },
  { name: '产品匹配度', score: 25, max: 30 },
  { name: '公司规模', score: 12, max: 15 },
  { name: '进出口记录', score: 15, max: 15 },
  { name: '联系人丰富度', score: 12, max: 20 },
];

function CompanyDetailDrawer({ company, open, onClose }: { company: CompanyRow | null; open: boolean; onClose: () => void }) {
  const [contacts, setContacts] = useState(MOCK_CONTACTS);

  const setDefaultContact = (id: string) => {
    setContacts(prev => prev.map(c => ({ ...c, is_default: c.id === id })));
    message.success('已设为默认联系人');
  };

  if (!company) return null;
  return (
    <Drawer
      title={
        <Space>
          <Text strong>{company.name}</Text>
          {company.grade && <RatingTag grade={company.grade} />}
          {company.score != null && <Text type="secondary">评分: {company.score}</Text>}
        </Space>
      }
      width="65%"
      open={open}
      onClose={onClose}
    >
      <Tabs
        items={[
          {
            key: 'basic',
            label: '基本信息',
            children: (
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="国家/地区">{company.country}</Descriptions.Item>
                <Descriptions.Item label="行业">{company.industry}</Descriptions.Item>
                <Descriptions.Item label="员工规模">{company.employee_count ?? '—'} 人</Descriptions.Item>
                <Descriptions.Item label="成立年份">{company.established_year ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="工厂性质">OEM + ODM</Descriptions.Item>
                <Descriptions.Item label="官网">
                  {company.website ? <a href={`https://${company.website}`} target="_blank" rel="noreferrer">{company.website}</a> : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="进出口记录">{company.export_record ? '有' : '无'}</Descriptions.Item>
                <Descriptions.Item label="数据来源">
                  <Tag color={SOURCE_COLOR[company.source] ?? 'default'}>{SOURCE_ALIAS[company.source] ?? company.source}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="数据标记" span={2}>
                  <Tag color={company.data_mark === 'precise' ? 'gold' : 'default'}>
                    {company.data_mark === 'precise' ? '精准采集' : '普通采集'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="产品标签" span={2}>
                  <Space wrap>{company.product_tags.map(t => <Tag key={t}>{t}</Tag>)}</Space>
                </Descriptions.Item>
              </Descriptions>
            ),
          },
          {
            key: 'score',
            label: '评分明细',
            children: company.grade ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <Text strong style={{ fontSize: 16 }}>总分: {company.score}</Text>
                  {'  '}
                  <RatingTag grade={company.grade} />
                </div>
                <Table
                  size="small"
                  pagination={false}
                  dataSource={MOCK_DIMENSION_SCORES}
                  rowKey="name"
                  columns={[
                    { title: '维度', dataIndex: 'name' },
                    { title: '得分', dataIndex: 'score' },
                    { title: '满分', dataIndex: 'max' },
                    {
                      title: '占比',
                      render: (_, r) => (
                        <div style={{ background: '#f0f0f0', borderRadius: 4, overflow: 'hidden', width: 100 }}>
                          <div style={{ background: '#1677ff', width: `${(r.score / r.max) * 100}%`, height: 8 }} />
                        </div>
                      ),
                    },
                  ]}
                />
              </Space>
            ) : <Text type="secondary">暂无评分数据</Text>,
          },
          {
            key: 'contacts',
            label: `联系人 (${company.contact_count})`,
            children: company.contact_count > 0 ? (
              <Table
                size="small"
                pagination={false}
                dataSource={contacts.slice(0, company.contact_count)}
                rowKey="id"
                columns={[
                  { title: '姓名', dataIndex: 'name' },
                  { title: '职位', dataIndex: 'title' },
                  { title: '邮箱', dataIndex: 'email' },
                  {
                    title: '默认联系人',
                    dataIndex: 'is_default',
                    width: 100,
                    render: (v) => v ? <Tag color="gold">默认</Tag> : null,
                  },
                  {
                    title: '操作',
                    width: 90,
                    render: (_, r) => !r.is_default ? (
                      <Button type="link" size="small" onClick={() => setDefaultContact(r.id)}>
                        设为默认
                      </Button>
                    ) : null,
                  },
                ]}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                <WarningOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                <div>暂无联系人信息</div>
              </div>
            ),
          },
          {
            key: 'emails',
            label: '邮件记录',
            children: (
              <Table
                size="small"
                pagination={false}
                dataSource={MOCK_EMAIL_RECORDS}
                rowKey="seq"
                columns={[
                  { title: '序列#', dataIndex: 'seq', width: 60 },
                  { title: '发送时间', dataIndex: 'sent_at' },
                  { title: '状态', dataIndex: 'status' },
                  {
                    title: '打开/点击/回复',
                    render: (_, r) => (
                      <Space>
                        <Text type={r.opened ? undefined : 'secondary'}>{r.opened ? '✅' : '❌'}</Text>
                        <Text type={r.clicked ? undefined : 'secondary'}>{r.clicked ? '✅' : '❌'}</Text>
                        <Text type={r.replied ? undefined : 'secondary'}>{r.replied ? '✅' : '❌'}</Text>
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
        ]}
      />
    </Drawer>
  );
}

function ImportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [step, setStep] = useState<'upload' | 'result'>('upload');
  const [uploading, setUploading] = useState(false);

  const handleUpload = () => {
    setUploading(true);
    setTimeout(() => {
      setUploading(false);
      setStep('result');
    }, 1500);
  };

  const handleClose = () => {
    setStep('upload');
    onClose();
  };

  return (
    <Modal title="批量导入公司" open={open} onCancel={handleClose} footer={null} width={480}>
      {step === 'upload' ? (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Button icon={<DownloadOutlined />} onClick={() => message.success('模板已下载')}>
            第一步：下载导入模板
          </Button>
          <Upload.Dragger
            accept=".xlsx,.xls"
            showUploadList={false}
            beforeUpload={() => false}
            onChange={() => {}}
          >
            <p className="ant-upload-drag-icon"><UploadOutlined /></p>
            <p>第二步：上传填写好的 Excel 文件</p>
            <p className="ant-upload-hint">支持 .xlsx / .xls 格式</p>
          </Upload.Dragger>
          <Button type="primary" block loading={uploading} onClick={handleUpload}>
            开始导入
          </Button>
        </Space>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6, padding: 16 }}>
            <Text type="success">✅ 成功导入: 120 条</Text>
          </div>
          <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 6, padding: 16 }}>
            <Text type="warning">⚠ 重复跳过: 15 条</Text>
          </div>
          <div style={{ background: '#fff2f0', border: '1px solid #ffa39e', borderRadius: 6, padding: 16 }}>
            <Text type="danger">❌ 格式错误: 3 条</Text>
          </div>
          <Button type="primary" block onClick={handleClose}>确定</Button>
        </Space>
      )}
    </Modal>
  );
}

export function Component() {
  const [form] = Form.useForm();
  const [selectedCompany, setSelectedCompany] = useState<CompanyRow | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [data] = useState<CompanyRow[]>(MOCK_COMPANIES);

  const columns: ColumnsType<CompanyRow> = [
    {
      title: '公司名称',
      dataIndex: 'name',
      width: 220,
      render: (name, record) => (
        <Space>
          <a onClick={() => { setSelectedCompany(record); setDrawerOpen(true); }}>{name}</a>
          {record.contact_count === 0 && (
            <Tooltip title="缺少联系人邮箱">
              <WarningOutlined style={{ color: '#fa8c16' }} />
            </Tooltip>
          )}
          {record.data_mark === 'precise' && <Tag color="gold" style={{ fontSize: 11 }}>精准</Tag>}
        </Space>
      ),
    },
    {
      title: '国家',
      dataIndex: 'country',
      width: 70,
      render: (c) => <Tag>{c}</Tag>,
    },
    {
      title: '行业',
      dataIndex: 'industry',
      width: 80,
    },
    {
      title: '产品标签',
      dataIndex: 'product_tags',
      render: (tags: string[]) => (
        <Space wrap size={4}>
          {tags.slice(0, 2).map(t => <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>)}
          {tags.length > 2 && <Tag style={{ fontSize: 11 }}>+{tags.length - 2}</Tag>}
        </Space>
      ),
    },
    {
      title: '评级',
      dataIndex: 'grade',
      width: 70,
      render: (g) => g ? <RatingTag grade={g} /> : <Text type="secondary">—</Text>,
    },
    {
      title: '联系人数',
      dataIndex: 'contact_count',
      width: 90,
      render: (n) => (
        <Badge
          count={n}
          showZero
          style={{ backgroundColor: n > 0 ? '#52c41a' : '#d9d9d9' }}
        />
      ),
    },
    {
      title: '数据源',
      dataIndex: 'source',
      width: 90,
      render: (s) => <Tag color={SOURCE_COLOR[s] ?? 'default'} style={{ fontSize: 11 }}>{SOURCE_ALIAS[s] ?? s}</Tag>,
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Space size={4}>
          <Button
            type="link"
            size="small"
            onClick={() => { setSelectedCompany(record); setDrawerOpen(true); }}
          >
            详情
          </Button>
          <Popconfirm
            title="确认将该公司加入黑名单？"
            onConfirm={() => message.success('已加入黑名单')}
          >
            <Button type="link" size="small" danger>黑名单</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const handleSearch = () => {
    message.info('搜索功能将在连接后端后生效');
  };

  const handleReset = () => {
    form.resetFields();
  };

  return (
    <>
      {/* 操作栏 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Button type="primary" icon={<PlusOutlined />}>手动添加</Button>
        <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>批量导入</Button>
        <Button icon={<DownloadOutlined />} onClick={() => message.success('模板已下载')}>下载模板</Button>
      </div>

      {/* 筛选面板 */}
      <div style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: 16, marginBottom: 16 }}>
        <Form form={form} layout="inline" style={{ rowGap: 8 }}>
          <Form.Item name="country" label="国家/地区">
            <Select mode="multiple" placeholder="全部" style={{ width: 160 }} allowClear>
              <Option value="DE">德国</Option>
              <Option value="US">美国</Option>
              <Option value="JP">日本</Option>
              <Option value="GB">英国</Option>
              <Option value="KR">韩国</Option>
              <Option value="MY">马来西亚</Option>
            </Select>
          </Form.Item>
          <Form.Item name="industry" label="行业">
            <Select placeholder="全部" style={{ width: 120 }} allowClear>
              <Option value="PCB">PCB</Option>
              <Option value="电子元器件">电子元器件</Option>
            </Select>
          </Form.Item>
          <Form.Item name="product_tag" label="产品标签">
            <Select placeholder="全部" style={{ width: 140 }} allowClear>
              <Option value="FPC">FPC</Option>
              <Option value="HDI">HDI</Option>
              <Option value="多层板">多层板</Option>
            </Select>
          </Form.Item>
          <Form.Item label="员工规模">
            <Space.Compact>
              <Form.Item name="min_employee" noStyle>
                <InputNumber placeholder="最小" style={{ width: 80 }} min={0} />
              </Form.Item>
              <span style={{ padding: '0 8px', lineHeight: '32px' }}>~</span>
              <Form.Item name="max_employee" noStyle>
                <InputNumber placeholder="最大" style={{ width: 80 }} min={0} />
              </Form.Item>
            </Space.Compact>
          </Form.Item>
          <Form.Item name="export_record" label="进出口记录">
            <Select placeholder="全部" style={{ width: 100 }} allowClear>
              <Option value="yes">有</Option>
              <Option value="no">无</Option>
            </Select>
          </Form.Item>
          <Form.Item name="source" label="数据源">
            <Select placeholder="全部" style={{ width: 120 }} allowClear>
              <Option value="外贸通">{SOURCE_ALIAS['外贸通']}</Option>
              <Option value="腾道">{SOURCE_ALIAS['腾道']}</Option>
              <Option value="励销云">{SOURCE_ALIAS['励销云']}</Option>
            </Select>
          </Form.Item>
          <Form.Item name="data_mark" label="数据标记">
            <Select placeholder="全部" style={{ width: 100 }} allowClear>
              <Option value="normal">普通</Option>
              <Option value="precise">精准</Option>
            </Select>
          </Form.Item>
          <Form.Item name="has_email" label="有联系人邮箱">
            <Select placeholder="全部" style={{ width: 100 }} allowClear>
              <Option value="yes">是</Option>
              <Option value="no">否</Option>
            </Select>
          </Form.Item>
          <Form.Item name="created_at" label="入库时间">
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

      {/* 数据表格 */}
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        size="middle"
        pagination={{
          pageSize: 20,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 条`,
        }}
        scroll={{ x: 900 }}
      />

      {/* 详情抽屉 */}
      <CompanyDetailDrawer
        company={selectedCompany}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />

      {/* 批量导入弹窗 */}
      <ImportModal open={importModalOpen} onClose={() => setImportModalOpen(false)} />
    </>
  );
}

Component.displayName = 'CompaniesPage';
