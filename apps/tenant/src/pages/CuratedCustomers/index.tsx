import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
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
import { PlusOutlined, ReloadOutlined, TeamOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Group, Prospect } from '@shared/api';
import { tenantApi } from '../../lib/api';

const { Text, Paragraph } = Typography;

type GroupMemberRow = {
  id: string;
  company_name: string;
  country: string;
  grade: string;
  contact_name: string;
  contact_email: string;
};

type CreateGroupValues = {
  name: string;
  description?: string;
};

type AddToGroupValues = {
  group_id: string;
};

function normalizeGroupMember(record: Record<string, unknown>): GroupMemberRow {
  return {
    id: String(record.id ?? record.tenant_company_id ?? record.company_id ?? ''),
    company_name: String(record.company_name ?? record.name ?? '—'),
    country: String(record.country ?? '—'),
    grade: String(record.grade ?? '—'),
    contact_name: String(record.contact_name ?? record.primary_contact_name ?? '—'),
    contact_email: String(record.contact_email ?? record.primary_contact_email ?? '—'),
  };
}

export function Component() {
  const queryClient = useQueryClient();
  const [selectedGroupId, setSelectedGroupId] = useState<string>('all');
  const [selectedProspectIds, setSelectedProspectIds] = useState<string[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [addToGroupOpen, setAddToGroupOpen] = useState(false);
  const [createForm] = Form.useForm<CreateGroupValues>();
  const [addToGroupForm] = Form.useForm<AddToGroupValues>();

  const groupsQuery = useQuery({
    queryKey: ['tenant', 'groups', 'list'],
    queryFn: async () => (await tenantApi.groups.list({ limit: 100 })).data.data,
  });

  const prospectsQuery = useQuery({
    queryKey: ['tenant', 'prospects', 'list'],
    queryFn: async () => (await tenantApi.prospects.list({ limit: 100 })).data.data,
  });

  const groupMembersQuery = useQuery({
    queryKey: ['tenant', 'groups', 'members', selectedGroupId],
    queryFn: async () => {
      if (selectedGroupId === 'all') {
        return [] as GroupMemberRow[];
      }
      return (await tenantApi.groups.listMembers(selectedGroupId)).data.data.map(normalizeGroupMember);
    },
    enabled: selectedGroupId !== 'all',
  });

  const createGroupMutation = useMutation({
    mutationFn: (values: CreateGroupValues) => tenantApi.groups.create(values),
    onSuccess: async () => {
      message.success('群组已创建');
      setCreateOpen(false);
      createForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'groups', 'list'] });
    },
    onError: () => message.error('创建群组失败'),
  });

  const addMembersMutation = useMutation({
    mutationFn: (values: AddToGroupValues) => tenantApi.groups.batchAddMembers(values.group_id, selectedProspectIds),
    onSuccess: async () => {
      message.success('已加入群组');
      setAddToGroupOpen(false);
      addToGroupForm.resetFields();
      setSelectedProspectIds([]);
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'groups', 'list'] });
    },
    onError: () => message.error('加入群组失败'),
  });

  const prospectStatusMutation = useMutation<void, Error, { id: string; action: 'select' | 'exclude' | 'blacklist' }>({
    mutationFn: async ({ id, action }) => {
      if (action === 'select') {
        await tenantApi.prospects.select(id);
        return;
      }
      if (action === 'exclude') {
        await tenantApi.prospects.exclude(id);
        return;
      }
      await tenantApi.prospects.blacklist(id);
    },
    onSuccess: async () => {
      message.success('状态已更新');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'prospects', 'list'] });
    },
    onError: () => message.error('状态更新失败'),
  });

  const groups = useMemo(() => groupsQuery.data ?? [], [groupsQuery.data]);
  const allProspects = useMemo(() => prospectsQuery.data ?? [], [prospectsQuery.data]);
  const currentGroup = selectedGroupId === 'all'
    ? { id: 'all', name: '全部优选客户', member_count: allProspects.length }
    : groups.find((item) => item.id === selectedGroupId);

  const groupColumns: ColumnsType<Group> = [
    {
      title: '群组',
      dataIndex: 'name',
      render: (value) => <Text strong>{value}</Text>,
    },
    {
      title: '成员数',
      dataIndex: 'member_count',
      width: 90,
    },
  ];

  const prospectColumns: ColumnsType<Prospect> = [
    {
      title: '公司',
      dataIndex: 'name',
      render: (value, record) => (
        <Space>
          <Text strong>{value}</Text>
          {record.is_precise_customer && <Tag color="gold">精准</Tag>}
        </Space>
      ),
    },
    {
      title: '国家',
      dataIndex: 'country',
      width: 90,
      render: (value) => value ? <Tag>{value}</Tag> : '—',
    },
    {
      title: '评级',
      dataIndex: 'grade',
      width: 90,
      render: (value) => value ? <Tag color="blue">{value}</Tag> : '—',
    },
    {
      title: '分数',
      dataIndex: 'total_score',
      width: 90,
      render: (value) => value ?? '—',
    },
    {
      title: '操作',
      width: 220,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => prospectStatusMutation.mutate({ id: record.id, action: 'select' })}>
            选入
          </Button>
          <Button type="link" size="small" onClick={() => prospectStatusMutation.mutate({ id: record.id, action: 'exclude' })}>
            排除
          </Button>
          <Popconfirm title="确认加入黑名单？" onConfirm={() => prospectStatusMutation.mutate({ id: record.id, action: 'blacklist' })}>
            <Button type="link" size="small" danger>
              黑名单
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const memberColumns: ColumnsType<GroupMemberRow> = [
    {
      title: '公司',
      dataIndex: 'company_name',
      render: (value) => <Text strong>{value}</Text>,
    },
    {
      title: '国家',
      dataIndex: 'country',
      width: 90,
      render: (value) => value === '—' ? '—' : <Tag>{value}</Tag>,
    },
    {
      title: '评级',
      dataIndex: 'grade',
      width: 90,
      render: (value) => value === '—' ? '—' : <Tag color="blue">{value}</Tag>,
    },
    {
      title: '联系人',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{record.contact_name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.contact_email}
          </Text>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Alert
        type="info"
        showIcon
        message="优选客户直接读取真实 prospects 与 groups 接口。收录阈值继续由设置页里的评分模板控制。"
      />

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16, alignItems: 'start' }}>
        <Card
          size="small"
          title={
            <Space>
              <TeamOutlined />
              <Text strong>群组</Text>
            </Space>
          }
          extra={
            <Space>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => queryClient.invalidateQueries({ queryKey: ['tenant', 'groups', 'list'] })} />
              <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
                新建
              </Button>
            </Space>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button
              type={selectedGroupId === 'all' ? 'primary' : 'default'}
              block
              onClick={() => setSelectedGroupId('all')}
            >
              全部优选客户 ({allProspects.length})
            </Button>
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              loading={groupsQuery.isLoading}
              columns={groupColumns}
              dataSource={groups}
              locale={{ emptyText: <Empty description="暂无群组" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              onRow={(record) => ({
                onClick: () => setSelectedGroupId(record.id),
                style: {
                  cursor: 'pointer',
                  background: selectedGroupId === record.id ? '#e6f4ff' : undefined,
                },
              })}
            />
          </Space>
        </Card>

        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Card
            size="small"
            title={currentGroup ? `${currentGroup.name}` : '优选客户'}
            extra={
              selectedGroupId === 'all' && (
                <Button
                  disabled={selectedProspectIds.length === 0 || groups.length === 0}
                  onClick={() => setAddToGroupOpen(true)}
                >
                  加入群组
                </Button>
              )
            }
          >
            <Paragraph type="secondary" style={{ marginBottom: 16 }}>
              {selectedGroupId === 'all'
                ? '展示当前租户所有优选客户候选。'
                : '展示所选群组中的真实成员列表。'}
            </Paragraph>
            <Table
              rowKey="id"
              pagination={false}
              loading={selectedGroupId === 'all' ? prospectsQuery.isLoading : groupMembersQuery.isLoading}
              dataSource={selectedGroupId === 'all' ? allProspects : undefined}
              columns={prospectColumns}
              rowSelection={{
                selectedRowKeys: selectedProspectIds,
                onChange: (keys) => setSelectedProspectIds(keys.map((key) => String(key))),
              }}
              locale={{ emptyText: <Empty description="暂无数据" /> }}
              style={{ display: selectedGroupId === 'all' ? 'block' : 'none' }}
            />
            <Table
              rowKey="id"
              pagination={false}
              loading={groupMembersQuery.isLoading}
              dataSource={selectedGroupId === 'all' ? undefined : groupMembersQuery.data}
              columns={memberColumns}
              locale={{ emptyText: <Empty description="暂无数据" /> }}
              style={{ display: selectedGroupId === 'all' ? 'none' : 'block' }}
            />
          </Card>
        </Space>
      </div>

      <Modal
        title="新建群组"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={async () => createGroupMutation.mutate(await createForm.validateFields())}
        confirmLoading={createGroupMutation.isPending}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="群组名称" rules={[{ required: true, message: '请输入群组名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="加入群组"
        open={addToGroupOpen}
        onCancel={() => setAddToGroupOpen(false)}
        onOk={async () => addMembersMutation.mutate(await addToGroupForm.validateFields())}
        confirmLoading={addMembersMutation.isPending}
      >
        <Form form={addToGroupForm} layout="vertical">
          <Form.Item name="group_id" label="目标群组" rules={[{ required: true, message: '请选择目标群组' }]}>
            <Select
              options={groups.map((item) => ({ label: `${item.name} (${item.member_count})`, value: item.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'CuratedCustomersPage';
