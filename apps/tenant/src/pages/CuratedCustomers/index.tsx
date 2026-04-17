import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Drawer,
  Form,
  Select,
  Input,
  Modal,
  Typography,
  Badge,
  Dropdown,
  Divider,
  Alert,
  message,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  ExportOutlined,
  MoreOutlined,
  SearchOutlined,
  ReloadOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';
import { Link } from 'react-router-dom';
import { RatingTag, ContactStatusTag } from '@shared/ui';
import type { TenantContactStatus } from '@shared/types';

const { Text } = Typography;
const { Option } = Select;

interface GroupItem {
  id: string;
  name: string;
  count: number;
}

interface ProspectRow {
  id: string;
  company_name: string;
  company_grade: string;
  contact_name: string;
  contact_email: string;
  contact_title: string;
  status: TenantContactStatus;
  country: string;
  product_tags: string[];
  data_mark: 'normal' | 'precise';
}

const MOCK_GROUPS: GroupItem[] = [
  { id: 'all', name: '全部客户', count: 1203 },
  { id: 'g1', name: '德国A级客户', count: 45 },
  { id: 'g2', name: '美国PCB采购商', count: 78 },
  { id: 'g3', name: '优先跟进', count: 23 },
  { id: 'g4', name: '日本精密客户', count: 31 },
];

const MOCK_PROSPECTS: ProspectRow[] = [
  { id: 'p1', company_name: 'ABC Electronics GmbH', company_grade: 'S', contact_name: 'John Doe', contact_email: 'john@abc.de', contact_title: '采购经理', status: 'replied', country: 'DE', product_tags: ['FPC', 'HDI'], data_mark: 'precise' },
  { id: 'p2', company_name: 'XYZ Circuit Board Inc.', company_grade: 'A', contact_name: 'Mike Johnson', contact_email: 'mike@xyz.com', contact_title: 'CEO', status: 'contacted', country: 'US', product_tags: ['HDI'], data_mark: 'normal' },
  { id: 'p3', company_name: 'Nippon PCB Co., Ltd', company_grade: 'A', contact_name: 'Tanaka Hiroshi', contact_email: 'tanaka@nipponpcb.jp', contact_title: '技术总监', status: 'in_plan', country: 'JP', product_tags: ['高频板', 'HDI'], data_mark: 'normal' },
  { id: 'p4', company_name: 'Seoul Circuits Korea', company_grade: 'B', contact_name: 'Kim Minjun', contact_email: 'km@seoulcircuits.kr', contact_title: '采购经理', status: 'available', country: 'KR', product_tags: ['多层板'], data_mark: 'normal' },
  { id: 'p5', company_name: 'Techboard Solutions Ltd', company_grade: 'C', contact_name: 'James Brown', contact_email: 'jb@techboard.co.uk', contact_title: '采购总监', status: 'bounced', country: 'GB', product_tags: ['刚挠结合板'], data_mark: 'normal' },
  { id: 'p6', company_name: '东莞精密电路有限公司', company_grade: 'S', contact_name: '李明', contact_email: 'liming@dgpcb.cn', contact_title: '总经理', status: 'replied', country: 'CN', product_tags: ['FPC'], data_mark: 'precise' },
];

function GroupPanel({
  groups,
  selectedGroupId,
  onSelect,
  onCreateGroup,
  onRenameGroup,
  onDeleteGroup,
}: {
  groups: GroupItem[];
  selectedGroupId: string;
  onSelect: (id: string) => void;
  onCreateGroup: () => void;
  onRenameGroup: (id: string) => void;
  onDeleteGroup: (id: string) => void;
}) {
  return (
    <div style={{ width: 240, minWidth: 240, borderRight: '1px solid #f0f0f0', paddingRight: 16, marginRight: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Text strong>群组管理</Text>
        <Button type="text" size="small" icon={<PlusOutlined />} onClick={onCreateGroup}>创建群组</Button>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {groups.map((g) => {
          const isSelected = g.id === selectedGroupId;
          const contextMenu: MenuProps['items'] = g.id !== 'all' ? [
            { key: 'rename', label: '重命名' },
            { key: 'merge', label: '合并群组' },
            { key: 'divider', type: 'divider' },
            { key: 'delete', label: '删除群组', danger: true },
          ] : [];

          const handleContextAction: MenuProps['onClick'] = ({ key }) => {
            if (key === 'rename') onRenameGroup(g.id);
            else if (key === 'delete') onDeleteGroup(g.id);
            else if (key === 'merge') message.info('合并功能即将上线');
          };

          return (
            <div
              key={g.id}
              onClick={() => onSelect(g.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 8px',
                borderRadius: 6,
                cursor: 'pointer',
                background: isSelected ? '#e6f4ff' : 'transparent',
                color: isSelected ? '#1677ff' : undefined,
              }}
            >
              <Space size={6}>
                {isSelected ? <FolderOpenOutlined /> : <FolderOutlined />}
                <Text style={{ color: isSelected ? '#1677ff' : undefined }}>{g.name}</Text>
              </Space>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Badge count={g.count} style={{ backgroundColor: isSelected ? '#1677ff' : '#d9d9d9' }} />
                {g.id !== 'all' && (
                  <Dropdown menu={{ items: contextMenu, onClick: handleContextAction }} trigger={['click']}>
                    <Button
                      type="text"
                      size="small"
                      icon={<MoreOutlined />}
                      onClick={(e) => e.stopPropagation()}
                      style={{ opacity: 0.6 }}
                    />
                  </Dropdown>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Component() {
  const [selectedGroupId, setSelectedGroupId] = useState('all');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedProspect, setSelectedProspect] = useState<ProspectRow | null>(null);
  const [createGroupOpen, setCreateGroupOpen] = useState(false);
  const [addToGroupOpen, setAddToGroupOpen] = useState(false);
  const [form] = Form.useForm();
  const [filterForm] = Form.useForm();

  const currentGroup = MOCK_GROUPS.find((g) => g.id === selectedGroupId);
  const data = selectedGroupId === 'all' ? MOCK_PROSPECTS : MOCK_PROSPECTS.slice(0, 3);

  const columns: ColumnsType<ProspectRow> = [
    {
      title: '公司',
      width: 200,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            <a onClick={() => { setSelectedProspect(record); setDetailDrawerOpen(true); }}>
              {record.company_name}
            </a>
            {record.data_mark === 'precise' && <Tag color="gold" style={{ fontSize: 11 }}>精准</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.country} · {record.product_tags[0]}</Text>
        </Space>
      ),
    },
    {
      title: '评级',
      dataIndex: 'company_grade',
      width: 70,
      render: (g) => <RatingTag grade={g} />,
    },
    {
      title: '联系人',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.contact_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.contact_title}</Text>
        </Space>
      ),
    },
    {
      title: '邮箱状态',
      dataIndex: 'status',
      width: 100,
      render: (s: TenantContactStatus) => <ContactStatusTag status={s} />,
    },
    {
      title: '操作',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => { setSelectedProspect(record); setDetailDrawerOpen(true); }}
        >
          查看详情
        </Button>
      ),
    },
  ];

  const handleCreateGroup = () => {
    form.validateFields().then((values) => {
      message.success(`群组"${values.name}"创建成功`);
      setCreateGroupOpen(false);
      form.resetFields();
    });
  };

  const handleAddToGroup = () => {
    message.success(`已将 ${selectedRowKeys.length} 条记录添加至群组`);
    setAddToGroupOpen(false);
    setSelectedRowKeys([]);
  };

  const handleExport = () => {
    message.success('导出任务已创建，请稍后下载');
  };

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* 左侧群组面板 */}
      <GroupPanel
        groups={MOCK_GROUPS}
        selectedGroupId={selectedGroupId}
        onSelect={setSelectedGroupId}
        onCreateGroup={() => setCreateGroupOpen(true)}
        onRenameGroup={(id) => message.info(`重命名群组 ${id}`)}
        onDeleteGroup={(id) => message.warning(`删除群组 ${id}`)}
      />

      {/* 右侧客户列表区 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* 当前群组标题 */}
        <div style={{ marginBottom: 12 }}>
          <Space>
            <TeamOutlined />
            <Text strong>{currentGroup?.name ?? '全部客户'}</Text>
            <Text type="secondary">({currentGroup?.count ?? 0} 人)</Text>
          </Space>
        </div>

        {/* 准入说明 */}
        <Alert
          type="info"
          showIcon
          message={
            <span>
              评分达到收录阈值（当前：<strong>A 级及以上</strong>）的公司由系统自动收录，也可从公司列表手动添加。
              阈值可在 <Link to="/settings/scoring">设置 → 评分配置</Link> 中调整。
            </span>
          }
          style={{ marginBottom: 12 }}
          closable
        />

        {/* 筛选栏 */}
        <div style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: '12px 16px', marginBottom: 12 }}>
          <Form form={filterForm} layout="inline" style={{ rowGap: 8 }}>
            <Form.Item name="grade" label="评级">
              <Select mode="multiple" placeholder="全部" style={{ width: 160 }} allowClear>
                {['S', 'A', 'B', 'C', 'D'].map((g) => (
                  <Option key={g} value={g}><RatingTag grade={g} /></Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="status" label="联系状态">
              <Select placeholder="全部" style={{ width: 130 }} allowClear>
                <Option value="available">可用</Option>
                <Option value="in_plan">计划中</Option>
                <Option value="contacted">已联系</Option>
                <Option value="replied">已回复</Option>
                <Option value="bounced">已退信</Option>
              </Select>
            </Form.Item>
            <Form.Item name="data_mark" label="数据标记">
              <Select placeholder="全部" style={{ width: 100 }} allowClear>
                <Option value="normal">普通</Option>
                <Option value="precise">精准</Option>
              </Select>
            </Form.Item>
            <Form.Item name="keyword">
              <Input placeholder="搜索公司名/联系人" prefix={<SearchOutlined />} style={{ width: 200 }} />
            </Form.Item>
          </Form>
          <div style={{ marginTop: 12 }}>
            <Space>
              <Button type="primary" icon={<SearchOutlined />}>搜索</Button>
              <Button icon={<ReloadOutlined />} onClick={() => filterForm.resetFields()}>重置</Button>
            </Space>
          </div>
        </div>

        {/* 批量操作栏 */}
        {selectedRowKeys.length > 0 && (
          <div style={{ background: '#e6f4ff', border: '1px solid #91caff', borderRadius: 6, padding: '8px 16px', marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text>已选 {selectedRowKeys.length} 条</Text>
            <Space>
              <Button size="small" onClick={() => setAddToGroupOpen(true)}>加入群组</Button>
              <Button size="small" danger>移出群组</Button>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>取消选择</Button>
            </Space>
          </div>
        )}

        {/* 工具栏 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
          <Button icon={<ExportOutlined />} size="small" onClick={handleExport}>导出 Excel</Button>
        </div>

        {/* 客户表格 */}
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          size="middle"
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          pagination={{
            pageSize: 20,
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
          locale={{
            emptyText: <Empty description="该群组暂无客户，请从公司列表添加" />,
          }}
        />
      </div>

      {/* 客户详情 Drawer */}
      <Drawer
        title={
          selectedProspect ? (
            <Space>
              <Text strong>{selectedProspect.company_name}</Text>
              <RatingTag grade={selectedProspect.company_grade} />
            </Space>
          ) : null
        }
        width="60%"
        open={detailDrawerOpen}
        onClose={() => setDetailDrawerOpen(false)}
      >
        {selectedProspect && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text type="secondary">联系人</Text>
              <div style={{ marginTop: 4 }}>
                <Text strong>{selectedProspect.contact_name}</Text>
                <Text type="secondary"> · {selectedProspect.contact_title}</Text>
              </div>
              <div><Text type="secondary" style={{ fontSize: 12 }}>{selectedProspect.contact_email}</Text></div>
            </div>
            <Divider style={{ margin: 0 }} />
            <div>
              <Text type="secondary">联系状态</Text>
              <div style={{ marginTop: 4 }}>
                <ContactStatusTag status={selectedProspect.status} />
              </div>
            </div>
            <div>
              <Text type="secondary">产品标签</Text>
              <div style={{ marginTop: 4 }}>
                <Space wrap>{selectedProspect.product_tags.map(t => <Tag key={t}>{t}</Tag>)}</Space>
              </div>
            </div>
          </Space>
        )}
      </Drawer>

      {/* 创建群组弹窗 */}
      <Modal
        title="创建群组"
        open={createGroupOpen}
        onOk={handleCreateGroup}
        onCancel={() => { setCreateGroupOpen(false); form.resetFields(); }}
        okText="创建"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="群组名称" rules={[{ required: true, message: '请输入群组名称' }]}>
            <Input placeholder="如：德国A级客户" />
          </Form.Item>
          <Form.Item name="description" label="描述（选填）">
            <Input.TextArea rows={2} placeholder="群组用途说明" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 加入群组弹窗 */}
      <Modal
        title="加入群组"
        open={addToGroupOpen}
        onOk={handleAddToGroup}
        onCancel={() => setAddToGroupOpen(false)}
        okText="确认加入"
      >
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item label="选择目标群组" required>
            <Select placeholder="选择群组" style={{ width: '100%' }}>
              {MOCK_GROUPS.filter((g) => g.id !== 'all').map((g) => (
                <Option key={g.id} value={g.id}>{g.name} ({g.count} 人)</Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
        <Text type="secondary">将为 {selectedRowKeys.length} 位联系人添加至所选群组</Text>
      </Modal>
    </div>
  );
}

Component.displayName = 'CuratedCustomersPage';
