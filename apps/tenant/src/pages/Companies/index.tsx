import { useMemo, useState } from 'react';
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
  Radio,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { CloseCircleOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@shared/api';
import type { Company } from '@shared/api';
import { useCursorPagination } from '@shared/hooks';
import { tenantApi } from '../../lib/api';
import { formatDateTime } from '../../lib/format';

const { Text, Paragraph } = Typography;

// ─── 类型定义 ─────────────────────────────────────────────────────────────────

type CompanyContact = {
  name: string;
  email: string;
  title: string;
  is_default: boolean;
  raw: Record<string, unknown>;
};

type CreateCompanyValues = {
  name: string;
  country?: string;
  website?: string;
  industry?: string;
  contact_name?: string;
  contact_email?: string;
  contact_title?: string;
};

/** C5：筛选表单值 */
type FilterValues = {
  keyword?: string;
  grade?: string;
  countries?: string[];
  sub_industries?: string[];
  product_tags?: string[];
  sources?: string[];
  contact_count_range?: string;
  founded_year_from?: number;
  founded_year_to?: number;
  employee_scales?: string[];
  min_score?: number;
  max_score?: number;
};

/** C4：编辑态表单值 */
type EditValues = {
  score_adjustment?: number;
  score_adjust_reason?: string;
  notes?: string;
  tags?: string[];
};

// 联系人数量档位选项
const CONTACT_COUNT_RANGE_OPTIONS = [
  { label: '全部', value: '' },
  { label: '0', value: '0' },
  { label: '1-3', value: '1-3' },
  { label: '4-10', value: '4-10' },
  { label: '11-30', value: '11-30' },
  { label: '30+', value: '30+' },
];

function normalizeContact(record: Record<string, unknown>): CompanyContact {
  return {
    name: String(record.name ?? record.contact_name ?? record.full_name ?? '—'),
    email: String(record.email ?? record.contact_email ?? '—'),
    title: String(record.title ?? record.contact_title ?? '—'),
    is_default: Boolean(record.is_default ?? record.default ?? false),
    raw: record,
  };
}

/** 将筛选表单值转为 API 参数（多选字段加 [] 后缀） */
function buildApiFilters(values: FilterValues, limit = 20): Record<string, unknown> {
  const params: Record<string, unknown> = { limit };
  if (values.keyword) params.keyword = values.keyword;
  if (values.grade) params.grade = values.grade;
  if (values.countries?.length) params['countries[]'] = values.countries;
  if (values.sub_industries?.length) params['sub_industries[]'] = values.sub_industries;
  if (values.product_tags?.length) params['product_tags[]'] = values.product_tags;
  if (values.sources?.length) params['sources[]'] = values.sources;
  if (values.contact_count_range) params.contact_count_range = values.contact_count_range;
  if (values.founded_year_from != null) params.founded_year_from = values.founded_year_from;
  if (values.founded_year_to != null) params.founded_year_to = values.founded_year_to;
  if (values.employee_scales?.length) params['employee_scale[]'] = values.employee_scales;
  if (values.min_score != null) params.min_score = values.min_score;
  if (values.max_score != null) params.max_score = values.max_score;
  return params;
}

// ─── 主组件 ───────────────────────────────────────────────────────────────────

export function Component() {
  const queryClient = useQueryClient();
  const [filterForm] = Form.useForm<FilterValues>();
  const [editForm] = Form.useForm<EditValues>();
  const [createForm] = Form.useForm<CreateCompanyValues>();

  const [appliedFilters, setAppliedFilters] = useState<Record<string, unknown>>({ limit: 20 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [blacklistTarget, setBlacklistTarget] = useState<{ id: string; name: string } | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  /** C4：Drawer 是否处于编辑态 */
  const [drawerEditing, setDrawerEditing] = useState(false);

  // ─── 查询 ─────────────────────────────────────────────────────────────────

  const companiesQuery = useCursorPagination(
    queryKeys.companies.list(appliedFilters),
    async (cursor) =>
      (await tenantApi.companies.list({ ...(appliedFilters as Record<string, unknown>), cursor, limit: 20 })).data,
  );

  const companies = useMemo(
    () => companiesQuery.data?.pages.flatMap((page) => page.data) ?? [],
    [companiesQuery.data],
  );

  const selectedCompanyQuery = useQuery({
    queryKey: selectedId ? queryKeys.companies.detail(selectedId) : ['tenant', 'companies', 'detail', 'empty'],
    queryFn: async () => {
      if (!selectedId) return null;
      return (await tenantApi.companies.detail(selectedId)).data.data;
    },
    enabled: Boolean(selectedId),
  });

  const contactsQuery = useQuery({
    queryKey: selectedId
      ? [...queryKeys.companies.detail(selectedId), 'contacts']
      : ['tenant', 'companies', 'contacts', 'empty'],
    queryFn: async () => {
      if (!selectedId) return [];
      return (await tenantApi.companies.contacts(selectedId)).data.data.map(normalizeContact);
    },
    enabled: Boolean(selectedId),
  });

  // ─── 黑名单 mutation ──────────────────────────────────────────────────────

  const blacklistMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      tenantApi.companies.blacklist(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.companies.all() });
      message.success('已加入黑名单');
      setBlacklistTarget(null);
    },
    onError: () => message.error('黑名单操作失败'),
  });

  // ─── 创建公司 mutation ────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (values: CreateCompanyValues) =>
      tenantApi.companies.create({
        name: values.name.trim(),
        country: values.country?.trim() || undefined,
        website: values.website?.trim() || undefined,
        industry: values.industry?.trim() || undefined,
        contact_name: values.contact_name?.trim() || undefined,
        contact_email: values.contact_email?.trim() || undefined,
        contact_title: values.contact_title?.trim() || undefined,
      }),
    onSuccess: async () => {
      message.success('公司已创建');
      setCreateOpen(false);
      createForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: queryKeys.companies.all() });
    },
    onError: () => message.error('公司创建失败'),
  });

  // ─── C4：编辑私有字段 mutation ────────────────────────────────────────────

  const patchProspectMutation = useMutation({
    mutationFn: (values: EditValues) => {
      if (!selectedId) throw new Error('未选中公司');
      return tenantApi.prospects.update(selectedId, {
        score_adjustment: values.score_adjustment,
        score_adjust_reason: values.score_adjust_reason?.trim() || undefined,
        notes: values.notes?.trim() || undefined,
        tags: values.tags,
      });
    },
    onSuccess: async () => {
      message.success('保存成功');
      setDrawerEditing(false);
      await queryClient.invalidateQueries({
        queryKey: selectedId ? queryKeys.companies.detail(selectedId) : queryKeys.companies.all(),
      });
    },
    onError: () => message.error('保存失败'),
  });

  // ─── 进入编辑态时，回填现有值 ─────────────────────────────────────────────

  const enterEditMode = () => {
    const company = selectedCompanyQuery.data;
    editForm.setFieldsValue({
      score_adjustment: company?.score_adjustment ?? 0,
      score_adjust_reason: company?.score_adjust_reason ?? '',
      notes: company?.notes ?? '',
      tags: (company?.tags ?? []) as string[],
    });
    setDrawerEditing(true);
  };

  // ─── 列定义 ───────────────────────────────────────────────────────────────

  const columns: ColumnsType<Company> = [
    {
      title: '公司名称',
      dataIndex: 'name',
      render: (name, record) => (
        <Space>
          <a onClick={() => setSelectedId(record.id)}>{name}</a>
          {record.is_precise_customer && <Tag color="gold">精准</Tag>}
        </Space>
      ),
    },
    {
      title: '国家',
      dataIndex: 'country',
      width: 90,
      render: (value) => (value ? <Tag>{value}</Tag> : '—'),
    },
    {
      title: '行业',
      dataIndex: 'industry',
      width: 120,
      render: (value) => value ?? '—',
    },
    {
      title: '评级',
      dataIndex: 'grade',
      width: 80,
      render: (value) => (value ? <Tag color="blue">{value}</Tag> : '—'),
    },
    {
      title: '总分',
      dataIndex: 'total_score',
      width: 80,
      render: (value, record) => {
        if (value == null) return '—';
        const adj = record.score_adjustment ?? 0;
        return (
          <Space size={4}>
            <span>{value}</span>
            {adj !== 0 && (
              <Tag color={adj > 0 ? 'green' : 'red'} style={{ margin: 0 }}>
                {adj > 0 ? `+${adj}` : adj}
              </Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: '联系人',
      dataIndex: 'contacts_count',
      width: 70,
      render: (value) => value ?? '—',
    },
    {
      title: '域名',
      dataIndex: 'domain',
      render: (value, record) => value ?? record.website ?? '—',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      width: 170,
      render: (value) =>
        value ? <Text type="secondary">{formatDateTime(value)}</Text> : '—',
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => setSelectedId(record.id)}>
            详情
          </Button>
          <Button
            type="link"
            size="small"
            danger
            onClick={() => setBlacklistTarget({ id: record.id, name: record.name })}
          >
            黑名单
          </Button>
        </Space>
      ),
    },
  ];

  // ─── 筛选处理 ─────────────────────────────────────────────────────────────

  const handleSearch = async () => {
    const values = await filterForm.validateFields();
    setAppliedFilters(buildApiFilters(values));
  };

  const handleReset = () => {
    filterForm.resetFields();
    setAppliedFilters({ limit: 20 });
  };

  // 当前已激活的筛选 chips（用于展示）
  const activeFilterChips = useMemo(() => {
    const chips: Array<{ key: string; label: string }> = [];
    const v = filterForm.getFieldsValue();
    if (v.keyword) chips.push({ key: 'keyword', label: `关键词: ${v.keyword}` });
    if (v.grade) chips.push({ key: 'grade', label: `评级: ${v.grade}` });
    if (v.countries?.length) chips.push({ key: 'countries', label: `国家: ${v.countries.join(',')}` });
    if (v.sub_industries?.length) chips.push({ key: 'sub_industries', label: `行业: ${v.sub_industries.join(',')}` });
    if (v.product_tags?.length) chips.push({ key: 'product_tags', label: `产品标签: ${v.product_tags.join(',')}` });
    if (v.sources?.length) chips.push({ key: 'sources', label: `来源: ${v.sources.join(',')}` });
    if (v.contact_count_range) chips.push({ key: 'contact_count_range', label: `联系人: ${v.contact_count_range}` });
    if (v.founded_year_from != null) chips.push({ key: 'founded_year_from', label: `成立年 ≥${v.founded_year_from}` });
    if (v.founded_year_to != null) chips.push({ key: 'founded_year_to', label: `成立年 ≤${v.founded_year_to}` });
    if (v.employee_scales?.length)
      chips.push({ key: 'employee_scales', label: `规模: ${v.employee_scales.join(',')}` });
    if (v.min_score != null) chips.push({ key: 'min_score', label: `最低分: ${v.min_score}` });
    if (v.max_score != null) chips.push({ key: 'max_score', label: `最高分: ${v.max_score}` });
    return chips;
  }, [appliedFilters]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 渲染 ─────────────────────────────────────────────────────────────────

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* ── C5 筛选栏 ─────────────────────────────────────────────────── */}
      <Card size="small">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <Text strong style={{ fontSize: 16 }}>
                公司列表
              </Text>
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                管理目标公司列表，支持筛选、评分和批量导入。
              </Paragraph>
            </div>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新建公司
            </Button>
          </div>

          <Form form={filterForm} layout="inline">
            <Form.Item name="keyword" label="关键词">
              <Input placeholder="公司名 / 域名" style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="grade" label="评级">
              <Select placeholder="全部" allowClear style={{ width: 90 }}>
                {['S', 'A', 'B', 'C', 'D'].map((g) => (
                  <Select.Option key={g} value={g}>
                    {g}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="countries" label="国家">
              <Select
                mode="tags"
                placeholder="多选 OR"
                style={{ width: 160 }}
                tokenSeparators={[',']}
                allowClear
              />
            </Form.Item>
            <Form.Item name="sub_industries" label="行业">
              <Select
                mode="tags"
                placeholder="多选 OR"
                style={{ width: 160 }}
                tokenSeparators={[',']}
                allowClear
              />
            </Form.Item>
            <Form.Item name="product_tags" label="产品标签">
              <Select
                mode="tags"
                placeholder="多选 OR"
                style={{ width: 160 }}
                tokenSeparators={[',']}
                allowClear
              />
            </Form.Item>
            <Form.Item name="sources" label="来源">
              <Select
                mode="tags"
                placeholder="多选 OR"
                style={{ width: 130 }}
                tokenSeparators={[',']}
                allowClear
              />
            </Form.Item>
            <Form.Item name="contact_count_range" label="联系人数">
              <Radio.Group size="small">
                {CONTACT_COUNT_RANGE_OPTIONS.map((opt) => (
                  <Radio.Button key={opt.value} value={opt.value || undefined}>
                    {opt.label}
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Form.Item>
            <Form.Item name="founded_year_from" label="成立年起">
              <InputNumber min={1800} max={2100} placeholder="2000" style={{ width: 90 }} />
            </Form.Item>
            <Form.Item name="founded_year_to" label="止">
              <InputNumber min={1800} max={2100} placeholder="2025" style={{ width: 90 }} />
            </Form.Item>
            <Form.Item name="employee_scales" label="规模">
              <Select
                mode="tags"
                placeholder="多选 OR"
                style={{ width: 160 }}
                tokenSeparators={[',']}
                allowClear
              />
            </Form.Item>
            <Form.Item name="min_score" label="最低分">
              <InputNumber min={0} max={100} style={{ width: 80 }} />
            </Form.Item>
            <Form.Item name="max_score" label="最高分">
              <InputNumber min={0} max={100} style={{ width: 80 }} />
            </Form.Item>
          </Form>

          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
              搜索
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Space>

          {/* 已选筛选 Chip */}
          {activeFilterChips.length > 0 && (
            <Space wrap>
              {activeFilterChips.map((chip) => (
                <Tag key={chip.key} closable icon={<CloseCircleOutlined />} onClose={handleReset} color="processing">
                  {chip.label}
                </Tag>
              ))}
              <Button size="small" type="link" onClick={handleReset}>
                清空全部
              </Button>
            </Space>
          )}
        </Space>
      </Card>

      {/* ── 公司列表 ────────────────────────────────────────────────── */}
      <Table
        rowKey="id"
        columns={columns}
        dataSource={companies}
        loading={companiesQuery.isLoading}
        pagination={false}
        locale={{ emptyText: <Empty description="暂无公司数据" /> }}
      />

      <div style={{ textAlign: 'center' }}>
        <Button
          onClick={() => companiesQuery.fetchNextPage()}
          loading={companiesQuery.isFetchingNextPage}
          disabled={!companiesQuery.hasNextPage}
        >
          {companiesQuery.hasNextPage ? '加载更多' : '没有更多了'}
        </Button>
      </div>

      {/* ── C4：公司详情 Drawer（含编辑态） ─────────────────────────── */}
      <Drawer
        title={selectedCompanyQuery.data ? selectedCompanyQuery.data.name : '公司详情'}
        open={Boolean(selectedId)}
        onClose={() => {
          setSelectedId(null);
          setDrawerEditing(false);
        }}
        size="large"
        extra={
          selectedCompanyQuery.data && !drawerEditing ? (
            <Button icon={<EditOutlined />} onClick={enterEditMode}>
              编辑
            </Button>
          ) : drawerEditing ? (
            <Space>
              <Button onClick={() => setDrawerEditing(false)}>取消</Button>
              <Button
                type="primary"
                loading={patchProspectMutation.isPending}
                onClick={() => editForm.validateFields().then((v) => patchProspectMutation.mutate(v))}
              >
                保存
              </Button>
            </Space>
          ) : null
        }
      >
        {selectedCompanyQuery.isLoading && <Text type="secondary">正在加载详情…</Text>}
        {selectedCompanyQuery.data && !drawerEditing && (
          /* ── 展示态 ── */
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="国家">{selectedCompanyQuery.data.country ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="行业">{selectedCompanyQuery.data.industry ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="评级">{selectedCompanyQuery.data.grade ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="总分">
                {selectedCompanyQuery.data.total_score != null ? (
                  <Space>
                    <span>{selectedCompanyQuery.data.total_score}</span>
                    {(selectedCompanyQuery.data.score_adjustment ?? 0) !== 0 && (
                      <Tag color={(selectedCompanyQuery.data.score_adjustment ?? 0) > 0 ? 'green' : 'red'}>
                        人工调分:{' '}
                        {(selectedCompanyQuery.data.score_adjustment ?? 0) > 0
                          ? `+${selectedCompanyQuery.data.score_adjustment}`
                          : selectedCompanyQuery.data.score_adjustment}
                      </Tag>
                    )}
                  </Space>
                ) : (
                  '—'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="域名">
                {selectedCompanyQuery.data.domain ?? selectedCompanyQuery.data.website ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label="精准客户">
                {selectedCompanyQuery.data.is_precise_customer ? '是' : '否'}
              </Descriptions.Item>
              <Descriptions.Item label="调分原因" span={2}>
                {selectedCompanyQuery.data.score_adjust_reason ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>
                {selectedCompanyQuery.data.notes ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label="标签" span={2}>
                <Space wrap>
                  {(selectedCompanyQuery.data.tags ?? []).length > 0
                    ? selectedCompanyQuery.data.tags!.map((tag) => <Tag key={tag}>{tag}</Tag>)
                    : '—'}
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="联系人">
              <Table<CompanyContact>
                rowKey={(record, index) => `${record.email}-${index}`}
                loading={contactsQuery.isLoading}
                dataSource={contactsQuery.data ?? []}
                pagination={false}
                locale={{ emptyText: <Empty description="暂无联系人数据" /> }}
                columns={[
                  { title: '姓名', dataIndex: 'name' },
                  { title: '职位', dataIndex: 'title' },
                  { title: '邮箱', dataIndex: 'email' },
                  {
                    title: '默认',
                    dataIndex: 'is_default',
                    width: 90,
                    render: (value) => (value ? <Tag color="gold">默认</Tag> : '—'),
                  },
                ]}
              />
            </Card>
          </Space>
        )}

        {selectedCompanyQuery.data && drawerEditing && (
          /* ── C4 编辑态 ── */
          <Form form={editForm} layout="vertical">
            <Form.Item
              name="score_adjustment"
              label="人工调分（±20）"
              rules={[
                {
                  validator: (_, value) => {
                    if (value == null) return Promise.resolve();
                    if (value < -20 || value > 20)
                      return Promise.reject(new Error('调分范围 -20 ~ +20'));
                    return Promise.resolve();
                  },
                },
              ]}
            >
              <InputNumber
                min={-20}
                max={20}
                style={{ width: '100%' }}
                placeholder="0（范围 -20 ~ +20，影响最终评级）"
              />
            </Form.Item>

            <Form.Item name="score_adjust_reason" label="调分原因">
              <Input.TextArea
                rows={2}
                placeholder="说明调分原因（可选）"
              />
            </Form.Item>

            <Form.Item name="notes" label="备注（私有）">
              <Input.TextArea
                rows={4}
                placeholder="仅本租户可见的备注"
              />
            </Form.Item>

            <Form.Item name="tags" label="标签">
              <Select
                mode="tags"
                placeholder="输入标签后回车添加"
                tokenSeparators={[',']}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Form>
        )}
      </Drawer>

      {/* ── 黑名单确认 Modal ─────────────────────────────────────────── */}
      <Modal
        title={`确认拉黑 ${blacklistTarget?.name ?? ''}`}
        open={Boolean(blacklistTarget)}
        onCancel={() => setBlacklistTarget(null)}
        onOk={() => {
          if (!blacklistTarget) return;
          blacklistMutation.mutate({ id: blacklistTarget.id });
        }}
        confirmLoading={blacklistMutation.isPending}
      >
        <Text type="secondary">将该公司加入黑名单后，后续列表会按后端规则重新过滤。</Text>
      </Modal>

      {/* ── 新建公司 Modal ───────────────────────────────────────────── */}
      <Modal
        title="新建公司"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={async () => createMutation.mutate(await createForm.validateFields())}
        confirmLoading={createMutation.isPending}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="公司名称" rules={[{ required: true, message: '请输入公司名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="country" label="国家">
            <Input placeholder="DE / US / JP" />
          </Form.Item>
          <Form.Item name="website" label="网站">
            <Input placeholder="https://example.com" />
          </Form.Item>
          <Form.Item name="industry" label="行业">
            <Input placeholder="PCB" />
          </Form.Item>
          <Form.Item name="contact_name" label="联系人姓名">
            <Input />
          </Form.Item>
          <Form.Item name="contact_email" label="联系人邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="contact_title" label="联系人职位">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'CompaniesPage';
